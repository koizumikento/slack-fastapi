from slack_sdk.oauth.installation_store.async_installation_store import AsyncInstallationStore
from slack_sdk.oauth.state_store.async_state_store import AsyncOAuthStateStore
from slack_sdk.oauth.installation_store import Installation, Bot
from google.cloud.firestore import Client
from google.cloud.firestore_v1 import collection
from logging import Logger
from datetime import datetime  # type: ignore
from uuid import uuid4
import time
from typing import Optional


class InstallationStoreRepository(AsyncInstallationStore):
    def __init__(self, *, client: Client, logger: Logger, app_id: str, ):
        self.team_repository = TeamStoreRepository(client)
        self.enterprise_repository = EnterPriseRepository(client)
        self._logger = logger
        self.app_id = app_id

    @property
    def logger(self) -> Logger:
        return self._logger

    async def async_save(self, installation: Installation):
        i = installation.to_dict()
        self.logger.debug(f"installation: {i}")
        i["enterprise_id"] = i["enterprise_id"] if i["enterprise_id"] is not None else False
        bot = {
            "user_token": i["user_token"],
            "user_scopes": i["user_scopes"],
            "user_refresh_token": i["user_refresh_token"],
            "user_token_expires_at": i["user_token_expires_at"],
            "bot_token": i["bot_token"],
            "bot_id": i["bot_id"],
            "bot_user_id": i["bot_user_id"],
            "bot_scopes": i["bot_scopes"],
            "bot_refresh_token": i["bot_refresh_token"],
            "bot_token_expires_at": i["bot_token_expires_at"],
            "incoming_webhook_url": i["incoming_webhook_url"],
            "incoming_webhook_channel": i["incoming_webhook_channel"],
            "incoming_webhook_channel_id": i["incoming_webhook_channel_id"],
            "incoming_webhook_configuration_url": i["incoming_webhook_configuration_url"],
            "is_enterprise_install": i["is_enterprise_install"],
            "token_type": i["token_type"],
            "installed_at": i["installed_at"],
        }

        if (i["enterprise_id"]):
            self.enterprise_repository.save(
                i["enterprise_id"], {
                    "name": i["enterprise_name"],
                    "enterprise_url": i["enterprise_url"],
                }
            )

        if (i["team_id"] is not None):
            app_bot_repository = AppConfigRepository(i["team_id"])
            app_repository = AppConfigRepository(i["team_id"])
            user_repository = AppConfigRepository(
                team_id=i["team_id"], app_id=self.app_id)

            self.team_repository.save(
                i["team_id"], {
                    "name": i["team_name"],
                    "enterprise_id": i["enterprise_id"],
                    "is_enterprise_install": i["is_enterprise_install"],
                }
            )

            app_bot_repository.save(
                self.app_id,
                bot
            )

            if (not app_repository.exists(self.app_id)):
                app_repository.save(
                    self.app_id,
                    i["user_id"],
                    {}
                )

            if user_repository.get(i["user_id"]) is None:
                user_repository.save(
                    i["user_id"], {}
                )

    async def async_save_bot(self, bot: Bot):
        return

    async def async_find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        bot: Optional[Bot] = None
        return bot

    async def async_find_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Installation]:
        app_bot_repository = BotStoreRepository(team_id)
        enterprise = self.enterprise_repository.get(enterprise_id)
        team = self.team_repository.get(team_id)
        bot = app_bot_repository.get(self.app_id)
        installation: Optional[Installation] = None
        self.logger.debug(f"user_id: {user_id}")
        self.logger.debug(f"enterprise: {enterprise}")
        self.logger.debug(f"team: {team}")
        self.logger.debug(f"bot: {bot}")

        bot["installed_at"] = datetime.fromtimestamp(
            bot["installed_at"].timestamp()) if bot is not None else None

        installation = Installation(
            app_id=self.app_id,
            enterprise_id=enterprise_id,
            enterprise_name=enterprise["name"] if enterprise is not None else None,
            enterprise_url=enterprise["enterprise_url"] if enterprise is not None else None,
            team_id=team_id,
            team_name=team["name"] if team is not None else None,
            bot_token=bot["bot_token"] if bot is not None else None,
            bot_id=bot["bot_id"] if bot is not None else None,
            bot_user_id=bot["bot_user_id"] if bot is not None else None,
            bot_scopes=bot["bot_scopes"] if bot is not None else None,
            bot_refresh_token=bot["bot_refresh_token"] if bot is not None else None,
            bot_token_expires_at=bot["bot_token_expires_at"] if bot is not None else None,
            user_id=user_id,
            user_token=bot["user_token"] if bot is not None else None,
            user_scopes=bot["user_scopes"] if bot is not None else None,
            user_refresh_token=bot["user_refresh_token"] if bot is not None else None,
            user_token_expires_at=bot["user_token_expires_at"] if bot is not None else None,
            incoming_webhook_url=bot["incoming_webhook_url"] if bot is not None else None,
            incoming_webhook_channel=bot["incoming_webhook_channel"] if bot is not None else None,
            incoming_webhook_channel_id=bot["incoming_webhook_channel_id"] if bot is not None else None,
            incoming_webhook_configuration_url=bot["incoming_webhook_configuration_url"] if bot is not None else None,
            is_enterprise_install=is_enterprise_install,
            token_type=bot["token_type"] if bot is not None else None,
            installed_at=bot["installed_at"] if bot is not None else None,
        )

        self.logger.debug(f"installation: {installation}")
        return installation

    async def async_delete_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
    ) -> None:
        self.team_repository.delete(team_id=team_id)
        user_repo = UserConfigRepository(team_id=team_id, app_id=self.app_id)
        users = user_repo.get_all()
        for user in users:
            user_repo.delete(user_id=user["user_id"])

    async def async_delete_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
    ) -> None:
        app_bot_repository = BotStoreRepository(team_id)
        app_bot_repository.delete(self.app_id)
        user_repo = UserConfigRepository(team_id=team_id, app_id=self.app_id)
        user_repo.delete(user_id=user_id)

    async def async_delete_all(self, *, enterprise_id: str | None, team_id: str | None):
        await self.async_delete_bot(enterprise_id=enterprise_id, team_id=team_id)


