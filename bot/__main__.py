# coding=utf-8
import logging

from bot.client import Client
from bot.utils import get_token

__author__ = "Gareth Coles"

logging.basicConfig(
    format="%(asctime)s | %(name)s | [%(levelname)s] %(message)s",
    level=logging.INFO
)

logger = logging.getLogger("discord")
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(
    filename="output.log", encoding="utf-8", mode="w"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s | %(name)s | [%(levelname)s] %(message)s")
)
logger.addHandler(handler)


def main():
    client = Client()
    client.run(get_token(), bot=False)

if __name__ == "__main__":
    main()
