import discord
from discord.ext import commands
from MODULE.log import log_set

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_log = log_set("DISCORD_client_admin")
        self.discord_log.activate_dicord_log()

    """# on_ready 이벤트도 Cog 리스너로 가져올 수 있습니다.
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ 로그인됨: {self.bot.user}")
        self.discord_log.sys_log.info(f"✅ 로그인됨: {self.bot.user}")"""

    @commands.command(name='stop')
    async def stop_command(self, ctx):
        """봇을 안전하게 종료합니다."""
        await ctx.send("L.A.S. DISCORD 시스템을 종료합니다... 👋")
        self.discord_log.sys_log.info("L.A.S. DISCORD 시스템을 종료합니다... 👋")
        await self.bot.close()

    @commands.command(name='상태')
    async def state_command(self, ctx):
        print("--------------------------------------------------")
        print(f"✅ 다음 계정으로 성공적으로 로그인했습니다: {self.bot.user.name}")
        print(f"✅ 사용자 ID: {self.bot.user.id}")
        print(f"✅ 소속된 서버 개수: {len(self.bot.guilds)}개")

        for guild in self.bot.guilds:
            print(f"- 서버 이름: {guild.name} (ID: {guild.id})")

        print("--------------------------------------------------")

    @commands.command(name='도움말', aliases=['명령어'])
    async def help_(self, ctx):
        with open(r"C:\Users\taewo\Desktop\Programming\Team_Listro\L.A.S\Project\DATABASE\discord_help.txt", 'r', encoding='utf-8') as f:
            messages = f.read()
        await ctx.send(messages)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))