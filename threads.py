import discord
import aiohttp
import json
import datetime

from typing import Union, Dict, Any

class APIException(Exception):
    pass

class Route:

    def __init__(self, method, url):
        self.method = method
        url = "https://discord.com/api/v9" + str(url)
        self.url = url

class Thread:

    def __init__(self, data):
        self._raw_data = data
        self.__update(data)

    def __update(self, data):
        self._thread_metadata = data["thread_metadata"]

        self.id = data["id"]
        self.guild_id = data["guild_id"]
        self.parent_id = data["parent_id"]
        self.owner_id = data["owner_id"]
        self.type = data["type"]
        self.name = data["name"]

        self.archived = self._thread_metadata["archived"]
        self.archive_timestamp = self._thread_metadata["archive_timestamp"]
        self.auto_archive_duration = self._thread_metadata["auto_archive_duration"]
        self.locked = self._thread_metadata["locked"]

        self.last_message_id = data.get("last_message_id", None)
        self.message_count = data.get("message_count", 0)
        self.member_count = data.get("member_count", 0)
        self.rate_limit_per_user = data.get("rate_limit_per_user", 0)
        self.member_ids_preview = data.get("member_ids_preview", [])

class ArchivedThreads:

    def __init__(self, data):
        self._raw_data = data
        self.__update(data)

    def __update(data):
        self.threads = [Thread(i) for i in data["threads"] if data["threads"] != []]
        self.has_more = data["has_more"]
        self.members = [ThreadMember(i) for i in data["members"] if data["members"] != []]

class ThreadMember:

    def __init__(self, data):
        self.__raw_data = data
        self.__update(data)

    def __update(self, data):
        self.thread_id = data["id"]
        self.flags = data["flags"]
        self.joined_at = data["join_timestamp"]
        self.user_id = data["user_id"]

async def json_or_text(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
    text = await response.text(encoding='utf-8')

    try:
        if response.headers['content-type'] == 'application/json':
            return await response.json()
    except:
        pass

    return text

class ThreadHTTP:

    def __init__(self, bot):
        self.bot = bot
        self.headers = {"Authorization": f"Bot {bot.http.token}", "User-Agent": "DiscordBot ()"}

        if hasattr(bot, "session") and isinstance(bot.session, aiohttp.ClientSession):
            self.session = bot.session
        else:
            self.session = aiohttp.ClientSession()

    ########################################################################
    ### --- Super Methods --- ###
    async def fetch_thread(self, thread_id: int):
        request = await self.get_thread(thread_id)
        return Thread(request)

    async def fetch_thread_members(self, thread_id: int):
        request = await self.get_thread_members(thread_id)
        return [ThreadMember(i) for i in request]

    async def fetch_active_threads(self, guild_id: int):
        request = await self.get_active_threads(guild_id)
        return [Thread(i) for i in request["threads"]]

    async def fetch_arvhied_public_threads(self, channel_id: int):
        request = await self.get_archived_public_threads(channel_id)
        return ArchivedThreads(request)

    async def fetch_archived_private_threads(self, channel_id: int):
        request = await self.get_archived_private_threads(channel_id)
        return ArchivedThreads(request)
    ########################################################################

    #request
    async def request(self, route: Route, data=None):
        async with self.session.request(route.method, route.url, headers=self.headers, json=data) as request:
            response = None

            if 300 > request.status >= 200:
                response = await json_or_text(request)
                return response
            else:
                raise APIException(f"Discord API returns {request.status} \n{response}")

    #get_thread
    def get_thread(self, thread_id: int):
        route = Route("GET", "/channels/" + str(thread_id))
        return self.request(route)

    #get_thread_members
    def get_thread_members(self, thread_id: int):
        route = Route("GET", "/channels/" + str(thread_id) + "/thread-members")
        return self.request(route)

    #get_active_threads
    def get_active_threads(self, guild_id: int):
        route = Route("GET", "/guilds/" + str(guild_id) + "/threads/active")
        return self.request(route)

    #get_archived_public_threads
    def get_archived_public_threads(self, channel_id: int):
        route = Route("GET", "/channels/" + str(channel_id) + "/threads/archived/public")
        return self.request(route)

    #get_archived_private_threads
    def get_archived_private_threads(self, channel_id: int):
        route = Route("GET", "/channels/" + str(channel_id) + "/threads/archived/private")
        return self.request(route)

    #create_thread
    def create_thread(self, channel_id: int, name: str, archive: int=1440):
        route = Route("POST", "/channels/" + str(channel_id) + "/threads")
        payload = {
            "name": name,
            "auto_archive_duration": archive,
            "type": 11
        }
        return self.request(route, payload)

    #create_thread_with_message
    def create_thread_with_message(self, channel_id: int, message_id: int, name: str, archive: int=1440):
        route = Route("POST", "/channels/" + str(channel_id) + "/messages/" + str(message_id) + "/threads")
        payload = {
            "name": name,
            "auto_archive_duration": archive,
            "type": 11
        }
        return self.request(route, payload)

    #create_private_thread
    def create_private_thread(self, channel_id: int, name: str, archive: int=1440):
        route = Route("POST", "/channels/" + str(channel_id) + "/threads")
        payload = {
            "name": name,
            "auto_archive_duration": archive,
        }
        return self.request(route, payload)

    #create_thread_with_message
    def create_private_thread_with_message(self, channel_id: int, message_id: int, name: str, archive: int=1440):
        route = Route("POST", "/channels/" + str(channel_id) + "/messages/" + str(message_id) + "/threads")
        payload = {
            "name": name,
            "auto_archive_duration": archive,
        }
        return self.request(route, payload)

    #edit_thread
    def edit_thread(self, thread_id: int, **kwargs):
        route = Route("PATCH", "/channels/" + str(thread_id))
        keys = ["name", "archived", "auto_archive_duration", "locked", "rate_limit_per_user"]
        payload = {k: v for k, v in kwargs.items() if k in keys}

        return self.request(route, payload)

    #archive_thread
    def archive_thread(self, thread_id: int):
        route = Route("PATCH", "/channels/" + str(thread_id))
        payload = {
            "archived": True
        }

        return self.request(route, payload)

    #add_member
    def add_member(self, thread_id: int, member_id: int):
        route = Route("PUT", "/channels/" + str(thread_id) + "/thread-members/" + str(member_id))
        return self.request(route)

    #remove_member
    def remove_member(self, thread_id: int, member_id: int):
        route = Route("DELETE", "/channels/" + str(thread_id) + "/thread-members/" + str(member_id))
        return self.request(route)

    #join_thread
    def join_thread(self, thread_id: int):
        route = Route("PUT", "/channels/" + str(thread_id) + "/thread-members/@me")
        return self.request(route)

    #leave_thread
    def leave_thread(self, thread_id: int):
        route = Route("DELETE", "/channels/" + str(thread_id) + "/thread-members/@me")
        return self.request(route)
