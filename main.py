# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
)
from fastapi.staticfiles import StaticFiles
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from const import VERSION
from dependencies.db import get_db_connector
from exceptions.exceptions import AuthError, BusinessError
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
    handlers=[log_file_handler, logging.StreamHandler(sys.stdout)],
)

log = logging.getLogger("asterisk_agent")

app = FastAPI(
    title="Asterisk Agent",
    description="Light web server for calls history and webhook features",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    responses={
        HTTP_400_BAD_REQUEST: {
            "description": "Business Logic Error",
        },
        HTTP_401_UNAUTHORIZED: {
            "description": "Unauthorized",
        },
        HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation Error"},
        HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error",
        },
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# swagger file from local instead CDN
@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


# статичная папка для картинок документации
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.include_router(router)


@app.exception_handler(BusinessError)
async def catch_exception_buisness(request: Request, exc: BusinessError):
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail=exc.detail,
    )


@app.exception_handler(AuthError)
async def catch_exception_auth(request: Request, exc: AuthError):
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail=exc.detail,
    )


@app.exception_handler(Exception)
async def catch_exception_internal(request: Request, exc: Exception):
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)


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
    app.state.connector_database = get_db_connector(config)

    log.info("start check cdr version...")
    try:
        await app.state.connector_database.check_cdr_old()
    except Exception as e:
        log.exception("Unknown check_cdr_old error: %s", e)
    log.info("end check cdr version")

    app.state.background_tasks = [
        asyncio.create_task(producer_webhook(config)),
    ]


@app.on_event("shutdown")
async def shutdown():
    for t in app.state.background_tasks:
        t.cancel()
