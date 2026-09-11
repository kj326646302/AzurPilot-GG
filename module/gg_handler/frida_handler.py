"""
AlasGG Frida 集成

调用时机: GG 倍率设完后, 游戏已在主界面, Lua 加载完毕

行为:
  1. 检查 keepalive 进程在不在 → 在就跳过
  2. 不在 → 拿游戏 PID → spawn 系统 Python313 + inject.py <PID>
  3. inject.py 一次性 hook, 成功后保持运行 (守 NativeCallback 内存)
"""
import os
import shutil
import subprocess
import sys
import time
from module.logger import logger

def _detect_sys_python():
    """
    探测一个带 frida 的系统 Python 解释器。
    优先级: 环境变量 ALASGG_FRIDA_PYTHON > PATH 里的 python > 当前解释器
    (不硬编码任何用户私有路径)
    """
    env = os.environ.get("ALASGG_FRIDA_PYTHON")
    if env and os.path.exists(env):
        return env
    for name in ("python", "python3", "py"):
        found = shutil.which(name)
        if found:
            return found
    return sys.executable

SYS_PYTHON = _detect_sys_python()
FRIDA_DIR = os.path.join(os.path.abspath("."), "bin", "Frida")
INJECT_PY = os.path.join(FRIDA_DIR, "inject.py")
PIDFILE = os.path.join(FRIDA_DIR, "daemon.pid")

class FridaHandler:
    def __init__(self, config=None, device=None):
        self.config = config
        self.device = device

    def _keepalive_alive(self):
        if not os.path.exists(PIDFILE):
            return False
        try:
            with open(PIDFILE, encoding="utf-8") as f:
                pid = int(f.read().strip())
        except (OSError, ValueError):
            return False
        try:
            if os.name == "nt":
                out = subprocess.check_output(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    stderr=subprocess.STDOUT, timeout=5,
                )
                return str(pid).encode() in out
            os.kill(pid, 0)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def _find_game_pid(self):
        """通过 adb 拿游戏主进程 PID"""
        try:
            serial = getattr(self.device, "serial", "127.0.0.1:7555")
            adb = os.environ.get("ALASGG_ADB") or shutil.which("adb")
            if not adb:
                bundled = os.path.join(
                    os.path.abspath("."),
                    "toolkit", "Lib", "site-packages", "adbutils", "binaries", "adb.exe"
                )
                adb = bundled if os.path.exists(bundled) else "adb"
            out = subprocess.check_output(
                [adb, "-s", serial, "shell", "pidof", "com.bilibili.azurlane"],
                stderr=subprocess.STDOUT, timeout=5,
            ).decode().strip().split()
            if out and out[0].isdigit():
                return int(out[0])
        except Exception as e:
            logger.warning(f"[Frida] pidof failed: {e}")
        return None

    def ensure_running(self):
        """
        确保 hook 已注入 + keepalive 进程活着
        游戏 PID 已变 (重启过) 也要重新注入
        """
        if not os.path.exists(SYS_PYTHON):
            logger.warning(f"[Frida] system python not found: {SYS_PYTHON}, skip")
            return False
        if not os.path.exists(INJECT_PY):
            logger.warning(f"[Frida] inject script not found: {INJECT_PY}, skip")
            return False

        game_pid = self._find_game_pid()
        if game_pid is None:
            logger.warning("[Frida] game process not found, skip")
            return False

        # 检查 keepalive 还在不在，且它持有的 PID 跟当前游戏 PID 一致
        # (重启游戏后 PID 变了, 旧 keepalive 已 detach 自动退出, pidfile 会清掉)
        if self._keepalive_alive():
            logger.info("[Frida] keepalive already running, skip")
            return True

        # spawn 新 keepalive
        env = os.environ.copy()
        env["ALASGG_ADB_SERIAL"] = getattr(self.device, "serial", "127.0.0.1:7555")

        popen_kwargs = {
            "cwd": FRIDA_DIR,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "env": env,
            "close_fds": True,
        }
        if os.name == "nt":
            # Windows DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            popen_kwargs["creationflags"] = 0x00000008 | 0x00000200
        else:
            # Linux 容器中脱离 WebUI 的会话组，避免重载时误杀 keepalive。
            popen_kwargs["start_new_session"] = True
        try:
            p = subprocess.Popen(
                [SYS_PYTHON, INJECT_PY, str(game_pid)],
                **popen_kwargs,
            )
            logger.info(f"[Frida] inject spawned, pid={p.pid}, target game pid={game_pid}")
            # 等 hook 装上 (最长 30s, 实际通常 1-3s)
            for i in range(60):
                time.sleep(0.5)
                if self._keepalive_alive():
                    # pidfile 存在且进程活着 = hook 成功进入 keepalive
                    logger.info(f"[Frida] hook installed (after {(i+1)*0.5:.1f}s)")
                    return True
            logger.warning("[Frida] hook did not confirm within 30s, see bin/Frida/daemon.log")
            return False
        except Exception as e:
            logger.warning(f"[Frida] spawn failed: {e}")
            return False