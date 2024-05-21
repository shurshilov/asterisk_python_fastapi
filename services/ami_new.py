# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging
import posixpath

import httpx
from asterisk.ami import AMIClient

from schemas.config_schema import AmiConfig

log = logging.getLogger("asterisk_agent")


class Ami:
    """AMI"""

    def __init__(
        self,
        ami_config: AmiConfig,
        api_key_base64: str,
        webhook_url: str,
    ) -> None:
        super().__init__()
        self.ami_config = ami_config
        self.api_key_base64 = api_key_base64
        self.webhook_url = webhook_url

    async def start_catch_events(self):
        try:
            self.client = AMIClient(address=self.ami_config.host, port=self.ami_config.port)
            self.client.login(username=self.ami_config.login, secret=self.ami_config.password)

            log.info("Create AMI listener...")
            self.client.add_event_listener(
                self.send_webhook_event, white_list=self.ami_config.events_used
            )

        except Exception as exc:
            log.exception("AMI start error: %s", exc)
            await self.start_catch_events()

    async def send_webhook_event(self, event, **kwargs):
        """send asterisk ami event to customer webhook url

        Arguments:
            payload -- asterisk event
        """
        try:
            log.info("AMI event:")
            log.info(event)
            # async with httpx.AsyncClient() as client:
            #     res = await client.post(
            #         posixpath.join(self.webhook_url, "ami"),
            #         json=payload,
            #         headers={
            #             "Authorization": f"Basic {self.api_key_base64}",
            #         },
            #     )
            #     res.raise_for_status()
        except Exception as exc:
            log.exception("Unknown AMI send_webhook_event error: %s", exc)
