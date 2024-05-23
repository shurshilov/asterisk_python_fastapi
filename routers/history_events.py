# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime

from dependencies.auth import verify_basic_auth
from exceptions.exceptions import BusinessError
from services.database import MysqlStrategy, PostgresqlStrategy, SqliteStrategy

log = logging.getLogger("asterisk_agent")
router = APIRouter(tags=["API"], dependencies=[Depends(verify_basic_auth)])


@router.get("/api/events/hisroty/")
async def events_history(req: Request, start_date: AwareDatetime, end_date: AwareDatetime):
    """Return events history

    Arguments:
        start_date -- start date
        end_date -- end date

    Raises:
        BusinessError: The start date cannot be greater than or equal to the end date

    Returns:
        cel list of events
    """
    log.info("EVENTS")

    if start_date >= end_date:
        raise BusinessError("The start date cannot be greater than or equal to the end date")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_cel(start_date, end_date)
