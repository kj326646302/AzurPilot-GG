"""
AlasGG Frida 一次性注入 + keepalive

设计：
  - 假定调用时机：AlasGG 已重启游戏、登录完毕、进入主界面、GG 倍率已开
  - 注入 remove_hard_limit.js，等 'result' 消息确认 hook 成功
  - 成功后保持进程活着（守住 NativeCallback 内存），直到游戏崩溃 / 被杀
  - 失败立即退出（exit code != 0），让上层 frida_handler 知道

控制流：
  python inject.py <PID>
    -> attach
    -> load script
    -> 等待 result 消息 (timeout 30s)
    -> 成功: 保持 idle，监听 detached
    -> 失败: 退出
"""
import sys
import os
import time
import threading
import subprocess
import socket
import frida

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "remove_hard_limit.js")
PIDFILE = os.path.join(SCRIPT_DIR, "daemon.pid")
LOGFILE = os.path.join(SCRIPT_DIR, "daemon.log")

FRIDA_HOST = "127.0.0.1:27042"

def _detect_adb():
    """
    探测 adb 可执行文件。
    优先级: 环境变量 ALASGG_ADB > PATH 里的 adb > 项目内 adbutils 自带的 adb
    (不硬编码任何用户私有路径)
    """
    env = os.environ.get("ALASGG_ADB")
    if env and os.path.exists(env):
        return env
    import shutil
    found = shutil.which("adb")
    if found:
        return found
    # 项目内 adbutils 自带的 adb (相对本文件向上找项目根)
    try:
        import adbutils
        bundled = os.path.join(os.path.dirname(adbutils.__file__), "binaries", "adb.exe")
        if os.path.exists(bundled):
            return bundled
    except Exception:
        pass
    return "adb"

ADB = _detect_adb()
ADB_SERIAL = os.environ.get("ALASGG_ADB_SERIAL", "127.0.0.1:7555")
DEVICE_FRIDA_SERVER = "/data/local/tmp/frida-server"

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def adb(*args, timeout=10):
    try:
        out = subprocess.check_output(
            [ADB, "-s", ADB_SERIAL] + list(args),
            stderr=subprocess.STDOUT, timeout=timeout,
        )
        return out.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[adb error] {e}"

def is_frida_port_open():
    try:
        s = socket.create_connection(("127.0.0.1", 27042), timeout=1.5)
        s.close()
        return True
    except Exception:
        return False

def ensure_frida_server():
    if is_frida_port_open():
        return True
    log("frida-server not listening, starting on device ...")
    adb("shell", f"nohup {DEVICE_FRIDA_SERVER} >/dev/null 2>&1 &")
    adb("forward", "tcp:27042", "tcp:27042")
    for _ in range(15):
        time.sleep(0.5)
        if is_frida_port_open():
            log("frida-server port up")
            return True
    log("[!] frida-server failed to come up")
    return False

def write_pidfile():
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

def remove_pidfile():
    try:
        os.remove(PIDFILE)
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        log("Usage: inject.py <game_pid>")
        sys.exit(2)
    try:
        pid = int(sys.argv[1])
    except Exception:
        log(f"invalid pid: {sys.argv[1]}")
        sys.exit(2)

    log(f"=== AlasGG Frida one-shot inject, target pid={pid}, my pid={os.getpid()} ===")
    write_pidfile()

    if not ensure_frida_server():
        sys.exit(3)

    mgr = frida.get_device_manager()
    try:
        dev = mgr.add_remote_device(FRIDA_HOST)
    except Exception:
        dev = None
        for d in mgr.enumerate_devices():
            if d.id == f"socket@{FRIDA_HOST}":
                dev = d; break
        if dev is None:
            log("[!] cannot reach frida-server")
            sys.exit(4)

    try:
        session = dev.attach(pid)
    except Exception as e:
        log(f"[!] attach failed: {e}")
        sys.exit(5)
    log(f"attached pid={pid}")

    detached_reason = {"v": None}
    def on_detached(reason, *_a, **_kw):
        detached_reason["v"] = reason
        log(f"session detached: reason={reason}")
    session.on("detached", on_detached)

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_src = f.read()
    script = session.create_script(script_src)

    result_evt = threading.Event()
    result = {"status": None, "hooked": 0, "error": None}

    def on_message(message, data):
        if message.get("type") == "send":
            payload = message.get("payload", {})
            if isinstance(payload, dict):
                kind = payload.get("type")
                if kind == "log":
                    log(f"[GAME] {payload.get('message')}")
                elif kind == "result":
                    result["status"] = payload.get("status")
                    result["hooked"] = payload.get("hooked", 0)
                    result["error"] = payload.get("error")
                    result_evt.set()
                else:
                    log(f"[GAME] {payload}")
            else:
                log(f"[GAME] {payload}")
        elif message.get("type") == "error":
            log(f"[ERROR] {message.get('description')}")
            result["status"] = "frida_error"
            result["error"] = message.get("description")
            result_evt.set()

    script.on("message", on_message)
    script.load()
    log("script loaded, waiting for hook result ...")

    # 等结果 (脚本会在 doHook 完成后 send result)
    got = result_evt.wait(timeout=30)
    if not got:
        log("[!] timeout waiting for hook result, exit")
        try: session.detach()
        except Exception: pass
        remove_pidfile()
        sys.exit(6)

    if result["status"] != "ok":
        log(f"[!] hook not fully ok: {result}")
        try: session.detach()
        except Exception: pass
        remove_pidfile()
        sys.exit(7)

    log(f"=== HOOK INSTALLED ({result['hooked']}/3), entering keepalive ===")

    # Keepalive: 保住 NativeCallback (trueFunc) 内存不被 GC
    # 游戏崩溃/detach => 退出
    while detached_reason["v"] is None:
        time.sleep(2)

    log("game session ended, exit keepalive")
    remove_pidfile()

if __name__ == "__main__":
    try:
        main()
    finally:
        remove_pidfile()