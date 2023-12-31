from logging import getLogger, Logger
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.context.say.async_say import AsyncSay
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from fastapi import APIRouter, Request
from config import settings, firestore_client
from repositorys import InstallationStoreRepository, StateStoreRepository, AppConfigRepository, BotStoreRepository


app_logger: Logger = getLogger("slack-app")
APP_ID: str = settings["APP_ID"]
CLIENT_ID: str = settings["CLIENT_ID"]
CLIENT_SECRET: str = settings["CLIENT_SECRET"]
SIGNING_SECRET: str = settings["SIGNING_SECRET"]
SCOPES: list[str] = [
    "app_mentions:read",
    "channels:history", "channels:read", "chat:write",
    "im:history", "im:read", "im:write", "users:read"
]
SLACK_USER_SCOPES: list[str] = []
app = AsyncApp(
    signing_secret=SIGNING_SECRET,
    oauth_settings=AsyncOAuthSettings(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
        user_scopes=SLACK_USER_SCOPES,
        installation_store=InstallationStoreRepository(
            client=firestore_client, logger=app_logger, app_id=APP_ID
        ),
        state_store=StateStoreRepository(
            client=firestore_client, logger=app_logger, expiration_seconds=300
        ),
        install_path=f"/{APP_ID}/slack/install",
        redirect_uri_path=f"/{APP_ID}/slack/oauth_redirect"
    ),
)

app_handler = AsyncSlackRequestHandler(app)
api = APIRouter(
    prefix=f"/{APP_ID}",
)


@app.event("app_mention")
async def app_mention(body: dict, say: AsyncSay, logger: Logger, client: AsyncWebClient):
    logger.info(body)
    await say("Hi there!")


@app.event("app_uninstalled")
async def handle_app_uninstalled(event, logger: Logger, body: dict):
    app_logger.debug(f"App uninstalled event: {event}")
    app_logger.debug(f"App uninstalled body: {body}")
    team_id = body["team_id"]
    app_id = body["api_app_id"]
    try:
        app_logger.debug(f"uninstall: {app_id}, {team_id}")
        app_repository = AppConfigRepository(
            client=firestore_client, team_id=team_id)
        app_bot_repository = BotStoreRepository(
            client=firestore_client, team_id=team_id)

        app_bot_repository.delete(app_id=app_id)
        app_repository.delete(app_id=app_id)
    except Exception as e:
        app_logger.debug(f"Error handling app uninstalled: {e}")


@api.post("/slack/events")
async def endpoint(req: Request):
    return await app_handler.handle(req)


@api.get("/slack/install")
async def install(req: Request):
    return await app_handler.handle(req)


@api.get("/slack/oauth_redirect")
async def oauth_redirect(req: Request):
    return await app_handler.handle(req)
