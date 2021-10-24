import argparse
import json
import logging

import re

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import aiohttp
import discord
from discord.ext import commands, tasks


EMBED_COLOR = 0x6441A5
AUTHOR_SUFFIX = "is spelunking!"


@dataclass
class Config:
    # Channel to sync streams to
    channel: int

    # Path to API where we get current streamers
    api_path: str

    # Key used to connect to API
    api_key: str

    # Token used to log into Discord
    discord_token: str

    @classmethod
    def from_path(cls, path: Path):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        return cls(
            channel=data["channel"],
            api_path=data["api-path"],
            api_key=data["api-key"],
            discord_token=data["discord-token"],
        )


@dataclass
class StreamRecord:
    username: str
    twitch: str
    id: str
    logo: str
    url: str
    status: str
    game: str

    def to_embed(self):
        embed = discord.Embed(title=self.url, url=self.url, color=EMBED_COLOR)
        embed.set_author(name=f"{self.username} {AUTHOR_SUFFIX}", url=self.url)
        embed.set_thumbnail(url=self.logo)
        embed.add_field(name="Game", value=self.game, inline=False)
        embed.add_field(name="Stream Title", value=self.status, inline=False)
        return embed


class StreamsSync(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config):
        self.bot = bot
        self.config = config

        self.syncer.start()  # pylint: disable=no-member

    async def get_streams_from_api(self) -> Optional[Dict[str, StreamRecord]]:
        records = {}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.config.api_path, params={"key": self.config.api_key}
            ) as req:
                if req.status != 200:
                    return
                data = await req.json()

        for stream in data:
            record = StreamRecord(**stream)
            records[record.url] = record

        return records

    async def get_stream_messages(self, channel):
        messages = {}

        async for msg in channel.history():
            if msg.author != self.bot.user:
                continue

            if len(msg.embeds) != 1:
                continue

            author_name = msg.embeds[0].author.name
            if not author_name.endswith(f" {AUTHOR_SUFFIX}"):
                continue
            author_url = msg.embeds[0].author.url

            # If we have multiple messages from one streamer just garbage collect
            # one of them.
            if author_url in messages:
                await messages[author_url].delete()

            messages[author_url] = msg

        return messages

    @staticmethod
    def contents_changed(record: StreamRecord, message):
        fields = {}
        for field in message.embeds[0].fields:
            fields[field.name] = field.value

        if record.game.strip() != fields.get("Game"):
            logging.info(
                "Game changed. Before: %s, After: %s",
                repr(fields.get("Game")),
                repr(record.game),
            )
            return True

        if record.status.strip() != fields.get("Stream Title"):
            logging.info(
                "Status changed. Before: %s, After: %s",
                repr(fields.get("Stream Title")),
                repr(record.status),
            )
            return True

        return False

    @tasks.loop(seconds=60.0)
    async def syncer(self):

        channel = self.bot.get_channel(self.config.channel)
        if channel is None:
            logging.warning("Failed to find channel %s", self.config.channel)
            return

        if not isinstance(channel, discord.TextChannel):
            logging.warning("Expected Text chanel for %s", self.config.channel)
            return

        records = await self.get_streams_from_api()
        if records is None:
            logging.warning("Failed to get streams from API")
            return

        messages = await self.get_stream_messages(channel)

        for twitch_name, record in records.items():
            if twitch_name not in messages:
                logging.info("Added new stream for %s", twitch_name)
                await channel.send(embed=record.to_embed())
            elif self.contents_changed(record, messages[twitch_name]):
                logging.info("Updating stream info for %s", twitch_name)
                await channel.edit(embed=record.to_embed())

            # Remove from messages to signal we're done processing. Any left
            # over messages will be deleted.
            messages.pop(twitch_name, None)

        for twitch_name, message in messages.items():
            logging.info(
                "Streamer %s stopped streaming. Removing message.", twitch_name
            )
            await message.delete()

    @syncer.before_loop
    async def before_syncer(self):
        logging.info("Waiting for bot to be ready before starting sync task...")
        await self.bot.wait_until_ready()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default=Path(__file__).absolute().parent / "streams-bot-config.json",
        type=Path,
        help="Path to config file.",
    )
    args = parser.parse_args()

    config = Config.from_path(args.config)
    intents = discord.Intents(guilds=True)
    bot = commands.Bot(command_prefix=None, intents=intents)
    bot.add_cog(StreamsSync(bot=bot, config=config))
    bot.run(config.discord_token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