class StateStoreRepository(AsyncOAuthStateStore):
    def __init__(self, expiration_seconds: int, logger: Logger):
        self.expiration_seconds = expiration_seconds
        self._logger = logger
        self.state_repository = StateRepository()

    @property
    def logger(self) -> Logger:
        return self._logger

    async def async_issue(self, *args, **kwargs) -> str:
        state: str = str(uuid4())
        now = datetime.utcfromtimestamp(time.time() + self.expiration_seconds)

        self.state_repository.save(state, {
            "expire_at": now,
        })
        return state

    async def async_consume(self, state: str) -> bool:
        self.logger.debug(f"Consuming state: {state}")
        try:

            ret = self.state_repository.is_expire(state)
            self.logger.debug(f"@async_consume ret: {ret}")
            if ret:
                self.state_repository.delete(state)
                return True
            else:
                return False
        except Exception as e:  # skipcq: PYL-W0703
            message = f"Failed to find any persistent data for state: {state} - {e}"
            self.logger.debug(message)
            return False


class StateRepository:
    TABLE_NAME = "states"

    def __init__(self, client):
        self.collection: collection = client.collection(
            self.TABLE_NAME
        )

    def exists(self, state: str) -> bool:
        return self.collection.document(state).get().exists

    def get(self, state: str) -> dict:
        doc = self.collection.document(state).get()
        if doc.exists:
            return {
                "state": state,
                **doc.to_dict()
            }
        else:
            return None

    def is_expire(self, state: str) -> bool:
        now = datetime.utcnow()
        if self.exists(state):
            s = self.collection.document(state).get()
            s.to_dict()["expire_at"] = s.to_dict()[
                "expire_at"].replace(tzinfo=None)

            if datetime.fromtimestamp(s.to_dict()["expire_at"].timestamp()) >= now:
                return True
            else:
                return False
        else:
            return False

    def save(self, state: str, state_obj: dict):
        self.collection.document(state).set(state_obj)

    def delete(self, state: str):
        self.collection.document(state).delete()


class EnterPriseRepository:
    TABLE_NAME = "enterprises"

    def __init__(self, client: Client):
        self.collection = client.collection(self.TABLE_NAME)

    def get(self, enterprise_id: str):
        return {
            **self.collection.document(enterprise_id).get().to_dict(),
            "id": enterprise_id
        }

    def save(self, enterprise_id: str, data: dict):
        self.collection.document(enterprise_id).set(data)

    def delete(self, enterprise_id: str):
        self.collection.document(enterprise_id).delete()


class TeamStoreRepository:
    TABLE_NAME = "teams"

    def __init__(self, client: Client):
        self.collection = client.collection(self.TABLE_NAME)

    def get(self, team_id: str):
        return {
            **self.collection.document(team_id).get().to_dict(),
            "id": team_id
        }

    def save(self, team_id: str, data: dict):
        self.collection.document(team_id).set(data)

    def delete(self, team_id: str):
        self.collection.document(team_id).delete()


class AppConfigRepository:
    TABLE_NAME = "app_configs"

    def __init__(self, client: Client, team_id: str):
        self.collection = TeamStoreRepository(client).collection.document(
            team_id).collection(self.TABLE_NAME)

    def get(self, app_id: str):
        return {
            **self.collection.document(app_id).get().to_dict(),
            "id": app_id
        }

    def save(self, app_id: str, data: dict):
        self.collection.document(app_id).set(data)

    def delete(self, app_id: str):
        self.collection.document(app_id).delete()


class BotStoreRepository:
    TABLE_NAME = "bots"

    def __init__(self, client: Client, team_id: str, app_id: str):
        self.collection = AppConfigRepository(client, team_id).collection.document(
            app_id).collection(self.TABLE_NAME)

    def get(self, bot_id: str):
        return {
            **self.collection.document(bot_id).get().to_dict(),
            "id": bot_id
        }

    def save(self, bot_id: str, data: dict):
        self.collection.document(bot_id).set(data)

    def delete(self, bot_id: str):
        self.collection.document(bot_id).delete()


class UserConfigRepository:
    TABLE_NAME = "user_configs"

    def __init__(self, client: Client, team_id: str, app_id: str):
        self.collection = AppConfigRepository(client, team_id).collection.document(
            app_id).collection(self.TABLE_NAME)

    def get(self, user_id: str):
        return {
            **self.collection.document(user_id).get().to_dict(),
            "id": user_id
        }

    def save(self, user_id: str, data: dict):
        self.collection.document(user_id).set(data)

    def delete(self, user_id: str):
        self.collection.document(user_id).delete()
