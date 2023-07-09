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

from .. import loader, utils, main

import logging
import inspect

from telethon import functions, types
logger = logging.getLogger(__name__)
from telethon.tl.functions.channels import JoinChannelRequest



class HelpMod(loader.Module):
    """All help commands"""
    """Provides this help message"""
    strings = {"name": "Help",
               "bad_module": "<b>Invalid module name specified</b>",
               "single_mod_header": ("<b>Help for</b> <u>{}</u>:\nNote that the monospace text are the commands "
                                     "and they can be run with <code>{}&lt;command&gt;</code>"),
               "single_cmd": "\n• <code><u>{}</u></code>\n",
               "undoc_cmd": "There is no documentation for this command",
               "all_header": ("<b>Help for</b> <a href='https://t.me/friendlytgbot'>Friendly-Telegram</a>\n"
                              "For more help on how to use a command, type <code>{}help &lt;module name&gt;</code>\n\n"
                              "<b>Available Modules:</b>"),
               "mod_tmpl": "\n• <b>{}</b>",
               "first_cmd_tmpl": ": <code>{}",
               "cmd_tmpl": ", {}",
               "footer": ("\n\nYou can <b>read more</b> about most commands "
                          "<a href='https://friendly-telegram.gitlab.io'>here</a>"),
               "joined": "<b>Joined to</b> <a href='https://t.me/friendlytgbot'>support channel</a>",
               "join": "<b>Join the</b> <a href='https://t.me/friendlytgbot'>support channel</a>"}



        
    async def supportcmd(self, message):
        """Joins the support chat"""
        await self.client(JoinChannelRequest("https://t.me/friendlytgbot"))
        await message.edit(_("<code>Join to</code> <a href='https://t.me/friendlytgbot'>support chat</a>"))

    async def client_ready(self, client, db):
        self.client = client
        self.is_bot = await client.is_bot()
        self.db = db
   
        
    async def helpcmd(self, message):
        """Help for all available modules"""
        raph = "<b>Available Commands in RaphielGang section:<b>\n"
        uni = "<b>Available Commands in Uniborg section:<b>\n"
        ftg = "<b>Available Commands in Friendly-Telegram section:</b>\n"
        all = "<b>Available Commands:</b>\n"
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(
            "<b>Please choose a section to see your modules:</b>"
            "\n\n\n<b>.help raph:</b><i> Shows all your PP and PPE originated modules.</i>\n"
            "\n<b>.help uni:</b><i> Shows all your Uniborg originated modules.</i>\n"
            "\n<b>.help ftg:</b><i> Shows all your native modules.</i>\n"
            "\n<b>.help all:</b><i> Shows all your modules.</i>")
            return
        for mod in self.allmodules.modules:
            if mod.name.find("RaphielGang") != -1:
                raph += "\n\n<b>" + mod.name + "</b>: "
                for cmd in mod.commands:
                    raph += "<i>" + cmd + "</i>, "
                raph = raph[:-2:]
                raph = raph.replace("Raphielgang Configuration Placeholder:", "")
            if mod.name.find("UniBorg") != -1:
                uni += "\n\n<b>" + mod.name + "</b>: "
                for cmd in mod.commands:
                    uni += "<i>" + cmd + "</i>, "
                uni = uni[:-2:]
                uni = uni.replace("Uniborg Configuration Placeholder:", "")
            if mod.name.find("UniBorg") == -1 and mod.name.find("RaphielGang") == -1:
                ftg += "\n\n<b>" + mod.name + "</b>: "
                for cmd in mod.commands:
                    ftg += "<i>" + cmd + "</i>, "
                ftg = ftg[:-2:]
                ftg = ftg.replace("Raphielgang Configuration Placeholder:", "")
                ftg = ftg.replace("Uniborg Configuration Placeholder:", "")
            all += "\n\n<b>" + mod.name + "</b>: "
            for cmd in mod.commands:
                all += "<i>" + cmd + "</i>, "
            all = all[:-2:]
        if args == "uni":
            await message.edit(uni)
            return
        if args == "raph":
            await message.edit(raph)
            return
        if args == "ftg":
            await message.edit(ftg)
            return
        if args == "all":
            await message.edit(all)
            return
        else:
            module = None
            for mod in self.allmodules.modules:
                if mod.strings("name", message).lower() == args.lower():
                    module = mod

            if module is None:
                await message.edit("<code>" + "Invalid module name specified" + "</code>")
                return
        try:
            name = module.strings("name", message)
        except KeyError:
            name = getattr(module, "name", "ERROR")

        reply = self.strings("single_mod_header", message).format(utils.escape_html(name),utils.escape_html((self.db.get(main.__name__,"command_prefix",False) or ".")[0]))

        if module.__doc__:
                reply += "\n" + "\n".join("  " + t for t in utils.escape_html(inspect.getdoc(module)).split("\n"))
        else:
            logger.warning("Module %s is missing docstring!", module)
        commands = {name: func for name, func in module.commands.items()
                    if await self.allmodules.check_security(message, func)}
        for name, fun in commands.items():
            reply += self.strings("single_cmd", message).format(name)
            if fun.__doc__:
                reply += utils.escape_html("\n".join("  " + t for t in inspect.getdoc(fun).split("\n")))
            else:
                reply += self.strings("undoc_cmd", message)
        
        await utils.answer(message, reply)

