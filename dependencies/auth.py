# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from schemas.config_schema import Config

security = HTTPBasic()


async def verify_basic_auth(
    req: Request, credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    """Classical HTTP Basic auth"""
    config: Config = req.app.state.config
    if (
        credentials.username != config.ari_login
        or credentials.password != config.ari_password
    ):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
