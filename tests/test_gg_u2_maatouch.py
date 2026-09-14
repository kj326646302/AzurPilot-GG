import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from module.gg_handler.gg_u2 import GGU2


class GgU2MaaTouchTest(unittest.TestCase):
    def _handler(self):
        handler = GGU2.__new__(GGU2)
        handler.device = Mock()
        handler.d = Mock()
        return handler

    def test_ui_object_click_uses_maatouch_center(self):
        handler = self._handler()
        selector = Mock()
        selector.center.return_value = (48.4, 72.8)

        handler._click_u2_object(selector)

        handler.device.click_maatouch.assert_called_once_with(48, 72)
        selector.click.assert_not_called()

    def test_xpath_click_uses_maatouch_center(self):
        handler = self._handler()
        element = Mock()
        element.center.return_value = (1190.9, 198.2)
        xpath_selector = Mock()
        xpath_selector.get.return_value = element
        handler.d.xpath.return_value = xpath_selector

        handler._click_xpath('//*[@text="执行"]')

        handler.d.xpath.assert_called_once_with('//*[@text="执行"]')
        xpath_selector.get.assert_called_once_with(timeout=3)
        handler.device.click_maatouch.assert_called_once_with(1190, 198)

    def test_enabled_multiplier_returns_to_game_without_killing_gg(self):
        handler = self._handler()
        handler.gg_package_name = 'com.example.gg'
        handler.device.package = 'com.bilibili.azurlane'
        handler.device.adb_shell.return_value = (
            'mResumedActivity: ActivityRecord{x u0 '
            'com.bilibili.azurlane/com.manjuu.azurlane.MainActivity t1}'
        )

        handler._return_to_game()

        handler.device.app_start.assert_called_once_with()
        handler.d.app_stop.assert_not_called()

    def test_return_to_game_explicitly_starts_game_if_gg_stays_foreground(self):
        handler = self._handler()
        handler.device.package = 'com.bilibili.azurlane'
        handler.device.adb_shell.side_effect = [
            'mResumedActivity: ActivityRecord{x u0 com.example.gg/.MainActivity t1}',
            '',
            'mResumedActivity: ActivityRecord{x u0 '
            'com.bilibili.azurlane/com.manjuu.azurlane.MainActivity t2}',
        ]

        handler._return_to_game()

        handler.device.adb_shell.assert_any_call([
            'am', 'start', '-n',
            'com.bilibili.azurlane/com.manjuu.azurlane.MainActivity',
        ], timeout=15)

    def test_read_multiplier_status_strips_output(self):
        handler = self._handler()
        handler.device.adb_shell.return_value = 'ok:8\n'

        self.assertEqual('ok:8', handler._read_multiplier_status())

    def test_read_multiplier_status_returns_empty_on_adb_error(self):
        handler = self._handler()
        handler.device.adb_shell.side_effect = RuntimeError('adb offline')

        self.assertEqual('', handler._read_multiplier_status())

    def test_script_dialog_detected_from_edit_field_before_cancel(self):
        handler = self._handler()
        handler.gg_package_name = 'com.example.gg'

        def selector(**kwargs):
            result = Mock()
            result.exists = kwargs.get('resourceId') == 'com.example.gg:id/edit'
            return result

        handler.d.side_effect = selector
        handler.d.xpath.return_value.exists = False

        self.assertTrue(handler._has_script_dialog())

    def test_restart_cleanup_keeps_daemon_and_returns_to_game(self):
        handler = self._handler()
        handler.gg_package_name = 'com.example.gg'
        handler.device.package = 'com.bilibili.azurlane'
        handler.device.adb_shell.return_value = (
            'mResumedActivity: ActivityRecord{x u0 '
            'com.bilibili.azurlane/com.manjuu.azurlane.MainActivity t1}'
        )
        handler.d.xpath.return_value.exists = False

        skipped = handler.skip_error()

        self.assertEqual(0, skipped)
        handler.device.app_start.assert_called_once_with()
        handler.d.app_stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
