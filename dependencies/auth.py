# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

from typing import Annotated
from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from exceptions.exceptions import AuthError
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
        raise AuthError(detail="Not authenticated")
