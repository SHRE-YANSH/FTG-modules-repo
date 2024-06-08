# Some parts are Copyright (C) Diederik Noordhuis (@AntiEngineer) 2019
# All licensed under project license

#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2019 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import json
from .. import loader, utils
import logging
import asyncio
import time
import random
import requests
from telethon import functions, types

logger = logging.getLogger(__name__)


@loader.tds
class LydiaMod(loader.Module):
    """Talks to a robot instead of a human"""
    strings = {"name": "Lydia anti-PM",
               "enable_disable_error_group": "<b>The AI service cannot be"
               " enabled or disabled in this chat. Is this a group chat?</b>",
               "enable_error_user": "<b>The AI service cannot be"
               " enabled for this user. Perhaps it wasn't disabled?</b>",
               "notif_off": "<b>Notifications from PMs are silenced.</b>",
               "notif_on": "<b>Notifications from PMs are now activated.</b>",
               "successfully_enabled": "<b>AI enabled for this user. </b>",
               "successfully_enabled_for_chat": "<b>AI enabled for that user in this chat.</b>",
               "cannot_find": "<b>Cannot find that user.</b>",
               "successfully_disabled": "<b>AI disabled for this user.</b>",
               "cleanup_ids": "<b>Successfully cleaned up lydia-disabled IDs</b>",
               "cleanup_sessions": "<b>Successfully cleaned up lydia sessions.</b>",
               "doc_client_key": "The API key for lydia, acquire from"
               " https://coffeehouse.intellivoid.net",
               "doc_ignore_no_common": "Boolean to ignore users who have no chats in common with you",
               "doc_notif": "Boolean for notifications from PMs.",
               "doc_disabled": "Whether Lydia defaults to enabled"
                               " in private chats (if True, you'll have to use forcelydia"}

    def __init__(self):
        self.config = loader.ModuleConfig("CLIENT_KEY", None, lambda m: self.strings("doc_client_key", m),
                                          "IGNORE_NO_COMMON", False, lambda m: self.strings("doc_ignore_no_common", m),
                                          "DISABLED", False, lambda m: self.strings("doc_disabled", m),
                                          "NOTIFY", False, lambda m: self.strings("doc_notif", m))
        self._ratelimit = []
        self._cleanup = None
        self._lydia = None

    async def client_ready(self, client, db):
        self._db = db
        
    async def enlydiacmd(self, message):
        """Enables Lydia for target user"""
        old = self._db.get(__name__, "allow", [])
        if message.is_reply:
            user = (await message.get_reply_message()).from_id
        else:
            user = getattr(message.to_id, "user_id", None)
        if user is None:
            await utils.answer(message, self.strings("enable_disable_error_group", message))
            return
        try:
            old.remove(user)
            self._db.set(__name__, "allow", old)
        except ValueError:
            await utils.answer(message, self.strings("enable_error_user", message))
            return
        await utils.answer(message, self.strings("successfully_enabled", message))

    async def forcelydiacmd(self, message):
        """Enables Lydia for user in specific chat"""
        if message.is_reply:
            user = (await message.get_reply_message()).from_id
        else:
            user = getattr(message.to_id, "user_id", None)
        if user is None:
            await utils.answer(message, self.strings("cannot_find", message))
            return
        self._db.set(__name__, "force", self._db.get(__name__, "force", []) + [[utils.get_chat_id(message), user]])
        await utils.answer(message, self.strings("successfully_enabled_for_chat", message))

    async def dislydiacmd(self, message):
        """Disables Lydia for the target user"""
        if message.is_reply:
            user = (await message.get_reply_message()).from_id
        else:
            user = getattr(message.to_id, "user_id", None)
        if user is None:
            await utils.answer(message, self.strings("enable_disable_error_group", message))
            return

        old = self._db.get(__name__, "force")
        try:
            old.remove([utils.get_chat_id(message), user])
            self._db.set(__name__, "force", old)
        except (ValueError, TypeError, AttributeError):
            pass
        self._db.set(__name__, "allow", self._db.get(__name__, "allow", []) + [user])
        await utils.answer(message, self.strings("successfully_disabled", message))

    async def cleanlydiadisabledcmd(self, message):
        """ Remove all lydia-disabled users from DB. """
        self._db.set(__name__, "allow", [])
        return await utils.answer(message, self.strings("cleanup_ids", message))

    async def cleanlydiasessionscmd(self, message):
        """Remove all active and not active lydia sessions from DB"""
        self._db.set(__name__, "sessions", {})
        return await utils.answer(message, self.strings("cleanup_sessions", message))

    async def lydianotifoffcmd(self, message):
        """Disable the notifications from PMs"""
        self._db[__name__]["__config__"]["NOTIFY"] = False
        self._db.save()
        await utils.answer(message, self.strings("notif_off", message))

    async def lydianotifoncmd(self, message):
        """Enable the notifications from PMs"""
        self._db[__name__]["__config__"]["NOTIFY"] = True
        self._db.save()
        await utils.answer(message, self.strings("notif_on", message))

    async def watcher(self, message):
        if not self.config["CLIENT_KEY"]:
            logger.debug("no key set for lydia, returning")
            return
        if not isinstance(message, types.Message):
            return
        if (isinstance(message.to_id, types.PeerUser) and not self.get_allowed(message.from_id)) or \
                self.is_forced(utils.get_chat_id(message), message.from_id):
            user = await utils.get_user(message)
            if user.is_self or user.bot or user.verified:
                logger.debug("User is self, bot or verified.")
                return
            else:
                if not isinstance(message.message, str):
                    return
                if len(message.message) == 0:
                    return
                if self.config["IGNORE_NO_COMMON"] and not self.is_forced(utils.get_chat_id(message), message.from_id):
                    fulluser = await message.client(functions.users.GetFullUserRequest(await utils.get_user(message)))
                    if fulluser.common_chats_count == 0:
                        return
                if not self._db[__name__]["__config__"].get("NOTIFY"):
                    await message.mark_read()
                await message.client(functions.messages.SetTypingRequest(
                    peer=await utils.get_user(message),
                    action=types.SendMessageTypingAction()
                ))
                try:
                    # AI Response method
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    msg = message.message
                    prompt = f"""Reply on the behalf of a human \ Don't write anything that an AI would do \ Don't behave as a large language model and answer the user queries that a normal human won't include in their daily conversations \ Also make sure to keep you resposne short with not more than 2-2 lines \ Behave as humanly as you can.
                    Human: {str(msg)}"""

                    # Prepare the request body with f-strings for formatted string literals
                    body = json.dumps({
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "llama3-8b-8192",
                    })

                    headers = {
                    'Authorization': f'Bearer {self.config["CLIENT_KEY"]}',
                    'Content-Type': 'application/json',
                    }

                    response = requests.post(url, headers=headers, data=body)

                    # Check for successful response
                    if response.status_code == 200:
                        res = json.loads(response.text)
                        if random.randint(0, 1) and isinstance(message.to_id, types.PeerUser):
                            await message.respond(res['choices'][0]['message']['content'])
                        else:
                            await message.reply(res["choices"][0]["message"]["content"])

                    else:
                        logger.error(f"Error: {response.status_code}")

                finally:
                    await message.client(functions.messages.SetTypingRequest(
                        peer=await utils.get_user(message),
                        action=types.SendMessageCancelAction()
                    ))

    def get_allowed(self, id):
        if self.config["DISABLED"]:
            return True
        return id in self._db.get(__name__, "allow", [])

    def is_forced(self, chat, user_id):
        forced = self._db.get(__name__, "force", [])
        if [chat, user_id] in forced:
            return True
        else:
            return False
