import MODULE.GUI_LAS as LAS
from MODULE.log import log_set

test_log = log_set("main")

if __name__ == "__main__":
    test_log.sys_log.info("🔥 LAS 프로그램 시작")
    LAS.LAS_GUI_App().run()