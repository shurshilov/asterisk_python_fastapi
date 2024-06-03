# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

import asyncio
import datetime
import json
import logging

import httpx
import websockets

from schemas.config_schema import AriConfig

log = logging.getLogger("asterisk_agent")


class WebsocketEvents:
    """
    Websocket client.
    Catch events from Asterisk and send it to customer webhook url.

    Singleton design pattern (generative pattern).
    Ensuring the creation of one and only one class object.
    """

    answer_last_message_time = ""
    answer_last_message = {}
    no_answer_last_message_time = ""
    no_answer_last_message = {}
    last_connected_time = ""
    last_try_connected_time = ""
    connected = False
    disconnected_reason = ""
    disconnected_time = ""
    disconnect_count = 0

    def __init__(
        self,
        api_key_base64: str,
        api_key: str,
        ari_config: AriConfig,
        webhook_url: str,
        timeout: int,
    ) -> None:
        super().__init__()
        websocket_url = f"{ari_config.wss}".rstrip("/")
        self.api_key_base64 = api_key_base64

        self.websocket_url = (
            f"{websocket_url}?api_key={api_key}&app=AsteriskAgentPython&subscribeAll=true"
        )
        self.webhook_url = webhook_url
        self.timeout = timeout

        self.webhook_events_ignore = ari_config.events_ignore
        self.webhook_events_used = ari_config.events_used

    async def send_webhook_event(self, payload: dict):
        """send asterisk ari event to customer webhook url

        Arguments:
            payload -- asterisk event
        """
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={
                        "Authorization": f"Basic {self.api_key_base64}",
                    },
                )
                res.raise_for_status()
        except Exception as exc:
            log.exception("Unknown send_webhook_event error: %s", exc)

    # async def subscribe(self):
    #     try:
    #         async with httpx.AsyncClient() as client:
    #             path = f"applications/AsteriskAgentPython/subscription?api_key={self.api_key}"
    #             r = await client.post(
    #                 f"{posixpath.join(self.ari_url, path)}",
    #                 data={"eventSource": "channel:ChannelCreated,ChannelDestroyed"},
    #             )
    #             r.raise_for_status()
    #             return r.text
    #     except Exception as e:
    #         log.exception("Unknown send_webhook_event error: %s", e)

    async def start_consumer(self):
        """
        ChannelTalkingFinished
            asterisk_id: string (optional) - The unique ID for the Asterisk
                instance that raised this event.
            type: string - Indicates the type of this message.
            application: string - Name of the application receiving the event.
            timestamp: Date - Time at which this event was created.
            channel: [Channel|#Channel] - The channel on which talking completed.
            duration: int - The length of time, in milliseconds,
                that talking was detected on the channel

        ChannelTalkingStarted
            asterisk_id: string (optional) - The unique ID for the Asterisk
                instance that raised this event.
            type: string - Indicates the type of this message.
            application: string - Name of the application receiving the event.
            timestamp: Date - Time at which this event was created.
            channel: [Channel|#Channel] - The channel on which talking started.

            Channel
                accountcode: string
                caller: [CallerID|#CallerID]
                channelvars: [object|#object] (optional) - Channel variables
                connected: [CallerID|#CallerID]
                creationtime: Date - Timestamp when channel was created
                dialplan: [DialplanCEP|#DialplanCEP] - Current location
                    in the dialplan
                id: string - Unique identifier of the channel.

                CallerID
                    name: string
                    number: string
                DialplanCEP
                    app_data: string - Parameter of current dialplanapplication
                    app_name: string - Name of current dialplan application
                    context: string - Context in the dialplan
                    exten: string - Extension in the dialplan
                    priority: long - Priority in the dialplan
        Sample:
            {
            "type":"ChannelCreated",
            "timestamp":"2024-05-11T16:04:53.044+0300",
            "channel":{
                "id":"1715432693.70626",
                "name":"SIP/9222222222_out-000080ca",
                "state":"Down",
                "caller":{
                    "name":"",
                    "number":"+79111111111"
                },
                "connected":{
                    "name":"",
                    "number":""
                },
                "accountcode":"",
                "dialplan":{
                    "context":"from-trunk-sip-9222222222_out",
                    "exten":"9222222222",
                    "priority":1,
                    "app_name":"",
                    "app_data":""
                },
                "creationtime":"2024-05-11T16:04:53.044+0300",
                "language":"en"
            },
            "asterisk_id":"52:54:00:02:46:7d",
            "application":"AsteriskAgentPython"
            }

            {
            "type":"ChannelDestroyed",
            "timestamp":"2024-05-11T17:18:13.438+0300",
            "cause":16,
            "cause_txt":"Normal Clearing",
            "channel":{
                "id":"1715437081.70636",
                "name":"SIP/9222222222_out-000080ce",
                "state":"Ringing",
                "caller":{
                    "name":"<unknown>",
                    "number":"79111111111"
                },
                "connected":{
                    "name":"",
                    "number":"9222222222"
                },
                "accountcode":"",
                "dialplan":{
                    "context":"from-trunk-sip-9222222222_out",
                    "exten":"79111111111",
                    "priority":1,
                    "app_name":"AppDial",
                    "app_data":"(Outgoing Line)"
                },
                "creationtime":"2024-05-11T17:18:01.177+0300",
                "language":"ru"
            },
            "asterisk_id":"52:54:00:02:46:7d",
            "application":"AsteriskAgentPython"
            }
        """
        try:
            self.last_try_connected_time = str(datetime.datetime.now())
            async with websockets.connect(self.websocket_url) as websocket:
                self.connected = True
                self.last_connected_time = str(datetime.datetime.now())
                log.info("Connected to ARI websocket server succesfully")
                # subscribe = await self.send_subscribe()
                # log.info(subscribe)

                while True:
                    message = await websocket.recv()
                    message_json = json.loads(message)
                    if message_json["type"] in self.webhook_events_ignore:
                        continue

                    log.info("Received: %s", message)

                    if self.webhook_events_used:
                        if message_json["type"] not in self.webhook_events_used:
                            continue

                    self.answer_last_message_time = str(datetime.datetime.now())
                    self.answer_last_message = message_json

                    await self.send_webhook_event(payload=message_json)

        except asyncio.CancelledError:
            log.info("graceful stop webscoket client start_consumer")
            await websocket.close()
        except Exception as exc:
            log.exception("Unknown start_consumer error: %s", exc)
            self.connected = False
            self.disconnect_count += 1
            self.disconnected_reason = str(exc)
            self.disconnected_time = str(datetime.datetime.now())
            await asyncio.sleep(self.timeout)
            await self.start_consumer()
