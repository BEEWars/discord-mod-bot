import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")

intents = discord.Intents.default()
intents.members = True          # necessário para kick/ban/timeout e eventos de membro
intents.message_content = True  # necessário para comandos baseados em prefixo

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=commands.DefaultHelpCommand())


@bot.event
async def on_ready():
    log.info(f"Conectado como {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        log.info(f"Sincronizados {len(synced)} comandos slash.")
    except Exception as e:
        log.exception(f"Falha ao sincronizar comandos slash: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar esse comando.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("Eu não tenho permissão suficiente para fazer isso.")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Faltou um argumento: `{error.param.name}`.")
    else:
        log.exception("Erro não tratado", exc_info=error)
        await ctx.send("Ocorreu um erro ao executar o comando.")


async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            log.info(f"Cog carregado: {filename}")


async def main():
    async with bot:
        await load_extensions()
        if not TOKEN:
            raise RuntimeError("DISCORD_TOKEN não definido. Configure o arquivo .env.")
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
