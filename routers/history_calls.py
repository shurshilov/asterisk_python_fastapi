# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime

from dependencies.auth import verify_basic_auth
from exceptions.exceptions import BusinessError
from schemas.config_schema import Id
from services.database import MysqlStrategy, PostgresqlStrategy, SqliteStrategy

log = logging.getLogger("asterisk_agent")
router = APIRouter(tags=["API"], dependencies=[Depends(verify_basic_auth)])


@router.get("/api/calls/hisroty/uniqueid")
async def calls_history_uniqueid(
    req: Request,
    uniqueid: Id,
):
    log.info("HISTORY UNIQUEID")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_cdr_uniqueid_or_linkedid(uniqueid)


@router.get("/api/calls/hisroty/")
async def calls_history(req: Request, start_date: AwareDatetime, end_date: AwareDatetime):
    """
    Arguments:
        start_date -- start date
        end_date -- end date

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
