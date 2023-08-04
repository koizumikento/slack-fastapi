import os
from pydantic_settings import BaseSettings
from logging import basicConfig, DEBUG, INFO
from google.cloud import logging
from google.cloud.logging_v2 import Logger
from google.cloud import firestore


logger_client: Logger = logging.Client()
logger_client.setup_logging(log_level=DEBUG)
firestore_client = firestore.Client()
log_level = DEBUG if os.environ.get("LOGLEVEL") == "DEBUG" else INFO
basicConfig(level=log_level)


class Settings(BaseSettings):
    APP_ID: str = os.environ.get("APP_ID", "")
    CLIENT_ID: str = os.environ.get("CLIENT_ID", "")
    CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET", "")
    SIGNING_SECRET: str = os.environ.get("SIGNING_SECRET", "")


settings = Settings().model_dump()
