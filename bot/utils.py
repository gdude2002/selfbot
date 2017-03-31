# coding=utf-8
import aiohttp
import logging
import os
import re
import yaml

from unicodedata import normalize

_punct_re = re.compile(r'[\t !"$%&\'()*\-/<=>?@\[\\\]^_`{|},:]+')

__author__ = 'Gareth Coles'
session = aiohttp.ClientSession()
loggers = {}


def get_token():
    with open("config.yml", "r") as fh:
        data = yaml.load(fh)

    return data["token"]



def get_logger(name):
    if name in loggers:
        return loggers[name]

    logger = logging.getLogger(name)
    handler = logging.FileHandler(
        filename="output.log", encoding="utf-8", mode="w"
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(name)s | [%(levelname)s] %(message)s")
    )
    logger.addHandler(handler)

    loggers[name] = logger
    return logger


def slugify(text, delimiter='-'):
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        word = word.decode('utf-8')
        if word:
            result.append(word)
    return delimiter.join(result)


async def save_attachment(url, user, channel, guild, message_id, filename):
    user = slugify(user)
    channel = slugify(channel)
    guild = slugify(guild)
    filename = slugify(filename)

    base_dir = "attachments/{}/{}/".format(guild, channel)
    filename = "{}-{}-{}".format(
        message_id, user, filename
    )

    try:
        async with session.get(url) as response:
            data = await response.read()

            os.makedirs(base_dir, exist_ok=True)

            with open(base_dir + filename, "wb") as fh:
                fh.write(data)
                fh.flush()
    except Exception as e:
        logger = get_logger("bot")
        logger.error("Failed to get attachment {}: {}".format(filename, e))
        return None

    return base_dir + filename
