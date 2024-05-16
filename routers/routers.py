# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import datetime
import json
import logging
import posixpath
import urllib.parse

import aiofiles
import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime

from const import VERSION
from dependencies.auth import verify_basic_auth
from exceptions.exceptions import BusinessError
from schemas.config_schema import Config
from services.ari import Ari
from services.database import MysqlStrategy, PostgresqlStrategy, SqliteStrategy

log = logging.getLogger("asterisk_agent")
router = APIRouter(tags=["API"], dependencies=[Depends(verify_basic_auth)])

# disable httpx logger, for not log get request with api_key
logging.getLogger("httpx").setLevel("CRITICAL")


@router.get("/api/checkup/")
async def checkup(req: Request):
    """
    1. Asterisk Database connect
    2. Asterisk ARI connect (request to asterisk version)
    3. Webhook connect
    4. Websocket connect
    """
    log.info("CHECKUP")
    config: Config = req.app.state.config
    result = {
        "vesrion": VERSION,
        "webhook_url": f"{config.webhook_url}",
        "status": {
            "checkup_db": "ok",
            "checkup_ari": "ok",
            "checkup_webhook_url": "ok",
            "checkup_websocket": "ok",
        },
        "info": {
            "checkup_db": {},
            "checkup_ari": {},
            "checkup_webhook_url": {},
            "checkup_websocket": {},
        },
    }

    # 1 Asterisk Database
    try:
        result["info"]["checkup_db"]["dialect"] = config.db_dialect

        connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
            req.app.state.connector_database
        )

        result["info"]["checkup_db"]["cdr_start_field"] = connector_database.cdr_start_field

        start_date = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        end_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = await connector_database.get_cdr(start_date, end_date)

        result["info"]["checkup_db"]["history_last_call"] = rows[0] if len(rows) else str(rows)
    except Exception as exc:
        result["info"]["checkup_db"]["error"] = str(exc)
        result["status"]["checkup_db"] = "error"

    # 2 Asterisk ARI
    try:
        async with httpx.AsyncClient() as client:
            url1 = f"{config.ari_url}"
            endpont_url = posixpath.join(url1, "asterisk/info")
            url = f"{endpont_url}?api_key={config.api_key}"

            checkup_ari = await client.get(url)
            checkup_ari.raise_for_status()

            result["info"]["checkup_ari"] = json.loads(checkup_ari.text)
    except Exception as exc:
        result["info"]["checkup_ari"] = str(exc)
        result["status"]["checkup_ari"] = "error"

    # 3. Webhook connect
    try:
        async with httpx.AsyncClient() as client:
            url = f"{config.webhook_url}"

            checkup_webhook_url = await client.get(url)

            result["info"]["checkup_webhook_url"] = f"status code {checkup_webhook_url.status_code}"
            if checkup_webhook_url.status_code != 200:
                result["status"]["checkup_webhook_url"] = "error"
    except Exception as exc:
        result["info"]["checkup_webhook_url"] = str(exc)
        result["status"]["checkup_webhook_url"] = "error"

    # 4. Websocket last message
    try:
        result["info"]["checkup_websocket"] = {
            "answer_last_message_time": req.app.state.websocket_client.answer_last_message_time,
            "answer_last_message": req.app.state.websocket_client.answer_last_message,
            "no_answer_last_message_time": req.app.state.websocket_client.no_answer_last_message_time,
            "no_answer_last_message": req.app.state.websocket_client.no_answer_last_message,
            "last_connected_time": req.app.state.websocket_client.last_connected_time,
            "connected": req.app.state.websocket_client.connected,
        }
        if not req.app.state.websocket_client.connected:
            result["status"]["checkup_websocket"] = "error"
        if req.app.state.websocket_client.disconnected_reason:
            result["info"]["checkup_websocket"][
                "disconnected_reason"
            ] = req.app.state.websocket_client.disconnected_reason
    except Exception as exc:
        result["info"]["checkup_websocket"]["error"] = str(exc)
        result["status"]["checkup_websocket"] = "error"

    log.info(result)
    return JSONResponse(content=result)


@router.get("/api/calls/hisroty/")
async def calls_history(req: Request, start_date: AwareDatetime, end_date: AwareDatetime):
    """Return calls history

    Arguments:
        start_date -- start date of calls
        end_date -- end date of calls

    Raises:
        BusinessError: The start date cannot be greater than or equal to the end date

    Returns:
        cdr list of calls
    """
    log.info("HISTORY")

    if start_date >= end_date:
        raise BusinessError("The start date cannot be greater than or equal to the end date")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_cdr(start_date, end_date)


@router.get("/api/numbers/")
async def numbers(req: Request):
    """Return numbers (endpoints) Asterisk

    Returns:
        list of numbers
    """
    log.info("NUMBERS")

    ari: Ari = req.app.state.ari
    # answer already in json
    res = await ari.numbers()
    return json.loads(res)


@router.get("/api/call/recording/ari")
async def call_recording_ari(req: Request, filename: str):
    """Return binary record of call, from ARI
    Arguments:
        filename -- filename
    Returns:
        binary record
    """
    log.info("RECORDING ARI")

    ari: Ari = req.app.state.ari
    return await ari.call_recording(filename)


@router.get("/api/call/recording")
async def call_recording(req: Request, filename: str):
    """Return binary record of call, from directly server folder
    Arguments:
        filename -- filename
    Returns:
        binary record
    """
    log.info("RECORDING")

    config: Config = req.app.state.config
    path_file = f"{posixpath.join(config.path_recordings, filename)}"
    log.info("Path recordings: %s", path_file)

    async with aiofiles.open(path_file, "rb") as file:
        recording = await file.read()

    return Response(
        headers={
            "Content-Disposition": f"Attachment" f""";filename={urllib.parse.quote(filename)}"""
        },
        media_type="application/octet-stream;charset=utf-8",
        content=recording,
    )
