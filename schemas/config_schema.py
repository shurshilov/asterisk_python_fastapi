# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import base64
from typing import Annotated, Literal

from pydantic import BaseModel, Field, UrlConstraints
from pydantic_core import Url
from pydantic_settings import BaseSettings, SettingsConfigDict

HttpURL = Annotated[Url, UrlConstraints(allowed_schemes=["http", "https"], max_length=2048)]
WsURL = Annotated[Url, UrlConstraints(allowed_schemes=["ws", "wss"], max_length=2048)]
TcpPort = Annotated[int, Field(ge=0, le=65535)]


class DbConfig(BaseModel):
    db_host: str
    db_port: TcpPort
    db_database: str
    db_user: str
    db_password: str
    db_dialect: Literal["mysql", "postgresql", "sqlite"]
    db_table_cdr_name: str


class AriConfig(BaseModel):
    url: HttpURL
    wss: WsURL
    login: str
    password: str
    events_ignore: list[str]
    events_used: list[str]


class AmiConfig(BaseModel):
    host: str
    port: TcpPort
    login: str
    password: str
    events_ignore: list[str]
    events_used: list[str]


class Config(BaseSettings):
    """Read from disk and validate .env conf file"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    # cdr_path = "/var/log/asterisk/cdr-csv"
    # debug_level: Literal["info", "debug", "error"]
    path_recordings: str
    # webhook
    webhook_url: HttpURL

    # DB
    db_check_cdr_enable: int
    db_host: str
    db_port: TcpPort
    db_database: str
    db_user: str
    db_password: str
    db_dialect: Literal["mysql", "postgresql", "sqlite"]
    db_table_cdr_name: str

    # ARI
    ari_enable: int
    ari_url: HttpURL
    ari_wss: WsURL
    ari_login: str
    ari_password: str
    ari_events_ignore: list[str]
    ari_events_used: list[str]

    # AMI
    ami_enable: int
    ami_host: str
    ami_port: TcpPort
    ami_login: str
    ami_password: str
    ami_events_ignore: list[str]
    ami_events_used: list[str]

    @property
    def ari_config(self):
        return AriConfig(
            url=self.ari_url,
            wss=self.ari_wss,
            login=self.ari_login,
            password=self.ari_password,
            events_ignore=self.ari_events_ignore,
            events_used=self.ari_events_used,
        )

    @property
    def ami_config(self):
        return AmiConfig(
            host=self.ami_host,
            port=self.ami_port,
            login=self.ami_login,
            password=self.ami_password,
            events_ignore=self.ami_events_ignore,
            events_used=self.ami_events_used,
        )

    @property
    def api_key(self):
        """Asterisk ARI api key auth. For read data from ARI."""
        return f"{self.ari_login}:{self.ari_password}"

    @property
    def api_key_base64(self):
        """HTTP basic header api key auth. For send data to webhook."""
        api_key_bytes = base64.b64encode(bytes(self.api_key, "utf-8"))
        api_key_base64 = api_key_bytes.decode("utf-8")
        return api_key_base64
