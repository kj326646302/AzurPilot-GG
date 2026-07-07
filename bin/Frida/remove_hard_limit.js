/*
 * AlasGG Frida MOD: Remove Hard Mode Stat Limit
 *
 * 调用时机假定：游戏已登录、已进入主界面、Lua 全局表已加载
 *               所以直接 hook，不再等 lua_tolstring，不再 polling
 *
 * 复刻 PiePerseus 的 RemoveHardModeStatLimit：
 *   WorldFleetSelectLayer.CheckValid             -> true
 *   BossSingleBattleFleetSelectSubPanel.CheckValid -> true
 *   Chapter.IsEliteFleetLegal                    -> true
 */
'use strict';

const LUA_GLOBALSINDEX = -10002;

// 防止 NativeCallback 被 GC, 必须保持引用 (常驻在 globalThis)
globalThis._alasgg_hold = globalThis._alasgg_hold || {};

function safelog(msg) {
    try { console.log("[AlasGG-Frida] " + msg); } catch(e) {}
    try { send({ type: 'log', message: msg }); } catch(e) {}
}

function doHook(L_main, libtolua) {
    const lua_newthread    = new NativeFunction(libtolua.findExportByName("lua_newthread"),    'pointer', ['pointer']);
    const lua_getfield     = new NativeFunction(libtolua.findExportByName("lua_getfield"),     'void',    ['pointer', 'int', 'pointer']);
    const lua_setfield     = new NativeFunction(libtolua.findExportByName("lua_setfield"),     'void',    ['pointer', 'int', 'pointer']);
    const lua_pushcclosure = new NativeFunction(libtolua.findExportByName("lua_pushcclosure"), 'void',    ['pointer', 'pointer', 'int']);
    const lua_pushboolean  = new NativeFunction(libtolua.findExportByName("lua_pushboolean"),  'void',    ['pointer', 'int']);
    const lua_settop       = new NativeFunction(libtolua.findExportByName("lua_settop"),       'void',    ['pointer', 'int']);
    const lua_type         = new NativeFunction(libtolua.findExportByName("lua_type"),         'int',     ['pointer', 'int']);

    // trueFunc: 标准 lua_CFunction, push true, return 1
    if (!globalThis._alasgg_hold.trueFunc) {
        globalThis._alasgg_hold.trueFunc = new NativeCallback(function (L) {
            lua_pushboolean(L, 1);
            return 1;
        }, 'int', ['pointer']);
    }
    const trueFunc = globalThis._alasgg_hold.trueFunc;

    // 隔离协程: 共享 globals, 但栈独立, 不污染主 state
    const L = lua_newthread(L_main);
    safelog("created isolated thread L=" + L);

    function hookOne(path) {
        const parts = path.split('.');
        const last = parts[parts.length - 1];

        lua_settop(L, 0);

        const firstName = Memory.allocUtf8String(parts[0]);
        lua_getfield(L, LUA_GLOBALSINDEX, firstName);

        const t0 = lua_type(L, -1);
        if (t0 !== 5) {  // 5 = LUA_TTABLE
            safelog("[!] " + path + ": " + parts[0] + " not a table (type=" + t0 + ")");
            lua_settop(L, 0);
            return false;
        }

        for (let i = 1; i < parts.length - 1; i++) {
            const name = Memory.allocUtf8String(parts[i]);
            lua_getfield(L, -1, name);
            const ti = lua_type(L, -1);
            if (ti !== 5) {
                safelog("[!] " + path + ": " + parts[i] + " not a table (type=" + ti + ")");
                lua_settop(L, 0);
                return false;
            }
        }

        const backupName = Memory.allocUtf8String("old_" + last);
        const lastName = Memory.allocUtf8String(last);

        lua_getfield(L, -1, lastName);
        lua_setfield(L, -2, backupName);

        lua_pushcclosure(L, trueFunc, 0);
        lua_setfield(L, -2, lastName);

        lua_settop(L, 0);
        safelog("[+] hooked " + path);
        return true;
    }

    let ok = 0;
    if (hookOne("WorldFleetSelectLayer.CheckValid")) ok++;
    if (hookOne("BossSingleBattleFleetSelectSubPanel.CheckValid")) ok++;
    if (hookOne("Chapter.IsEliteFleetLegal")) ok++;

    if (ok === 3) {
        send({ type: 'result', status: 'ok', hooked: ok });
        safelog("=== INSTALLED (" + ok + "/3) ===");
    } else {
        send({ type: 'result', status: 'partial', hooked: ok });
        safelog("=== PARTIAL/FAILED (" + ok + "/3) — globals not ready, retry after game UI fully loaded ===");
    }
}

/*
 * 入口: 拿到当前主 lua_State 立即 hook
 *
 * 我们没有现成的 L_main, 但有个简单办法:
 * 拦截下一次 lua_tolstring 调用拿 L (这个调用频率超高, 几乎瞬时触发),
 * 拿到后立即 detach. 注意: 假定游戏 Lua 此时已经活跃, 否则会等.
 */
function start() {
    safelog("AlasGG-Frida-HardLimit script starting...");

    const libtolua = Process.findModuleByName("libtolua.so");
    if (!libtolua) {
        safelog("[!] libtolua.so not loaded — game not at gameplay phase, abort");
        send({ type: 'result', status: 'no_libtolua' });
        return;
    }
    safelog("libtolua.so @ " + libtolua.base);

    const lua_tolstring_addr = libtolua.findExportByName("lua_tolstring");
    if (!lua_tolstring_addr) {
        safelog("[!] lua_tolstring not found");
        send({ type: 'result', status: 'no_lua_tolstring' });
        return;
    }

    let done = false;
    const ic = Interceptor.attach(lua_tolstring_addr, {
        onEnter: function (args) {
            if (done) return;
            done = true;
            const L_main = args[0];
            if (L_main.isNull()) { done = false; return; }
            try {
                doHook(L_main, libtolua);
            } catch (e) {
                safelog("[!] hook exception: " + e + "\n" + (e.stack || ''));
                send({ type: 'result', status: 'exception', error: String(e) });
            }
            setTimeout(function () {
                try { ic.detach(); } catch(e) {}
            }, 50);
        }
    });

    safelog("waiting for first lua_tolstring call to grab L_main ...");
}

start();