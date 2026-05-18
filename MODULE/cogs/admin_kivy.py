import discord
from discord.ext import commands
from MODULE.log import log_set

from dotenv import load_dotenv
import os
load_dotenv()

file = os.getenv("discord_help")

# 'AdminCommands'라는 이름의 Cog 클래스를 정의합니다.
class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """Cog가 초기화될 때 bot 인스턴스를 받아옵니다."""
        self.bot = bot
        self.discord_log = log_set("admin_kivy")
        self.discord_log.activate_dicord_log()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """모든 메시지를 Kivy 앱의 로그에 기록하는 리스너입니다."""
        # 봇 자신이 보낸 메시지는 무시합니다.
        # 봇에 연결된 Kivy 앱(kivy_app_ref)이 있다면 로그를 전송합니다.
        if self.bot.kivy_app_ref:
            log_text = f"[{message.channel}] {message.author}: {message.content}"
            self.discord_log.dis_log.info(log_text)
            
            # Kivy의 UI 업데이트는 메인 스레드에서 처리해야 하므로, 앱의 메서드를 호출합니다.
            self.bot.kivy_app_ref.add_log_message(log_text)
            #print(message.channel.id) #그냥 채널 id 확인용

        if message.author == self.bot.user:
            return

    @commands.command(name='도움말', aliases=['명령어'])
    async def help_(self, ctx):
        """명령어 도움말을 호출합니다."""
        self.discord_log.sys_log.info("'#도움말' 명령어 호출됨.")
        with open(r"C:\Users\taewo\Desktop\Programming\Team_Listro\L.A.S\Project\DATABASE\new_discord_help.txt", 'r', encoding='utf-8') as f:
            messages = f.read()
        await ctx.send(messages)

    @commands.command(name='상태', aliases=['state'])
    @commands.is_owner()
    async def state_command(self, ctx):
        """현 봇의 상태 정보를 TERMINAL에 출력합니다."""
        self.discord_log.sys_log.info("'#상태' 명령어 호출됨.")
        print("--------------------------------------------------")
        print(f"✅ 다음 계정으로 성공적으로 로그인했습니다: {self.bot.user.name}")
        print(f"✅ 사용자 ID: {self.bot.user.id}")
        print(f"✅ 소속된 서버 개수: {len(self.bot.guilds)}개")

        for guild in self.bot.guilds:
            print(f"- 서버 이름: {guild.name} (ID: {guild.id})")

        print("--------------------------------------------------")

    @commands.command()
    @commands.is_owner() # 봇 소유자만 실행 가능
    async def load(self,ctx, extension):
        """지정한 Cog를 로드합니다."""
        self.discord_log.sys_log.info("'#load' 명령어 호출됨.")
        await self.bot.load_extension(f'MODULE.cogs.{extension}')
        log = f"✅ `{extension}` Cog가 로드되었습니다."
        await ctx.send(log)
        self.discord_log.sys_log.info(log)

        if self.bot.kivy_app_ref:
            self.bot.kivy_app_ref.add_log_message(log)

    @commands.command()
    @commands.is_owner() # 봇 소유자만 실행 가능
    async def unload(self,ctx, extension):
        """지정한 Cog를 언로드합니다."""
        self.discord_log.sys_log.info("'#unload' 명령어 호출됨.")
        await self.bot.unload_extension(f'MODULE.cogs.{extension}')
        log = f"✅ `{extension}` Cog가 언로드되었습니다."
        await ctx.send(log)
        self.discord_log.sys_log.info(log)

        if self.bot.kivy_app_ref:
            self.bot.kivy_app_ref.add_log_message(log)

    @commands.command()
    @commands.is_owner() # 봇 소유자만 실행 가능
    async def reload(self,ctx, extension):
        """지정한 Cog를 다시 로드합니다."""
        self.discord_log.sys_log.info("'#reload' 명령어 호출됨.")
        await self.bot.reload_extension(f'MODULE.cogs.{extension}')
        log = f"✅ `{extension}` Cog가 다시 로드되었습니다."
        await ctx.send(log)
        self.discord_log.sys_log.info(log)

        if self.bot.kivy_app_ref:
            self.bot.kivy_app_ref.add_log_message(log)

    # 그냥 만들어본거
    @commands.command(name="send_channel")
    @commands.is_owner()
    async def send_custom_message(self, ctx, channel_id: int, *, message_content: str):
        """특정 채널 ID로 임의의 메시지를 전송하는 함수"""
        self.discord_log.sys_log.info("'#send_channel' 명령어 호출됨.")
        try:
            # self.get_channel 대신 self.bot.get_channel을 사용합니다.
            channel = self.bot.get_channel(channel_id)
            if not channel:
                log = f"오류: ID `{channel_id}`에 해당하는 채널을 찾을 수 없습니다."
                await ctx.send(log)
                self.discord_log.sys_log.error(log)
                return

            # 메시지를 보냅니다.
            await channel.send(message_content)
            log = f"✅ 메시지를 채널 ID `{channel_id}`에 성공적으로 보냈습니다."
            await ctx.send(log)
            self.discord_log.sys_log.info(log)

        except discord.Forbidden:
            log = f"오류: 채널 ID `{channel_id}`에 메시지를 보낼 권한이 없습니다."
            await ctx.send(log)
            self.discord_log.sys_log.error(log)
        except Exception as e:
            log = f"메시지 전송 중 오류 발생: {e}"
            await ctx.send(log)
            self.discord_log.sys_log.error(log)
        
    @commands.command(name="send_dm")
    @commands.is_owner()
    async def send_direct_message(self, ctx, user_id: int, *, message_content: str):
        """특정 사용자에게 DM을 보냅니다."""
        self.discord_log.sys_log.info("'#send_dm' 명령어 호출됨.")
        try:
            # 1. 사용자 ID로 사용자 객체를 얻습니다.
            user = self.bot.get_user(user_id)
            if not user:
                log = f"오류: ID `{user_id}`에 해당하는 사용자를 찾을 수 없습니다."
                await ctx.send(log)
                self.discord_log.sys_log.error(log)
                return

            # 2. 사용자에게 메시지를 보냅니다.
            await user.send(message_content)
            log = f"✅ 사용자 `{user.name}`에게 성공적으로 DM을 보냈습니다."
            await ctx.send(log)
            self.discord_log.sys_log.info(log)

        except discord.Forbidden:
            log = f"오류: 사용자 `{user.name}`에게 DM을 보낼 수 없습니다. 해당 사용자가 DM을 차단했거나 봇이 속하지 않은 서버에 있습니다."
            await ctx.send(log)
            self.discord_log.sys_log.error(log)
        except Exception as e:
            log = f"DM 전송 중 오류 발생: {e}"
            await ctx.send(log)
            print(log)
            self.discord_log.sys_log.error(log)

# setup 함수는 discord.py가 이 파일을 Cog로 인식하고 로드하기 위해 필수적입니다.
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
