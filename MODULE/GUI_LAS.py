import os
import discord
from discord.ext import commands
import asyncio
import threading
from dotenv import load_dotenv

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.window import Window

# 독립 모듈과 핸들러 import
from MODULE.LAS_handler import LAS_Handler

from MODULE.log import log_set
GUI_log = log_set("GUI_LAS")
GUI_log.activate_dicord_log()

from MODULE.LAS import LAS  #LAS의 변수를 조작하기 위한 호출, 다루는 건 handler로 다룸.

# .env 파일 로드
load_dotenv()

# --- Discord 봇 클래스 ---
class MySuperBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Kivy 앱과 공유 핸들러의 참조를 받습니다.
        self.kivy_app_ref = kwargs.pop('kivy_app_ref', None)
        self.LAS_Handler = kwargs.pop('LAS_Handler', None)
        super().__init__(*args, **kwargs)

    def all_log(self,log:str):
        GUI_log.sys_log.info(log)
        print(log)
        if self.kivy_app_ref:
            self.kivy_app_ref.add_log_message(log)

    async def setup_hook(self):
        print("Cog 로드를 시작합니다...")

        discord_cogs = ["LAS_Cog","admin_kivy","tts_kivy","voice_room_kivy","music_kivy"]
        for filename in discord_cogs:
            log ="버그방지 기본 변수 할당"
            try:
                await self.load_extension(f'MODULE.cogs.{filename}')
                log = f"✅ {filename} Cog가 로드되었습니다."
                
            except Exception as e:
                log = f"❌ {filename} Cog를 로드하는 중 오류 발생: {e}"
            finally:
                self.all_log(log)
    
        print("Cog 로드가 완료되었습니다.")
    
    async def on_ready(self):
        log_message = f'[봇] {self.user} (으)로 로그인했습니다.'
        self.all_log(log_message)
        if self.kivy_app_ref:
            self.kivy_app_ref.update_status_label("봇 상태: 온라인")
        
        state = "💻 L.A.S. Ver.1 프로토타입"
        await self.change_presence(status=discord.Status.online, activity=discord.Game(state))
        self.all_log(f"봇의 상태 메시지가 설정되었습니다. : {state}")
    
    async def on_disconnect(self):
        log_message = '[봇] 연결이 끊어졌습니다.'
        self.all_log(log_message)
        if self.kivy_app_ref:
            self.kivy_app_ref.update_status_label("봇 상태: 오프라인")
    
    async def close(self):
        self.all_log("봇 종료 절차를 시작합니다.")
        await super().close()

# --- Kivy 위젯 및 앱 클래스 ---
class LAS_GUI(BoxLayout):
    pass

class LAS_GUI_App(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot_thread = None
        self.bot_instance = None
        self.bot_loop = None
        
        # 공유할 OpenAI 핸들러를 앱이 시작될 때 '단 한 번' 생성합니다.
        try:
            self.LAS_Handler = LAS_Handler(max_workers=5)
        except ValueError as e:
            # API 키가 없으면 핸들러를 None으로 설정
            self.LAS_Handler = None
            Clock.schedule_once(lambda dt: self.add_log_message(f"[오류] {e}"))

        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        Window.bind(on_request_close=self.on_request_close)

    def build(self):
        return LAS_GUI()

    def ask_openai_from_gui(self):
        """인공지능 답변(설명은 적어야함)"""
        if not self.LAS_Handler:
            self.add_log_message("[오류] OpenAI 핸들러가 초기화되지 않았습니다. API 키를 확인하세요.")
            return

        prompt_input = self.root.ids.prompt_input
        prompt = prompt_input.text.strip()
        if not prompt:
            return

        prompt_input.text = ""
        Clock.schedule_once(lambda dt: setattr(prompt_input, 'focus', True))

        self.add_log_message(f"[GUI 요청] '{prompt[:20]}...' 처리 중...")

        # GUI에서 핸들러를 사용할 때의 콜백 함수
        def on_gui_complete(response_text):
            """다른 스레드의 결과를 Kivy 메인 스레드에서 안전하게 업데이트"""
            log_entry = f"[L.A.S.]\n{response_text}"
            # 다른 스레드의 결과를 Kivy 메인 스레드에서 안전하게 업데이트
            Clock.schedule_once(lambda dt: self.add_log_message(log_entry))

        # 독립된 핸들러에 작업을 요청합니다.
        self.LAS_Handler.request_response(prompt, on_gui_complete,name="Listro")

    def _run_bot_in_thread(self):
        self.bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.bot_loop)

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        self.bot_instance = MySuperBot(
            command_prefix='#', 
            intents=intents,
            kivy_app_ref=self,
            LAS_Handler=self.LAS_Handler # 공유 핸들러를 봇에 전달
        )
        
        try:
            self.bot_loop.run_until_complete(self.bot_instance.start(self.BOT_TOKEN))
        finally:
            self.bot_loop.run_until_complete(self.bot_loop.shutdown_asyncgens())
            self.bot_loop.close()
            print("봇 이벤트 루프가 완전히 종료되었습니다.")

    def start_bot_thread(self):
        if not self.BOT_TOKEN:
            self.add_log_message("[오류] .env 파일에 DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
            return
        if self.bot_thread and self.bot_thread.is_alive():
            self.add_log_message("[알림] 봇이 이미 실행 중입니다.")
            return
        
        self.update_status_label("봇 상태: 시작 중...")
        self.bot_thread = threading.Thread(target=self._run_bot_in_thread, daemon=True)
        self.bot_thread.start()

    def stop_bot_thread(self):
        if self.bot_instance and self.bot_loop and self.bot_loop.is_running():
            self.update_status_label("봇 상태: 종료 중...")
            asyncio.run_coroutine_threadsafe(self.bot_instance.close(), self.bot_loop)
            LAS.place = "Listro의 개발실"
            LAS.scenario="당신은 'Listro의 개발실'에서 당신의 ai비서로써의 역할을 수행하는지 테스트하고 있습니다."

        else:
            self.add_log_message("[알림] 봇이 실행되고 있지 않습니다.")

    def on_request_close(self, *args):
        self.exit_app()
        return True

    def exit_app(self):
        print("애플리케이션 종료 절차를 시작합니다...")
        if self.bot_thread and self.bot_thread.is_alive():
            self.stop_bot_thread()
        
        # 핸들러의 스레드 풀을 안전하게 종료
        if self.LAS_Handler:
            self.LAS_Handler.shutdown()
        
        self.stop() # Kivy 앱 종료

    def update_status_label(self, text):
        def update_ui(dt):
            if self.root: self.root.ids.status_label.text = text
        Clock.schedule_once(update_ui)

    # LAS_GUI_App 클래스 내의 add_log_message 함수
    def add_log_message(self, log_text):
        def update_ui(dt):
            if self.root:
                log_label = self.root.ids.log_label
                
                # 현재 로그 텍스트를 줄바꿈 기준으로 분리합니다.
                log_lines = log_label.text.split('\n')
                
                # 만약 로그 줄 수가 100개를 초과하면
                if len(log_lines) > 100:
                    # 가장 오래된 줄들을 제거하고 최신 90줄만 남깁니다.
                    log_label.text = '\n'.join(log_lines[-90:])
                
                # 새로운 로그 메시지를 추가합니다.
                log_label.text += f"\n{log_text}"
                
        # Kivy의 Clock 스케줄러를 사용하여 UI 업데이트를 메인 스레드로 보냅니다.
        Clock.schedule_once(update_ui)

if __name__ == '__main__':
    LAS_GUI_App().run()
