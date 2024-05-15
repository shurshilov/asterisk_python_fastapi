# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging
import posixpath
import urllib.parse

import httpx

log = logging.getLogger("asterisk_agent")


class Ari:
    """ARI (Asterisk REST FULL INTERFACE)"""

    def __init__(
        self,
        ari_url: str,
        api_key: str,
    ) -> None:
        super().__init__()
        self.ari_url = ari_url
        self.api_key = api_key

    async def numbers(self):
        """return ARI endpoints

        Returns:
            [{
                "technology": "SIP",
                "resource": "308",
                "state": "offline",
                "channel_ids": []
            },
            {
                "technology": "SIP",
                "resource": "9624032060_out",
                "state": "online",
                "channel_ids": []
            }
            ]
        """
        async with httpx.AsyncClient() as client:
            path = "endpoints"

            response = await client.get(
                f"{posixpath.join(self.ari_url, path)}",
                params={"api_key": self.api_key},
            )
            response.raise_for_status()
            return response.text

    async def call_recording(self, filename: str):
        """return ARI recorgings"""
        async with httpx.AsyncClient() as client:
            path = urllib.parse.quote(f"/recordings/stored/{filename}/file")

            response = await client.get(
                f"{posixpath.join(self.ari_url, path)}",
                params={"api_key": self.api_key},
            )
            response.raise_for_status()
            return response.content
