# -*- coding: utf-8 -*-
"""
Keil 监视器 (后台静默运行, 由登录计划任务启动)
每隔几秒检测 UV4.exe (Keil uVision) 是否启动;
当 Keil 从“未运行”变为“运行”时, 弹出开发记录助手 (keil_logger.py)。
使用 pythonw.exe 运行, 无控制台窗口。
"""
import os
import sys
import time
import socket
import subprocess

POLL_SECONDS = 4
PROCESS_NAME = "UV4.exe"
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGGER = os.path.join(TOOLS_DIR, "keil_logger.py")
CREATE_NO_WINDOW = 0x08000000


def single_instance(port=51764):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except OSError:
        return None


def keil_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq " + PROCESS_NAME, "/NH"],
            capture_output=True, text=True, errors="replace",
            creationflags=CREATE_NO_WINDOW)
        return PROCESS_NAME.lower() in (out.stdout or "").lower()
    except Exception:
        return False


def launch_logger():
    # 优先用 pythonw (无黑框); 找不到则退回当前解释器
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    try:
        subprocess.Popen([exe, LOGGER], cwd=TOOLS_DIR,
                         creationflags=CREATE_NO_WINDOW)
    except Exception:
        pass


def main():
    lock = single_instance()
    if lock is None:
        return                      # 已有监视器在运行
    was = keil_running()            # 启动时若已开着, 不立即弹 (等下次重开)
    while True:
        try:
            now = keil_running()
            if now and not was:
                launch_logger()
            was = now
        except Exception:
            pass
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
