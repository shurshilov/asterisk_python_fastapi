import logging
import posixpath
import httpx

log = logging.getLogger("asterisk_agent")


class Ari:
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
        try:
            async with httpx.AsyncClient() as client:
                path = f"endpoints?api_key={self.api_key}"
                r = await client.get(f"{posixpath.join(self.ari_url, path)}")
                r.raise_for_status()
                return r.text
        except Exception as e:
            log.exception("Unknown ari numbers error: %s", e)

    async def call_recording(self, id: str):
        """return ARI recorgings"""
        try:
            async with httpx.AsyncClient() as client:
                path = f"/recordings/stored/{id}/file?api_key={self.api_key}"
                r = await client.get(f"{posixpath.join(self.ari_url, path)}")
                r.raise_for_status()
                return r.content
        except Exception as e:
            log.exception("Unknown ari call_recording error: %s", e)
