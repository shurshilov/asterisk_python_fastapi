# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
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
from routers.routers import router
from schemas.config_schema import Config
from services.ami import Ami

# from services.ami_new import Ami as AmiNew
from services.ari import Ari
from services.websocket import WebsocketEvents

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
    level="DEBUG",
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


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    """Swagger ui docs from static (local) files not CDN

    Returns:
        HTML swagger ui
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Redoc ui docs from static (local) files not CDN

    Returns:
        HTML redoc ui
    """
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
async def catch_exception_buisness(req: Request, exc: BusinessError):
    log.info("Business error %s", exc)
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail=exc.detail,
    )


@app.exception_handler(AuthError)
async def catch_exception_auth(req: Request, exc: AuthError):
    log.info("Auth error %s", exc)
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail=exc.detail,
    )


@app.exception_handler(Exception)
async def catch_exception_internal(req: Request, exc: Exception):
    log.exception("Internal server error %s", exc)
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)


async def producer_webhook(config: Config, timeout: int = 30) -> None:
    """Producer send events to cusomer webhook from config file"""
    websocket_client = WebsocketEvents(
        ari_config=config.ari_config,
        api_key=config.api_key,
        api_key_base64=config.api_key_base64,
        webhook_url=f"{config.webhook_url}",
        timeout=timeout,
    )
    app.state.websocket_client = websocket_client

    await websocket_client.start_consumer()


@app.on_event("startup")
async def start() -> None:
    """Create backgrond task and init app"""
    # read and validate config file
    config = Config()  # type: ignore
    ari = Ari(api_key=config.api_key, ari_url=str(config.ari_url))
    # ami = AmiNew(
    #     ami_config=config.ami_config,
    #     api_key_base64=config.api_key_base64,
    #     webhook_url=str(config.webhook_url),
    # )
    ami = Ami(
        ami_config=config.ami_config,
        api_key_base64=config.api_key_base64,
        webhook_url=str(config.webhook_url),
    )

    app.state.config = config
    app.state.ari = ari
    app.state.ami = ami
    app.state.connector_database = get_db_connector(config)

    log.info("start check cdr version...")
    try:
        await app.state.connector_database.check_cdr_old()
    except Exception as exc:
        log.exception("Unknown check_cdr_old error: %s", exc)
    log.info("end check cdr version")

    asyncio.gather(ami.start_catch_events())

    app.state.background_tasks = [
        asyncio.create_task(producer_webhook(config)),
    ]


@app.on_event("shutdown")
async def shutdown():
    for task in app.state.background_tasks:
        task.cancel()
