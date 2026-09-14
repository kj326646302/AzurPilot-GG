import time

import uiautomator2 as u2

from module.base.base import ModuleBase as Base
from module.config.config import deep_get
from module.gg_handler.gg_data import GGData
from module.logger import logger


class GGU2(Base):

    def __init__(self, config, device):
        super().__init__(config, device)
        self.factor = 200
        self.config = config
        self.device = device
        self.d = u2.connect(self.device.serial)
        self.gg_package_name = deep_get(self.config.data, keys='GGManager.GGHandler.GGPackageName')
        self.d.wait_timeout = 10.0

    def _click_u2_object(self, selector):
        x, y = selector.center()
        self.device.click_maatouch(int(x), int(y))

    def _click_xpath(self, xpath):
        element = self.d.xpath(xpath).get(timeout=3)
        x, y = element.center()
        self.device.click_maatouch(int(x), int(y))

    def _submit_native_file_dialog(self):
        """Confirm GG's non-accessible Android 11 file picker.

        The path field is visible to U2, but the native file list and EXECUTE
        button use normal Android coordinates rather than GG's rotated canvas.
        """
        self.device.adb_shell(['input', 'keyevent', 66])
        self.device.sleep(0.5)
        self.device.adb_shell(['input', 'tap', 685, 190])
        self.device.sleep(0.5)
        self.device.adb_shell(['input', 'tap', 960, 176])
        self.device.sleep(1)

    def _foreground_package(self) -> str:
        """Return the package of the activity currently in the foreground."""
        try:
            out = self.device.adb_shell(['dumpsys', 'activity', 'activities'], timeout=15)
        except Exception:
            return ''
        for line in str(out).splitlines():
            if 'mResumedActivity' in line:
                # ... ActivityRecord{... u0 com.example/.MainActivity t123}
                for token in line.split():
                    if '/' in token and '.' in token:
                        return token.split('/')[0]
        return ''

    def _return_to_game(self):
        """Bring the game back to the foreground and verify that it worked.

        GG opens its own activity while Alas drives the multiplier, and simply
        calling app_start() afterwards is not reliable on this reDroid: GG's
        MainActivity stayed resumed, so Alas screenshotted GG instead of the
        game, its taps landed on GG's window, and the game's title screen never
        advanced -- which shows up as "GameTooManyClickError: STORY_CLOSE,
        LOGIN_ANNOUNCE_2" and then a Restart.
        """
        # Device.package is the resolved game package (config.package is None).
        game_package = getattr(self.device, 'package', None)
        if not game_package or game_package == 'auto':
            logger.warning('[GG] game package is unknown; skipping foreground check')
            self.device.app_start()
            logger.info('Return to Azur Lane and keep GG daemon in background')
            return
        for attempt in range(3):
            try:
                self.device.app_start()
            except Exception as e:
                logger.warning(f'[GG] app_start failed: {e}')
            self.device.sleep(1.5)

            current = self._foreground_package()
            if current == game_package:
                logger.info('Return to Azur Lane and keep GG daemon in background')
                return
            logger.info(f'[GG] foreground is {current or "unknown"}, bringing the game back')
            try:
                self.device.adb_shell([
                    'am', 'start', '-n',
                    f'{game_package}/com.manjuu.azurlane.MainActivity',
                ], timeout=15)
            except Exception as e:
                logger.warning(f'[GG] am start game failed: {e}')
            self.device.sleep(2)

        current = self._foreground_package()
        if current != game_package:
            logger.warning(f'[GG] game is still not in the foreground (current={current})')
        else:
            logger.info('Return to Azur Lane and keep GG daemon in background')

    def exit(self):
        # Keep the GG root daemon alive. Killing the package makes the host
        # watchdog reopen the full GG activity, which covers the game login
        # screen and traps Alas in repeated LOGIN_CHECK taps.
        self._return_to_game()
        logger.attr('GG', 'Background')

    def skip_error(self):
        _skipped = 0
        restart_xpath = ('//*[@text="重启游戏" or @text="RESTART GAME" '
                         'or @text="Restart game"]')
        if self.d.xpath(restart_xpath).exists:
            _skipped = 1
            logger.hr('Game died with GG panel')
        logger.info('Return to game and keep GG daemon alive')
        self.exit()
        return _skipped

    def set_on(self, factor=200):
        _name_dict = {
            'en' : 'Azur Lane',
            'cn' : '碧蓝航线',
            'jp' : 'アズールレーン',
            'tw' : '碧藍航線'
        }
        _server = self.config.SERVER
        _name = _name_dict[_server]
        self.factor = factor
        ggdata = GGData(self.config).get_data()
        for _i in range(1):
            try:
                if ggdata['gg_on']:
                    logger.attr('GG', 'Enabled')
                    pass
                else:
                    chosen = False
                    if self.d(resourceId=f"{self.gg_package_name}:id/hot_point_icon").exists:
                        self._click_u2_object(self.d(resourceId=f"{self.gg_package_name}:id/hot_point_icon"))
                        logger.info('Open GG panel')
                        self.device.sleep(0.5)
                    else:
                        self.d.app_start(self.gg_package_name)
                        logger.info('Starting GG')
                        logger.info('In GG overview')
                        self.device.sleep(3)
                    deadline = time.monotonic() + 120
                    empty_since = None
                    clean_restart_done = False
                    while time.monotonic() < deadline:
                        self.device.sleep(0.5)

                        # Android 11 sometimes leaves GG in its self-drawn help/
                        # panel canvas after Cancel. That window has an empty
                        # accessibility tree, so every selector below is absent
                        # and the state machine used to wait forever. Recover once
                        # by restarting GG into its accessible starter page. Alas
                        # owns this transition; the host watchdog never touches
                        # GG UI.
                        xml = self.d.dump_hierarchy(compressed=False)
                        has_gg_node = self.gg_package_name in xml
                        if not has_gg_node:
                            if empty_since is None:
                                empty_since = time.monotonic()
                            elif not clean_restart_done and time.monotonic() - empty_since >= 5:
                                logger.info('GG accessibility tree empty; clean restart to starter page')
                                self.d.app_stop(self.gg_package_name)
                                self.device.sleep(1)
                                self.d.app_start(self.gg_package_name)
                                self.device.sleep(5)
                                clean_restart_done = True
                                empty_since = None
                                continue
                        else:
                            empty_since = None
                        ignore_xpath = '//*[@text="忽略" or @text="IGNORE" or @text="Ignore"]'
                        if self.d.xpath(ignore_xpath).exists:
                            self._click_xpath(ignore_xpath)
                            logger.info("Click ignore")
                            self.device.sleep(0.3)
                            continue
                        if self.d(resourceId=f"{self.gg_package_name}:id/btn_start_usage").exists:
                            self._click_u2_object(self.d(resourceId=f"{self.gg_package_name}:id/btn_start_usage"))
                            logger.info('Click GG start button')
                            logger.attr('GG', 'Started')
                            self.device.sleep(0.3)
                            continue
                        if self.d(resourceId=f"{self.gg_package_name}:id/hot_point_icon").exists:
                            self._click_u2_object(self.d(resourceId=f"{self.gg_package_name}:id/hot_point_icon"))
                            logger.info('Open GG panel')
                            self.device.sleep(0.3)
                            continue
                        if self.d(resourceId=f"{self.gg_package_name}:id/search_tab").exists \
                                and not self.d(resourceId=f"{self.gg_package_name}:id/search_toolbar").exists:
                            self._click_u2_object(self.d(resourceId=f"{self.gg_package_name}:id/search_tab"))
                            logger.info('Switch to search tab')
                            self.device.sleep(0.3)
                            continue
                        target_xpath = (
                            f'//*[@package="{self.gg_package_name}" '
                            f'and @resource-id="android:id/text1" '
                            f'and (contains(@text,"{_name}") '
                            f'or contains(@text,"com.bilibili.azurlane"))]'
                        )
                        if self.d.xpath(target_xpath).exists:
                            self._click_xpath(target_xpath)
                            logger.info('Choose APP: AzurLane')
                            self.device.sleep(0.3)
                            chosen = True
                            continue
                        if not chosen and self.d(resourceId=f"{self.gg_package_name}:id/app_icon").exists:
                            self._click_u2_object(self.d(resourceId=f"{self.gg_package_name}:id/app_icon"))
                            logger.info('Click APP choosing tag')
                            self.device.sleep(0.3)
                            continue
                        if self.d(resourceId=f"{self.gg_package_name}:id/search_toolbar").exists:
                            run_xpath = (
                                f'//*[@resource-id="{self.gg_package_name}'
                                f':id/search_toolbar"]/android.widget.ImageView[last()]'
                            )
                            self._click_xpath(run_xpath)
                            logger.info('Click run Scripts')
                            self.device.sleep(0.3)
                            run_result = self._run()
                            if run_result == 1:
                                return 1
                            if run_result == -1:
                                return 0
                            continue

                        # GG's Lua file picker and value prompt both contain a
                        # generic Cancel button. Checking Cancel first repeatedly
                        # dismissed the active script dialog, so the outer loop
                        # clicked it until the 120-second timeout. Hand ownership
                        # to _run() whenever any script-dialog control is visible;
                        # _run() submits the dialog once and waits for the disk
                        # completion marker.
                        if self._has_script_dialog():
                            logger.info('GG script dialog detected; wait for Lua completion')
                            run_result = self._run()
                            if run_result == 1:
                                return 1
                            if run_result == -1:
                                return 0
                            continue

                        cancel_xpath = '//*[@text="取消" or @text="CANCEL" or @text="Cancel"]'
                        if self.d.xpath(cancel_xpath).exists:
                            self._click_xpath(cancel_xpath)
                            logger.info("Cancel exists but not running script, click cancel")
                            self.device.sleep(0.3)
                            continue
                        confirm_xpath = '//*[@text="确定" or @text="OK" or @text="Ok"]'
                        if self.d.xpath(confirm_xpath).exists:
                            self._click_xpath(confirm_xpath)
                            logger.info("Confirm exists but script crashed, click confirm")
                            self.device.sleep(0.3)
                            continue
                        if self.d.xpath('//*[@text="重启游戏"]').exists:
                            self._click_xpath('//*[@text="重启游戏"]')
                            logger.info('GG Panel after game died exists, restart the game')
                            logger.info('Click Restart')
                            self.device.sleep(0.3)
                            continue
                    logger.warning('GG setup timed out after 120 seconds')
                    return 0
            finally:
                pass

    def _has_script_dialog(self) -> bool:
        """Return whether GG is already inside the Lua file/value dialog."""
        execute_xpath = '//*[@text="执行" or @text="EXECUTE" or @text="Execute"]'
        return bool(
            self.d(resourceId=f"{self.gg_package_name}:id/file").exists
            or self.d(resourceId=f"{self.gg_package_name}:id/edit").exists
            or self.d.xpath(execute_xpath).exists
        )

    def _read_multiplier_status(self) -> str:
        """Read the completion marker written by Multiplier.lua.

        GameGuardian's search/progress dialogs are custom canvas overlays and are
        invisible to uiautomator. UI disappearance therefore cannot be used as a
        completion signal. The Lua script writes this marker only after every
        search/refine/edit call has returned.
        """
        try:
            status = self.device.adb_shell(
                'if [ -f /sdcard/Notes/multiplier.status ]; then '
                'cat /sdcard/Notes/multiplier.status; fi')
        except Exception:
            return ''
        return str(status or '').strip()

    def _run(self):
        _set = False
        _confirmed = False
        _submitted = False
        _repush = deep_get(self.config.data, keys='GGManager.GGHandler.RepushLua')
        if _repush:
            # os.popen(f'"toolkit/Lib/site-packages/adbutils/binaries/adb.exe" -s'
            #          f' {self.device.serial} shell mkdir /sdcard/Notes')
            # self.device.sleep(0.5)
            # os.popen(f'"toolkit/Lib/site-packages/adbutils/binaries/adb.exe" -s'
            #          f' {self.device.serial} shell rm /sdcard/Notes/Multiplier.lua')
            # self.device.sleep(0.5)
            # os.popen(f'"toolkit/Lib/site-packages/adbutils/binaries/adb.exe" -s'
            #          f' {self.device.serial} push "bin/Lua/Multiplier.lua" /sdcard/Notes/Multiplier.lua')
            # self.device.sleep(0.5)
            self.device.adb_shell("mkdir /sdcard/Notes")
            self.device.sleep(0.5)
            self.device.adb_shell("rm /sdcard/Notes/Multiplier.lua")
            self.device.sleep(0.5)
            self.device.adb_push("bin/Lua/Multiplier.lua", "/sdcard/Notes/Multiplier.lua")
            self.device.sleep(0.5)
            logger.info('Lua Pushed')
        # A stale marker must never make a new invocation look successful.
        self.device.adb_shell('rm -f /sdcard/Notes/multiplier.status')

        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            self.device.sleep(1)

            status = self._read_multiplier_status()
            if status.startswith('ok:'):
                logger.info(f'GG multiplier completed: {status}')
                GGData(self.config).set_data(target='gg_on', value=True)
                logger.attr('GG', 'Enabled')
                logger.info('Close the script')
                break
            if status.startswith('not_found:'):
                logger.warning('GG multiplier search found no target value')
                return -1
            if status.startswith('cancel:'):
                logger.warning('GG multiplier prompt was cancelled')
                return -1

            # Submit the native file dialog exactly once. It remains visible for
            # a short period while GG starts the script and is outside the
            # accessibility tree; repeatedly tapping it races with the search UI.
            if not _submitted and self.d(resourceId=f"{self.gg_package_name}:id/file").exists:
                file_input = self.d(resourceId=f"{self.gg_package_name}:id/file")
                if file_input.get_text() != "/sdcard/Notes/Multiplier.lua":
                    file_input.send_keys("/sdcard/Notes/Multiplier.lua")
                    logger.info('Lua path set')
                self._submit_native_file_dialog()
                logger.info('Click Run (native dialog fallback)')
                _submitted = True
                continue
            execute_xpath = '//*[@text="执行" or @text="EXECUTE" or @text="Execute"]'
            if self.d.xpath(execute_xpath).exists:
                self._click_xpath(execute_xpath)
                logger.info('Click Run')
                self.device.sleep(0.5)
            change_xpath = ('//*[contains(@text,"修改面板") '
                            'or contains(@text,"Change") or contains(@text,"MODIFY")]')
            if self.d.xpath(change_xpath).exists:
                self._click_xpath(change_xpath)
                logger.info('Click Change Statistic')
                self.device.sleep(0.5)
            if self.d(resourceId=f"{self.gg_package_name}:id/edit").exists:
                self.d(resourceId=f"{self.gg_package_name}:id/edit").send_keys(f"{self.factor}")
                logger.info(f'Factor Set: {self.factor}')
                self.device.sleep(0.5)
                _set = True
            confirm_xpath = '//*[@text="确定" or @text="OK" or @text="Ok"]'
            if _set and self.d.xpath(confirm_xpath).exists:
                self._click_xpath(confirm_xpath)
                logger.info("Click confirm")
                self.device.sleep(0.5)
                _confirmed = True
            # _set/_confirmed only mean the prompt was submitted. Search can
            # continue for tens of seconds afterwards, so do not mark GG enabled
            # until Lua writes multiplier.status.
            self.d.wait_timeout = 3
        else:
            logger.warning('GG multiplier setup timed out after 180 seconds')
            return 0
        logger.hr('GG Enabled', level=2)
        # Keep GG and its root daemon alive after configuring the multiplier.
        # Force-stopping GG kills the daemon; the host watchdog then reopens the
        # full GG activity over the game and intercepts every Alas tap.
        self._return_to_game()
        return 1