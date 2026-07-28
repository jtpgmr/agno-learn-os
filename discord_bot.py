from uuid import uuid4

import discord
from agno.integrations.discord import DiscordClient

from src.agents.verifier import buildCodeVerifier
from src.core import getSettings


if __name__ == "__main__":
    settings = getSettings()
    session_id: str = str(settings.feature_test.session_id or uuid4())

    code_verifier = buildCodeVerifier(settings, session_id=session_id)
    discord_client: DiscordClient = DiscordClient(code_verifier)

    _on_message = discord_client.client.on_message  # ty: ignore     # unresolved-attribute

    @discord_client.client.event
    async def on_message(message: discord.Message):
        # gate: only explicit @-mention or DM
        if discord_client.client.user not in message.mentions and not isinstance(
            message.channel, discord.DMChannel
        ):
            return

        await _on_message(message=message)

    discord_client.serve()
