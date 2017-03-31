# coding=utf-8
import aiohttp
import asyncio
import discord
import yaml

import json
import os

from aiohttp import ServerDisconnectedError
from discord import Object, Embed, Colour, Member
from discord import Status

from bot.interpreter import Interpreter
from bot.utils import get_logger, save_attachment, slugify

log = get_logger("bot")

__author__ = 'Gareth Coles'


class Client(discord.client.Client):
    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)

        self.banned_ids = []
        self.config = yaml.load(open("config.yml", "r"))

        self.load_banned_ids()
        self.interpreter = Interpreter(locals(), self)

    def has_feature(self, feature):
        return feature.lower() in self.config["features"]

    def load_banned_ids(self):
        if not os.path.exists("banned.json"):
            self.save_banned_ids()

        with open("banned.json", "r") as fh:
            self.banned_ids = json.loads(fh.read())

    def save_banned_ids(self):
        with open("banned.json", "w") as fh:
            fh.write(json.dumps(self.banned_ids))

    async def on_ready(self):
        if hasattr(Status, self.config["status"]):
            self.change_presence(status=getattr(Status, self.config["status"]))
        else:
            log.warning("Unknown status: {} - defaulting to Do Not Disturb".format(self.config["status"]))
            self.change_presence(status=Status.do_not_disturb)

    async def on_message(self, message):
        if message.server is None:
            logger = get_logger("Private Messages")
        else:
            logger = get_logger(message.server.name)

        if int(message.author.id) == self.user.id:
            if self.has_feature("logs") and message.content.lower().startswith("/logs"):
                _triggered_message = message
                await self.edit_message(_triggered_message, "Saving all previous messages for the channel...")

                logger.info("Retrieving messages...")

                current_index = None
                num_errors = 0
                chunk_number = 0

                message_chunks = []

                while current_index != -1:
                    if num_errors >= 5:
                        logger.critical("Too many errors; aborting and saving what we have.")
                        break

                    chunk_number += 1
                    current_message_chunk = []

                    try:
                        async for message in self.logs_from(message.channel, before=current_index):
                            current_message_chunk.append(message)
                    except ServerDisconnectedError:
                        try:
                            async for message in self.logs_from(message.channel, before=current_index):
                                current_message_chunk.append(message)
                        except Exception as e:
                            logger.error("Unable to get chunk {}: {}".format(chunk_number, e))
                            num_errors += 1
                            continue
                    except Exception as e:
                        logger.error("Unable to get chunk {}: {}".format(chunk_number, e))
                        num_errors += 1
                        continue

                    logger.info("Got chunk: {}".format(chunk_number))

                    if len(current_message_chunk) <= 0:
                        break

                    logger.info("Last message: <{}#{}> {}".format(
                        current_message_chunk[-1].author.name,
                        current_message_chunk[-1].author.discriminator,
                        current_message_chunk[-1].clean_content
                    ))

                    message_chunks.append(current_message_chunk)
                    current_index = current_message_chunk[-1]

                logger.info("Found {} message chunks.".format(len(message_chunks)))

                total_messages = 0

                if message.channel is not None:
                    filename = "{}.log".format(slugify(message.channel.name))
                else:
                    filename = "private-message.log"

                with open(filename, "w", encoding="utf-8") as fh:
                    for chunk in reversed(message_chunks):
                        for message in reversed(chunk):
                            total_messages += 1

                            fh.write("{} | <{}#{}> {}\n".format(
                                message.timestamp.strftime("%d %b %Y | %H:%M:%S (UTC)"),
                                message.author.name, message.author.discriminator, message.clean_content
                            ))

                del message_chunks

                logger.info("Written {} messages.".format(total_messages))

                await self.edit_message(_triggered_message, "Saved {} messages. Uploading...".format(total_messages))

                try:
                    with open(filename, "r") as fh:
                        data = {
                            "description": "",
                            "public": False,
                            "files": {
                                filename: {
                                    "content": fh.read()
                                }
                            }
                        }

                    session = aiohttp.ClientSession()
                    response = await session.post("https://api.github.com/gists", data=json.dumps(data))
                    result = await response.json()
                    session.close()

                    if response.status == 201:
                        await self.edit_message(_triggered_message, "Saved {} messages. <{}>".format( total_messages, result["html_url"]))
                    else:
                        await self.edit_message(_triggered_message, "Saved {} messages. Unable to upload: `{}`".format(total_messages, result["message"]))
                except Exception as e:
                    logger.exception("Failed to upload.")
                    await self.edit_message(_triggered_message, "Saved {} messages. Unable to upload: `{}`".format( total_messages, e))

            elif self.has_feature("repost") and message.content.lower().startswith("/repost"):
                split = message.content.split(" ")

                if len(split) > 1:
                    try:
                        message_id = int(split[1])

                        if len(split) == 2:
                            channel = message.channel
                        else:
                            channel = self.get_channel(split[2])

                            if channel is None:
                                await asyncio.sleep(1)
                                await self.edit_message(
                                    message,
                                    "No such channel: `{}`".format(split[2])
                                )

                        try:
                            messages = []

                            async for got_message in self.logs_from(channel, limit=1, before=Object(str(message_id + 1))):
                                messages.append(got_message)

                            if len(messages) < 1:
                                await asyncio.sleep(1)
                                await self.edit_message(
                                    message,
                                    "Error: Failed to get message `{}`, either the message doesn't exist or Discord fixed the dang exploit.".format(
                                        message_id
                                    )
                                )
                            else:
                                got_message = messages[0]

                                if str(message_id) != got_message.id:
                                    await asyncio.sleep(1)
                                    await self.edit_message(
                                        message,
                                        "Error: Wanted message `{}`, got `{}`".format(message_id, got_message.id)
                                    )
                                else:
                                    await asyncio.sleep(1)
                                    await self.edit_message(
                                        message,
                                        "**Message by {} at {}**\n\n{}".format(
                                            got_message.author.mention,
                                            got_message.timestamp.strftime(
                                                "%d %b %Y | %H:%M:%S (UTC)"
                                            ),
                                            got_message.content
                                        )
                                    )
                        except discord.NotFound:
                            await asyncio.sleep(1)
                            await self.edit_message(
                                message,
                                "No such message: `{}`".format(message_id)
                            )
                    except Exception as e:
                        await asyncio.sleep(1)
                        await self.edit_message(
                            message,
                            "Error reposting message `{}`: {}".format(
                                split[1], e
                            )
                        )
                else:
                    await asyncio.sleep(1)
                    await self.edit_message(
                        message, "Usage: `/repost <message id> [channel_id]`"
                    )

            elif self.has_feature("quote") and message.content.lower().startswith("/quote"):
                lines = message.content.split("\n")
                split = lines[0].split(" ") if lines else ""

                if len(lines) >= 1 and len(split) > 1:
                    try:
                        message_id = int(split[1])
                        channel = message.channel

                        try:
                            messages = []

                            async for got_message in self.logs_from(channel, limit=1, before=Object(str(message_id + 1))):
                                messages.append(got_message)

                            if len(messages) < 1:
                                await asyncio.sleep(1)
                                await self.edit_message(
                                    message,
                                    "Error: Failed to get message `{}`, either the message doesn't exist or Discord fixed the dang exploit.".format(
                                        message_id
                                    )
                                )
                            else:
                                got_message = messages[0]

                                if str(message_id) != got_message.id:
                                    await asyncio.sleep(1)
                                    await self.edit_message(
                                        message,
                                        "Error: Wanted message `{}`, got `{}`".format(message_id, got_message.id)
                                    )
                                else:
                                    if isinstance(got_message.author, Member):
                                        if got_message.author.color:
                                            embed_col = got_message.author.colour
                                        else:
                                            embed_col = Colour.gold()
                                    else:
                                        embed_col = Colour.gold()

                                    embed = Embed(
                                        colour=embed_col,
                                        title="Quote by {} | {}".format(
                                            got_message.author.display_name,
                                            got_message.timestamp.strftime(
                                                "%d %b %Y | %H:%M:%S (UTC)"
                                            )
                                        ),
                                        description=got_message.content
                                    )

                                    await asyncio.sleep(1)
                                    await self.delete_message(message)
                                    await self.send_message(
                                        message.channel,
                                        "\n".join(lines[1:]) if len(lines) > 1 else "",
                                        embed=embed
                                    )
                        except discord.NotFound:
                            await asyncio.sleep(1)
                            await self.edit_message(
                                message,
                                "No such message: `{}`".format(message_id)
                            )
                    except Exception as e:
                        await asyncio.sleep(1)
                        await self.edit_message(
                            message,
                            "Error quoting message `{}`: {}".format(
                                split[1], e
                            )
                        )
                else:
                    await asyncio.sleep(1)
                    await self.edit_message(
                        message, "Usage: \n"
                                 "```\n"
                                 "/quote <message id> \n"
                                 "[extra context]\n"
                                 "```\n"
                    )

            elif self.has_feature("eval") and message.content.lower().startswith("/eval"):
                code = message.content.lstrip("/eval").strip(" ")

                if code.startswith("```") and code.endswith("```"):
                    if code.startswith("```python"):
                        code = code[9:-3]
                    elif code.startswith("```py"):
                        code = code[5:-3]
                    else:
                        code = code[3:-3]
                elif code.startswith("`") and code.endswith("`"):
                    code = code[1:-1]

                code = code.strip().strip("\n")

                lines = []

                def output(line):
                    lines.append(line)

                self.interpreter.set_output(output)

                try:
                    rvalue = await self.interpreter.runsource(code, message)
                except Exception as e:
                    await self.edit_message(
                        message,
                        "**Error**\n ```{}```\n\n**Code** \n```py\n{}\n```".format(
                            e, code
                        )
                    )
                else:
                    out_message = "**Returned** \n```py\n{}\n```\n\n".format(repr(rvalue))

                    if lines:
                        out_message += "**Output** \n```\n{}\n```\n\n".format(
                            "\n".join(lines)
                        )

                    out_message += "**Code** \n```py\n{}\n```".format(code)

                    await asyncio.sleep(1)
                    await self.edit_message(
                        message, out_message
                    )

            elif self.has_feature("attachments") and message.content.lower().replace("'", "").startswith("/dontsavemebro"):
                split = message.content.split(" ", 1)
                if len(split) > 1:
                    user_id = split[1]

                    try:
                        int(user_id)
                    except ValueError:
                        await asyncio.sleep(1)
                        await self.edit_message(
                            message, "Invalid ID: {}".format(user_id)
                        )
                    else:
                        if user_id in self.banned_ids:
                            await asyncio.sleep(1)
                            await self.edit_message(
                                message, "ID already ignored: {}".format(user_id)
                            )
                        else:
                            self.banned_ids.append(user_id)
                            self.save_banned_ids()

                            await asyncio.sleep(1)
                            await self.edit_message(
                                message, "ID added to ignore list: {}".format(user_id)
                            )
                else:
                    await asyncio.sleep(1)
                    await self.edit_message(
                        message, "Usage: `/dontsavemebro <user ID>`"
                    )

        user = "{}#{}".format(
            message.author.name, message.author.discriminator
        )

        for line in message.content.split("\n"):
            if message.channel.is_private:
                logger.info("{} {}".format(
                    user, line
                ))
            else:
                logger.info("#{} / {} {}".format(
                    message.channel.name,
                    user, line
                ))

        if not self.has_feature("attachments"):
            pass
        elif message.author.id in self.banned_ids:
            logger.info("Ignored attachment from {}".format(user))
        else:
            for attachment in message.attachments:
                if message.server is not None:
                    result = await save_attachment(
                        attachment["url"], user, message.channel.name,
                        message.server.name, message.id, attachment["filename"]
                    )
                else:
                    result = await save_attachment(
                        attachment["url"], user, user,
                        "#private", message.id, attachment["filename"]
                    )

                if result is not None:
                    logger.info("Saved attachment: {}".format(result))
