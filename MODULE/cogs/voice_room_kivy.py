import discord
from discord.ext import commands
from MODULE.log import log_set

# 'Voice_Room'라는 이름의 Cog 클래스를 정의합니다.
class Voice_Room(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """Cog가 초기화될 때 bot 인스턴스를 받아옵니다."""
        self.bot = bot
        self.log = log_set("voice_room_kivy")


    @commands.command(name='입장', aliases=['join', 'j'])
    async def join_voice_channel(self,ctx):
        """명령어 사용자가 있는 음성 채널에 봇을 접속시킵니다."""
        # 명령어 사용자가 음성 채널에 접속해 있는지 확인합니다.
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            # 봇이 이미 다른 음성 채널에 접속해 있는지 확인합니다.
            if ctx.voice_client:
                # 이미 접속한 채널과 사용자가 있는 채널이 같으면 알림을 보냅니다.
                if ctx.voice_client.channel == channel:
                    pass
                # 다른 채널에 있다면, 그 채널로 이동합니다.
                else:
                    await ctx.voice_client.move_to(channel)
                    await ctx.send(f"➡️ **{channel.name}** 채널로 이동했습니다.")
                    self.log.sys_log.info(f"➡️ **{channel.name}** 채널로 이동했습니다.")
            # 봇이 아무 음성 채널에도 없다면, 새로 접속합니다.
            else:
                await channel.connect()
                await ctx.send(f"➡️ **{channel.name}** 채널에 접속했습니다.")
                self.log.sys_log.info(f"➡️ **{channel.name}** 채널에 접속했습니다.")
        else:
            await ctx.send("음성 채널에 먼저 들어가주시길 바랍니다. 🗣️")

    @commands.command(name='퇴장', aliases=['leave', 'l'])
    async def leave_voice_channel(self,ctx):
        """봇을 현재 접속해 있는 음성 채널에서 퇴장시킵니다."""
        # 봇이 음성 채널에 접속해 있는지 확인합니다.
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 음성 채널에서 나갔습니다.")
            self.log.sys_log.info(f"👋 음성 채널에서 나갔습니다.")
        else:
            await ctx.send("저는 이미 아무 채널에도 없습니다. 🤔")

# setup 함수는 discord.py가 이 파일을 Cog로 인식하고 로드하기 위해 필수적입니다.
async def setup(bot: commands.Bot):
    await bot.add_cog(Voice_Room(bot))