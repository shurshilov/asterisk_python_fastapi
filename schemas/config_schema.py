# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import base64
from typing import Annotated, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import UrlConstraints
from pydantic_core import Url

HttpURL = Annotated[
    Url, UrlConstraints(allowed_schemes=["http", "https"], max_length=2048)
]
WsURL = Annotated[Url, UrlConstraints(allowed_schemes=["ws", "wss"], max_length=2048)]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    # cdr_path = "/var/log/asterisk/cdr-csv"
    # debug_level: Literal["info", "debug", "error"]
    webhook_url: HttpURL
    webhook_events_denied: list[str]
    webhook_events_allow: list[str]

    # DB
    db_host: str
    db_port: int
    db_database: str
    db_user: str
    db_password: str
    db_dialect: Literal["mysql", "postgresql", "sqlite"]
    db_table_cdr_name: str

    # ARI
    ari_url: HttpURL
    ari_wss: WsURL
    ari_login: str
    ari_password: str

    @property
    def api_key(self):
        return f"{self.ari_login}:{self.ari_password}"

    @property
    def api_key_base64(self):
        api_key_bytes = base64.b64encode(bytes(self.api_key, "utf-8"))
        api_key_base64 = api_key_bytes.decode("utf-8")
        return api_key_base64

    # @field_serializer("webhook_url")
    # def serialize_webhook_url(self, url: HttpURL):
    #     return str(url)

    # @field_serializer("ari_url")
    # def serialize_ari_url(self, url: HttpURL):
    #     return str(url)

    # @field_serializer("ari_wss")
    # def serialize_ari_wss(self, url: WsURL):
    #     return str(url)
