# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging
import os
import urllib.parse

import aiofiles
from fastapi import APIRouter, Depends, Request, Response

from dependencies.auth import verify_basic_auth
from exceptions.exceptions import BusinessError
from schemas.config_schema import Config
from services.ari import Ari

log = logging.getLogger("asterisk_agent")
router = APIRouter(tags=["API"], dependencies=[Depends(verify_basic_auth)])


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
    path_file = ""
    log.info("Path recordings: %s", path_file)

    for root, dirnames, filenames in os.walk(config.path_recordings):
        for file_name in filenames:
            if file_name == filename:
                path_file = os.path.join(root, filename)
                break

    if not path_file:
        raise BusinessError("File not found")

    async with aiofiles.open(path_file, "rb") as file:
        recording = await file.read()

    return Response(
        headers={
            "Content-Disposition": f"Attachment" f""";filename={urllib.parse.quote(filename)}"""
        },
        media_type="application/octet-stream;charset=utf-8",
        content=recording,
    )
