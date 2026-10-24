"""Runtime compatibility checks without Slack or Google Cloud credentials."""

import hashlib
import hmac
import importlib
import os
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "APP_ID": "test-app",
    "CLIENT_ID": "test-client",
    "CLIENT_SECRET": "test-secret",
    "SIGNING_SECRET": "test-signing-secret",
}


@pytest.fixture(scope="module")
def client():
    with (
        patch.dict("os.environ", TEST_ENV),
        patch("google.cloud.logging.Client"),
        patch("google.cloud.firestore.Client"),
    ):
        app = importlib.import_module("app").app
        with TestClient(app) as test_client:
            yield test_client


def test_startup_and_routes(client):
    assert client.get("/").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/test-app/slack/events" in paths
    assert "/test-app/slack/install" in paths
    assert "/test-app/slack/oauth_redirect" in paths


def test_unsigned_slack_request_is_rejected(client):
    response = client.post("/test-app/slack/events", json={
        "type": "url_verification", "challenge": "test-challenge",
    })
    assert response.status_code == 401


def test_signed_slack_challenge(client):
    body = '{"type":"url_verification","challenge":"test-challenge"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"test-signing-secret", f"v0:{timestamp}:{body}".encode(), hashlib.sha256,
    ).hexdigest()
    response = client.post("/test-app/slack/events", content=body, headers={
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": f"v0={signature}",
    })
    assert response.status_code == 200
    assert response.json() == {"challenge": "test-challenge"}


@pytest.mark.skipif(sys.platform == "win32", reason="Gunicorn requires Unix")
def test_gunicorn_uvicorn_startup():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    # Mock only cloud clients; exercise the real app and production worker class.
    bootstrap = """
from unittest.mock import patch
patch('google.cloud.logging.Client').start()
patch('google.cloud.firestore.Client').start()
from gunicorn.app.wsgiapp import run
run()
"""
    with tempfile.TemporaryFile(mode="w+") as logs:
        process = subprocess.Popen([
            sys.executable, "-c", bootstrap,
            "--bind", f"127.0.0.1:{port}", "--workers", "1", "--threads", "8",
            "-k", "uvicorn.workers.UvicornWorker", "app:app",
        ], env={**os.environ, **TEST_ENV}, stdout=logs, stderr=logs)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                        assert response.status == 200
                        return
                except URLError:
                    time.sleep(0.1)
            logs.seek(0)
            pytest.fail(f"Gunicorn did not become ready:\n{logs.read()}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
