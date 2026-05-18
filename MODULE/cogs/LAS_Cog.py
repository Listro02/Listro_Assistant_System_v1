import discord
from discord.ext import commands
import asyncio

# 독립된 핸들러를 import 합니다.
from MODULE.LAS_handler import LAS_Handler
from MODULE.log import log_set
from MODULE.LAS import LAS  # LAS의 변수를 조작하기 위한 호출

#tts 모듈
from gtts import gTTS 

import os
from dotenv import load_dotenv
load_dotenv()
tts_file = os.getenv("LAS_tts")

class LAS_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot, LAS_Handler: LAS_Handler):
        self.bot = bot
        self.LAS_Handler = LAS_Handler
        self.is_talking_enabled = False 
        self.only_for_developer = True
        self.tts = False
        self.log = log_set("LAS_cog")
        LAS.place = "디스코드(Discord)"
        LAS.scenario="당신은 현재 디스코드(Discord)에 접속해있고, 이를 통해 다음의 기능을 제어해서 사용자를 도울 수 있다. : [음악 재생]"
        
        print("LAS_Cog가 초기화되었습니다.")

    #  개선점: AI 응답 처리 로직을 하나의 헬퍼(Helper) 함수로 통합
    async def _handle_las_request(self, channel: discord.TextChannel, content: str, author: discord.User,message: discord.Message = None):
        """AI 응답을 요청하고 채널에 응답을 보내는 통합 로직"""
        thinking_message = await channel.send("잠시만 기다려주세요, 생각 중입니다...")

        try:
            # 타이핑 상태를 표시하여 사용자 경험 개선
            async with channel.typing():
                future = self.bot.loop.create_future()

                # 비동기 작업이 완료되었을 때 future에 결과를 설정하는 콜백
                def on_complete_callback(response_text):
                    self.bot.loop.call_soon_threadsafe(future.set_result, response_text)

                # LAS 핸들러에 실제 응답 요청
                self.LAS_Handler.request_response(content, on_complete_callback, name=str(author))

                # 지정된 시간(60초) 동안 응답을 기다림
                response = await asyncio.wait_for(future, timeout=60.0)
            
            # 응답이 오면 "생각 중" 메시지를 실제 응답 내용으로 수정
            await thinking_message.edit(content=response)
            self.log.sys_log.info("✅ 디스코드 응답 완료")
            if self.bot.kivy_app_ref:
                self.bot.kivy_app_ref.add_log_message(f"[L.A.S.] {response}")
            
            if self.tts == True:
                await self.LAS_tts(message,response)

        except asyncio.TimeoutError:
            await thinking_message.edit(content="죄송합니다, 응답 시간이 초과되었어요. 😥")
            self.log.sys_log.info("💀 디스코드 응답 실패 [시간 초과]")
        except Exception as e:
            await thinking_message.edit(content=f"오류가 발생했습니다: {e}")
            self.log.sys_log.info(f"💀 디스코드 응답 실패 [오류발생 : {e}]")

    async def LAS_tts(self,message: discord.Message,text:str):
        if message == None:
            return

        voice_client = message.guild.voice_client
        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()

            def speak(text:str): 
                tts = gTTS(text=text, lang='ko')
                tts.save(tts_file)
            def log_print(log_text:str):
                print(log_text)
                self.log.sys_log.info(log_text)

            # 동기 함수인 speak()를 백그라운드 스레드에서 실행
            # async와 비동기 환경을 분리
            try:
                await self.bot.loop.run_in_executor(None, speak, text)
                log_print(f"'text > tts' 변환 완료. [“{text}”]")
            except Exception as e:
                log_print(f"'text > tts' 변환 실패. 오류 발생 (Executor): {e}")
                return

            # 파일 로드 및 재생 (파일 이름 통일 필요)
            try:
                # speak 함수에서 저장한 파일 이름(user.wav)을 사용하도록 수정
                source = discord.FFmpegPCMAudio(tts_file)
                voice_client.play(source)
                log = f"tts 재생 완료."
            except Exception as e:
                log = f"tts 재생 중 오류 발생: {e}"
            finally:
                log_print(log)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """LAS_Chat Activate관련 함수"""
        # 봇이 보낸 메시지, 개발자 모드, 명령어 여부 등 기본 조건 확인
        if message.author.bot or (self.only_for_developer and str(message.author) != "listro02") or message.content.startswith(self.bot.command_prefix):
            return

        # AI 대화 모드가 활성화된 경우, 통합 핸들러 호출
        if self.is_talking_enabled:
            await self._handle_las_request(message.channel, message.content, message.author,message)

    @commands.command(name="ask")
    async def ask_command(self, ctx: commands.Context, *, question: str):
        """디스코드 채널에서 OpenAI에게 질문하고 응답을 받습니다."""
        # ask 명령어 역시 통합 핸들러를 호출하여 코드 중복 방지
        await self._handle_las_request(ctx.channel, question, ctx.author)

    # --------------------------------------------------
    # LAS ai 대화
    # --------------------------------------------------

    @commands.command(name='activate_talking')
    async def activate_talking_command(self, ctx):
        """AI 대화 모드를 활성화합니다."""
        self.is_talking_enabled = True
        text = f"✅ AI 대화가 활성화되었습니다. (Only for Developer : {self.only_for_developer})"
        await ctx.send(text)
        self.log.sys_log.info(text)
    
    @commands.command(name='deactivate_talking')
    async def deactivate_talking_command(self, ctx):
        """AI 대화 모드를 비활성화합니다."""
        self.is_talking_enabled = False
        text = f"💀 대화가 비활성화되었습니다. (Only for Developer : {self.only_for_developer})"
        await ctx.send(text)
        self.log.sys_log.info(text)

    # --------------------------------------------------
    # LAS tts 대화
    # --------------------------------------------------

    @commands.command(name='activate_LAS_tts')
    async def activate_tts_command(self, ctx):
        """LAS 대화 tts를 활성화합니다."""
        self.tts = True
        text = f"✅ LAS_tts가 활성화되었습니다. (LAS_tts : {self.tts})"
        await ctx.send(text)
        self.log.sys_log.info(text)
    
    @commands.command(name='deactivate_LAS_tts')
    async def deactivate_tts_command(self, ctx):
        """LAS 대화 tts를 비활성화합니다."""
        self.tts = False
        text = f"💀 LAS_tts가 비활성화되었습니다. (LAS_tts : {self.tts})"
        await ctx.send(text)
        self.log.sys_log.info(text)

    # --------------------------------------------------
    # only 개발자 vs Everyone
    # --------------------------------------------------

    @commands.command(name='for_everyone')
    async def everyone_command(self, ctx):
        """다인 AI 대화 모드를 활성화합니다."""
        self.only_for_developer = False
        text = f"✅ Only for Developer 모드가 비활성화되었습니다. (Only for Developer : {self.only_for_developer})"
        await ctx.send(text)
        self.log.sys_log.info(text)

    @commands.command(name='for_developer')
    async def only_developer_command(self, ctx):
        """개발자 AI 대화 모드를 활성화합니다."""
        self.only_for_developer = True
        text = f"✅ Only for Developer 모드가 활성화되었습니다. (Only for Developer : {self.only_for_developer})"
        await ctx.send(text)
        self.log.sys_log.info(text)

# Cog를 로드하는 setup 함수
async def setup(bot: commands.Bot):
    if not hasattr(bot, 'LAS_Handler'):
        print("[오류] 봇에 LAS_Handler가 없습니다. 메인 파일에서 생성 후 Cog를 로드해주세요.")
        return
    
    await bot.add_cog(LAS_Cog(bot, bot.LAS_Handler))