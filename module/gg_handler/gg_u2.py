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

    def _return_to_game(self):
        self.device.app_start()
        logger.info('Return to Azur Lane and keep GG daemon in background')

    def exit(self):
        self.d.app_stop(f'{self.gg_package_name}')
        logger.attr('GG', 'Killed')

    def skip_error(self):
        _skipped = 0
        if self.d.xpath('//*[@text="重启游戏"]').exists:
            _skipped = 1
            logger.hr('Game died with GG panel')
        logger.info('No matter GG panel exists or not, Kill GG')
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
                    while time.monotonic() < deadline:
                        self.device.sleep(0.5)
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
                        if self.d(resourceId=f"{self.gg_package_name}:id/search_toolbar").exists:
                            run_xpath = (
                                f'//*[@resource-id="{self.gg_package_name}'
                                f':id/search_toolbar"]/android.widget.ImageView[last()]'
                            )
                            self._click_xpath(run_xpath)
                            logger.info('Click run Scripts')
                            self.device.sleep(0.3)
                            if self._run():
                                return 1
                            continue
                        if self.d(resourceId=f"{self.gg_package_name}:id/search_tab").exists:
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

    def _run(self):
        _run = False
        _set = False
        _confirmed = False
        import os
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
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            self.device.sleep(1)
            if self.d(resourceId=f"{self.gg_package_name}:id/file").exists:
                file_input = self.d(resourceId=f"{self.gg_package_name}:id/file")
                if file_input.get_text() != "/sdcard/Notes/Multiplier.lua":
                    file_input.send_keys("/sdcard/Notes/Multiplier.lua")
                    logger.info('Lua path set')
                # GG's native file picker is outside Accessibility on Android
                # 11. Submit it through normal Android coordinates.
                self._submit_native_file_dialog()
                logger.info('Click Run (native dialog fallback)')
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
            self.d.wait_timeout = 90.0

            if _set and _confirmed:
                try:
                    if self.d.xpath(confirm_xpath).exists:
                        self._click_xpath(confirm_xpath)
                    GGData(self.config).set_data(target='gg_on', value=True)
                finally:
                    pass
                GGData(self.config).set_data(target='gg_on', value='True')
                logger.attr('GG', 'Enabled')
                logger.info("Close the script")
            self.d.wait_timeout = 3
            if _set and _confirmed:
                break
        else:
            logger.warning('GG multiplier setup timed out after 90 seconds')
            return 0
        logger.hr('GG Enabled', level=2)
        # Keep GG and its root daemon alive after configuring the multiplier.
        # Force-stopping GG kills the daemon; the host watchdog then reopens the
        # full GG activity over the game and intercepts every Alas tap.
        self._return_to_game()
        return 1