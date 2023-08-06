import os
from pydantic_settings import BaseSettings
from logging import basicConfig, DEBUG, INFO
from google.cloud import logging
from google.cloud.logging_v2 import Logger
from google.cloud import firestore


logger_client: Logger = logging.Client()
log_level = DEBUG if os.getenv("LOGLEVEL") == "DEBUG" else INFO
logger_client.setup_logging(log_level=log_level)
firestore_client = firestore.Client()
basicConfig(level=log_level)


class Settings(BaseSettings):
    APP_ID: str = os.getenv("APP_ID", "")
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    SIGNING_SECRET: str = os.getenv("SIGNING_SECRET", "")


settings = Settings().model_dump()
