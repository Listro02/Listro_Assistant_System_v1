import discord
from discord.ext import commands
from MODULE.log import log_set

#tts 모듈
from gtts import gTTS 

from dotenv import load_dotenv
import os
load_dotenv()

file = os.getenv("tts_kivy")

# 'tts_talking'라는 이름의 Cog 클래스를 정의합니다.
class tts_talking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """Cog가 초기화될 때 bot 인스턴스를 받아옵니다."""
        self.bot = bot
        self.tts_talking_log = log_set("tts_kivy")
        self.activate = False

    def speak(self,text:str): 
        tts = gTTS(text=text, lang='ko')
        tts.save(file)

    def log_print(self,log:str):
        print(log)
        self.tts_talking_log.sys_log.info(log)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 봇이 보낸 메시지나 명령어를 무시합니다.
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        # 활성화 상태 및 특정 채널 ID 확인
        if self.activate and message.channel.id in [1406291680352796802,1406303002205356142]:
            voice_client = message.guild.voice_client

            if voice_client and voice_client.is_connected():
                if voice_client.is_playing():
                    voice_client.stop()

                # 동기 함수인 self.speak()를 백그라운드 스레드에서 실행
                # async와 비동기 환경을 분리
                try:
                    await self.bot.loop.run_in_executor(None, self.speak, message.content)
                    self.log_print(f"'text > tts' 변환 완료. [“{message.content}”]")
                except Exception as e:
                    self.log_print(f"'text > tts' 변환 실패. 오류 발생 (Executor): {e}")
                    return

                # 파일 로드 및 재생 (파일 이름 통일 필요)
                try:
                    # speak 함수에서 저장한 파일 이름(user.wav)을 사용하도록 수정
                    source = discord.FFmpegPCMAudio(file)
                    voice_client.play(source)
                    log = f"tts 재생 완료."
                except Exception as e:
                    log = f"tts 재생 중 오류 발생: {e}"
                finally:
                    self.log_print(log)


    @commands.command()
    async def activate_tts(self,ctx):
        """tts를 활성화합니다."""
        self.activate = True
        log = f"✅ tts생성기 활성화되었습니다."
        self.tts_talking_log.sys_log.info(log)
        
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
                    self.tts_talking_log.sys_log.info(f"➡️ **{channel.name}** 채널로 이동했습니다.")
            # 봇이 아무 음성 채널에도 없다면, 새로 접속합니다.
            else:
                await channel.connect()
                await ctx.send(f"➡️ **{channel.name}** 채널에 접속했습니다.")
                self.tts_talking_log.sys_log.info(f"➡️ **{channel.name}** 채널에 접속했습니다.")
        else:
            await ctx.send("음성 채널에 먼저 들어가주시길 바랍니다. 🗣️")
        await ctx.send(log)

    @commands.command()
    async def deactivate_tts(self,ctx):
        """tts를 비활성화합니다."""
        self.activate = False
        log = f"💀 tts생성기 비활성화되었습니다."
        self.tts_talking_log.sys_log.info(log)
        await ctx.send(log)



# setup 함수는 discord.py가 이 파일을 Cog로 인식하고 로드하기 위해 필수적입니다.
async def setup(bot: commands.Bot):
    await bot.add_cog(tts_talking(bot))
