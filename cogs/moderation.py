import datetime
import discord
from discord import app_commands
from discord.ext import commands

# Armazenamento simples em memória para avisos (troque por banco de dados em produção)
warnings: dict[int, list[dict]] = {}


class Moderation(commands.Cog):
    """Comandos de moderação: kick, ban, timeout, warn, clear."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_name = "mod-logs"

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        channel = discord.utils.get(guild.text_channels, name=self.log_channel_name)
        if channel:
            await channel.send(embed=embed)

    # ---------- KICK ----------
    @commands.hybrid_command(name="kick", description="Expulsa um membro do servidor.")
    @app_commands.describe(member="Membro a expulsar", reason="Motivo")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Não especificado"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("Você não pode expulsar alguém com cargo igual ou superior ao seu.")
        await member.kick(reason=f"{reason} | Por: {ctx.author}")
        embed = discord.Embed(title="Membro expulso", color=discord.Color.orange())
        embed.add_field(name="Usuário", value=f"{member} ({member.id})")
        embed.add_field(name="Moderador", value=str(ctx.author))
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)
        await self._log(ctx.guild, embed)

    # ---------- BAN ----------
    @commands.hybrid_command(name="ban", description="Bane um membro do servidor.")
    @app_commands.describe(member="Membro a banir", reason="Motivo", delete_days="Dias de mensagens para apagar (0-7)")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, delete_days: int = 0, *, reason: str = "Não especificado"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("Você não pode banir alguém com cargo igual ou superior ao seu.")
        delete_days = max(0, min(7, delete_days))
        await member.ban(reason=f"{reason} | Por: {ctx.author}", delete_message_days=delete_days)
        embed = discord.Embed(title="Membro banido", color=discord.Color.red())
        embed.add_field(name="Usuário", value=f"{member} ({member.id})")
        embed.add_field(name="Moderador", value=str(ctx.author))
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)
        await self._log(ctx.guild, embed)

    # ---------- UNBAN ----------
    @commands.hybrid_command(name="unban", description="Remove o banimento de um usuário pelo ID.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int):
        user = discord.Object(id=user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"Usuário com ID `{user_id}` foi desbanido.")

    # ---------- TIMEOUT (mute temporário) ----------
    @commands.hybrid_command(name="timeout", description="Silencia um membro por X minutos.")
    @app_commands.describe(member="Membro a silenciar", minutes="Duração em minutos", reason="Motivo")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "Não especificado"):
        if minutes <= 0 or minutes > 40320:  # limite do Discord: 28 dias
            return await ctx.send("Duração inválida (máx. 40320 minutos / 28 dias).")
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=f"{reason} | Por: {ctx.author}")
        embed = discord.Embed(title="Membro silenciado", color=discord.Color.gold())
        embed.add_field(name="Usuário", value=f"{member} ({member.id})")
        embed.add_field(name="Duração", value=f"{minutes} min")
        embed.add_field(name="Moderador", value=str(ctx.author))
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)
        await self._log(ctx.guild, embed)

    @commands.hybrid_command(name="untimeout", description="Remove o silenciamento de um membro.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None)
        await ctx.send(f"Silenciamento de {member.mention} removido.")

    # ---------- WARN ----------
    @commands.hybrid_command(name="warn", description="Aplica um aviso a um membro.")
    @app_commands.describe(member="Membro a avisar", reason="Motivo")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Não especificado"):
        warnings.setdefault(member.id, []).append({
            "reason": reason,
            "moderator": str(ctx.author),
            "date": datetime.datetime.utcnow().isoformat(),
        })
        count = len(warnings[member.id])
        embed = discord.Embed(title="Aviso aplicado", color=discord.Color.yellow())
        embed.add_field(name="Usuário", value=f"{member} ({member.id})")
        embed.add_field(name="Total de avisos", value=str(count))
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)
        await self._log(ctx.guild, embed)

    @commands.hybrid_command(name="warnings", description="Lista os avisos de um membro.")
    async def warnings_cmd(self, ctx: commands.Context, member: discord.Member):
        user_warnings = warnings.get(member.id, [])
        if not user_warnings:
            return await ctx.send(f"{member.mention} não tem avisos.")
        embed = discord.Embed(title=f"Avisos de {member}", color=discord.Color.yellow())
        for i, w in enumerate(user_warnings, 1):
            embed.add_field(name=f"#{i} — {w['date'][:10]}", value=f"{w['reason']} (por {w['moderator']})", inline=False)
        await ctx.send(embed=embed)

    # ---------- CLEAR ----------
    @commands.hybrid_command(name="clear", description="Apaga um número de mensagens do canal.")
    @app_commands.describe(amount="Quantidade de mensagens (1-100)")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int):
        amount = max(1, min(100, amount))
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 inclui o comando em si
        msg = await ctx.send(f"{len(deleted) - 1} mensagens apagadas.")
        await msg.delete(delay=3)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
