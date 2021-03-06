"""
This is a asyncio wrapper for the matrix API class.
"""
import json
from asyncio import sleep
from urllib.parse import quote

from matrix_client.api import MatrixHttpApi
from matrix_client.errors import MatrixError, MatrixRequestError


class AsyncHTTPAPI(MatrixHttpApi):
    """
    Contains all raw matrix HTTP client-server API calls using asyncio and coroutines.

    Usage:
        async def main():
            async with aiohttp.ClientSession() as session:
                mapi = AsyncHTTPAPI("http://matrix.org", session)
                resp = await mapi.get_room_id("#matrix:matrix.org")
                print(resp)


        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    """

    def __init__(self, base_url, client_session, token=None):
        self.base_url = base_url
        self.token = token
        self.txn_id = 0
        self.validate_cert = True
        self.client_session = client_session

    async def _send(self,
                    method,
                    path,
                    content=None,
                    query_params={},
                    headers={},
                    api_path="/_matrix/client/r0"):
        if not content:
            content = {}

        method = method.upper()
        if method not in ["GET", "PUT", "DELETE", "POST"]:
            raise MatrixError("Unsupported HTTP method: %s" % method)

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if self.token:
            query_params["access_token"] = self.token
        endpoint = self.base_url + api_path + path

        if headers["Content-Type"] == "application/json":
            content = json.dumps(content)

        while True:
            request = self.client_session.request(
                method,
                endpoint,
                params=query_params,
                data=content,
                headers=headers)
            async with request as response:
                if response.status == 429:
                    respjson = await response.json()
                    await sleep(respjson['retry_after_ms'] / 1000)
                elif response.status < 200 or response.status >= 300:
                    raise MatrixRequestError(
                        code=response.status, content=await response.text())
                else:
                    return await response.json()

    async def get_display_name(self, user_id):
        content = await self._send("GET", "/profile/%s/displayname" % user_id)
        return content.get('displayname', None)

    async def set_display_name(self, user_id, display_name):
        content = {"displayname": display_name}
        await self._send("PUT", "/profile/%s/displayname" % user_id, content)

    async def get_avatar_url(self, user_id):
        content = await self._send("GET", "/profile/%s/avatar_url" % user_id)
        return content.get('avatar_url', None)

    async def get_room_id(self, room_alias):
        """Get room id from its alias

        Args:
            room_alias(str): The room alias name.

        Returns:
            Wanted room's id.
        """
        content = await self._send(
            "GET",
            "/directory/room/{}".format(quote(room_alias)),
            api_path="/_matrix/client/r0")
        return content.get("room_id", None)

    async def get_room_displayname(self, room_id, user_id):
        """Get a users displayname for the given room"""
        if room_id.startswith('#'):
            room_id = await self.get_room_id(room_id)

        members = await self.get_room_members(room_id)
        members = members['chunk']
        for mem in members:
            if mem['sender'] == user_id:
                return mem['content']['displayname']

