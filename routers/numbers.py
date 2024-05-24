# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import json
import logging

from fastapi import APIRouter, Depends, Request

from dependencies.auth import verify_basic_auth
from services.ari import Ari
from services.database import MysqlStrategy, PostgresqlStrategy, SqliteStrategy

log = logging.getLogger("asterisk_agent")
router = APIRouter(tags=["API"], dependencies=[Depends(verify_basic_auth)])


@router.get("/api/numbers/ring_groups/")
async def ring_groups(req: Request):
    """Return ring_groups"""
    log.info("RING GROUPS")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_ring_groups()


@router.get("/api/numbers/queues_config/")
async def queues_config(req: Request):
    """Return queues_config"""
    log.info("QUEUES CONFIG")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_queues_config()


@router.get("/api/numbers/redirects/")
async def redirects(req: Request):
    """Return redirects"""
    log.info("REDIRECTS")

    connector_database: PostgresqlStrategy | MysqlStrategy | SqliteStrategy = (
        req.app.state.connector_database
    )

    return await connector_database.get_findmefollow()


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
