import MODULE.GUI_LAS as DISCORD
from MODULE.log import log_set

test_log = log_set("MODULE_test")

if __name__ == "__main__":
    test_log.sys_log.info("🔥 테스트 시작")
    DISCORD.LAS_GUI_App().run()
    #jarvis.png와 글꼴은 실행파일 위치에 있어야 인식함.