# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import datetime
import json
import logging
import posixpath
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from pydantic import AwareDatetime

from dependencies.auth import verify_basic_auth
from dependencies.db import get_db_connector
from const import VERSION
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

        result["info"]["checkup_db"][
            "cdr_start_field"
        ] = connector_database.cdr_start_field

        start_date = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        end_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res = await connector_database.get_cdr(start_date, end_date)

        result["info"]["checkup_db"]["history_3_last_days"] = (
            str(res[0]) if len(res) else str(res)
        )
    except Exception as e:
        result["info"]["checkup_db"]["error"] = str(e)
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
    except Exception as e:
        result["info"]["checkup_ari"] = str(e)
        result["status"]["checkup_ari"] = "error"

    # 3. Webhook connect
    try:
        async with httpx.AsyncClient() as client:
            url = f"{config.webhook_url}"

            checkup_webhook_url = await client.get(url)

            result["info"][
                "checkup_webhook_url"
            ] = f"status code {checkup_webhook_url.status_code}"
    except Exception as e:
        result["info"]["checkup_webhook_url"] = str(e)
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
    except Exception as e:
        result["info"]["checkup_websocket"]["error"] = str(e)
        result["status"]["checkup_websocket"] = "error"

    log.info(result)
    return JSONResponse(content=result)


@router.get("/api/calls/hisroty/")
async def calls_history(
    req: Request, start_date: AwareDatetime, end_date: AwareDatetime
):
    try:
        log.info("HISTORY")
        if start_date >= end_date:
            raise HTTPException(
                status_code=400,
                detail="The start date cannot be greater than or equal to the end date",
            )

        connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
            req.app.state.connector_database
        )

        return await connector_database.get_cdr(start_date, end_date)

    except Exception as e:
        log.exception("Unknown calls_history error: %s", e.__context__)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Watch log file please.",
        )


@router.get("/api/numbers/")
async def numbers(req: Request):
    try:
        log.info("NUMBERS")

        ari: Ari = req.app.state.ari
        return await ari.numbers()

    except Exception as e:
        log.exception("Unknown /api/numbers/ error: %s", e.__context__)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Watch log file please.",
        )


@router.get("/api/call/recording")
async def call_recording(req: Request, id: str):
    try:
        log.info("RECORDING")

        ari: Ari = req.app.state.ari
        return await ari.call_recording(id)

    except Exception as e:
        log.exception("Unknown /api/call/recording error: %s", e.__context__)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Watch log file please.",
        )
