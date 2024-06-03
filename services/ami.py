# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import logging
import posixpath

import requests
from panoramisk import Manager

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
        self.connected = False
        self.disconnect_count = 0

    async def start_catch_events(self):
        try:
            self.client = Manager(
                host=self.ami_config.host,
                port=self.ami_config.port,
                username=self.ami_config.login,
                secret=self.ami_config.password,
                on_login=self.on_login,
                on_connect=self.on_connect,
                on_disconnect=self.on_disconnect,
                ping_delay=5,
                ping_interval=5,
                reconnect_timeout=2,
            )

            log.info("AMI create async task...")
            for event in self.ami_config.events_used:
                log.info("AMI register event: %s", event)
                self.client.register_event(event, self.send_webhook_event)

            return self.client.connect(run_forever=False, on_shutdown=self.on_shutdown)

        except Exception as exc:
            log.exception("AMI start error: %s", exc)

    def on_login(self, mngr):
        log.info("AMI succesfull login")

    def on_disconnect(self, mngr, exc):
        log.info("AMI disconnect, error: %s", exc)
        self.connected = False
        self.disconnect_count += 1

    def on_connect(self, mngr):
        log.info("AMI succesfull connected")
        self.connected = True

    async def on_shutdown(self, mngr):
        log.info("AMI shutdown...")

    def send_webhook_event(self, manager, payload: dict):
        """send asterisk ami event to customer webhook url

        Arguments:
            payload -- asterisk event
        """
        try:
            log.info("AMI event:")
            log.info(payload)
            res = requests.post(
                posixpath.join(self.webhook_url, "ami"),
                json=dict(payload),
                headers={
                    "Authorization": f"Basic {self.api_key_base64}",
                },
            )
            res.raise_for_status()
        except Exception as exc:
            log.exception("Unknown AMI send_webhook_event error: %s", exc)
