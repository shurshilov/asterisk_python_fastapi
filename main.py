# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from const import VERSION
from dependencies.db import get_db_connector
from schemas.config_schema import Config
from services.ari import Ari
from services.websocket import WebsocketEvents
from routers.routers import router


log_file_handler = RotatingFileHandler(
    filename="asterisk_agent.log",
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding=None,
)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level="INFO",
    handlers=[log_file_handler],
)
log = logging.getLogger("asterisk_agent")

app = FastAPI(
    title="Asterisk Agent",
    description="Light web server for calls history and webhook feature",
    version=VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


async def producer_webhook(config: Config, timeout: int = 30) -> None:
    """Producer send events to cusomer webhook from config file"""
    try:
        websocket_url = f"{config.ari_wss}".rstrip("/")
        webhook_url = f"{config.webhook_url}"
        ari_url = f"{config.ari_url}"

        websocket_client = WebsocketEvents(
            ari_url=ari_url,
            websocket_url=websocket_url,
            webhook_url=webhook_url,
            timeout=timeout,
            api_key=config.api_key,
            api_key_base64=config.api_key_base64,
            webhook_events_denied=config.webhook_events_denied,
            webhook_events_allow=config.webhook_events_allow,
        )
        app.state.websocket_client = websocket_client

        await websocket_client.start_consumer()
    except Exception as e:
        log.exception("Unknown producer_webhook error: %s", e)


@app.on_event("startup")
async def start() -> None:
    """Create backgrond task"""
    # read and validate config file
    config = Config()  # type: ignore
    ari = Ari(api_key=config.api_key, ari_url=str(config.ari_url))
    app.state.config = config
    app.state.ari = ari
    connector_database = get_db_connector(config)
    await connector_database.check_cdr_old()

    app.state.background_tasks = [
        asyncio.create_task(producer_webhook(config)),
    ]


@app.on_event("shutdown")
async def shutdown():
    for t in app.state.background_tasks:
        t.cancel()
