import discord
from discord.ext import commands
from MODULE.log import log_set
import yt_dlp
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

class music_play(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.log = log_set("DISCORD_kivy")

    @commands.command(name='재생', aliases=['play', 'p'])
    async def play_music(self,ctx, *, query):
        """유튜브 URL이나 검색어로 음악을 재생합니다."""
        # 1. 봇이 음성 채널에 접속해 있는지 확인하고, 없다면 사용자가 있는 채널로 접속시킵니다.
        if not ctx.voice_client:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await channel.connect()
                text = f"➡️ **{channel.name}** 채널에 접속했습니다."
                await ctx.send(text)
                self.log.sys_log.info(text)
            else:
                await ctx.send("음성 채널에 먼저 들어가신 후 명령어를 사용해주시길 바랍니다. 🗣️")
                return
                
        # 2. 이미 재생 중인 음악이 있거나 일시정지 상태라면 중지합니다.
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        # 3. yt-dlp 설정: 오디오만 추출하고, 재생목록은 가져오지 않도록 설정합니다.
        YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'auto', # 검색어가 URL이 아닐 경우 자동으로 검색
        }
        
        # 4. yt-dlp를 이용해 영상 정보 추출
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                # 검색을 통해 영상 정보를 가져옵니다. (download=False는 다운로드하지 않음을 의미)
                info = ydl.extract_info(query, download=False)
                
                # 만약 검색 결과가 재생목록(entries) 형태이면 첫 번째 영상 정보를 사용합니다.
                if 'entries' in info:
                    info = info['entries'][0]
                
                # 스트리밍 URL과 영상 제목을 추출합니다.
                audio_url = info['url']
                video_title = info.get('title', '알 수 없는 제목')

            except Exception as e:
                text = f"⚠️ 음악을 찾는 중 오류가 발생했습니다. : {e}"
                await ctx.send(text)
                return

        # 5. FFmpeg를 통해 오디오를 디스코드로 스트리밍하기 위한 설정
        #    네트워크 문제로 끊기는 것을 방지하기 위한 옵션을 추가합니다.
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn', # 비디오는 제외하고 오디오만 처리
        }
        
        # 6. 오디오 소스를 생성합니다.
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        
        # 7. 생성된 오디오 소스를 재생합니다.
        ctx.voice_client.play(source)
        text = f"🎶 **{video_title}** 재생을 시작합니다."
        await ctx.send(text)
        self.log.sys_log.info(text)


    @commands.command(name='로컬재생')
    async def play_local_music(self,ctx, *, file_name: str):
        """지정된 이름의 로컬 오디오 파일을 재생합니다."""
        # 1. 봇이 음성 채널에 접속해 있는지 확인하고, 없다면 접속시킵니다.
        if not ctx.voice_client:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await channel.connect()
                text = f"➡️ **{channel.name}** 채널에 접속했습니다."
                await ctx.send(text)
                self.log.sys_log.info(text)
            else:
                await ctx.send("음성 채널에 먼저 들어가신 후 명령어를 사용해주세요! 🗣️")
                return
        
        # 2. 이미 재생 중인 음악이 있다면 중지합니다.
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        # 3. 파일 경로를 설정하고, 파일이 실제로 존재하는지 확인합니다.
        #    (예: 'music' 이라는 하위 폴더에 오디오 파일을 저장했다고 가정)
        file_path = os.getenv("local_music_file") +f"{file_name}"
        
        if not os.path.exists(file_path):
            text = f"⚠️ **{file_name}** 파일을 찾을 수 없어요. 파일 이름이나 경로를 확인해 주세요."
            await ctx.send(text)
            self.log.sys_log.error(text)
            return

        # 4. FFmpeg를 통해 로컬 파일을 오디오 소스로 변환합니다.
        source = discord.FFmpegPCMAudio(file_path)

        # 5. 오디오 소스를 재생합니다.
        ctx.voice_client.play(source)
        text = f"📁 **{file_name}** 재생을 시작합니다."
        await ctx.send(text)
        self.log.sys_log.info(text)

async def setup(bot):
    await bot.add_cog(music_play(bot))