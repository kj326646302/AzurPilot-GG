import unittest
from unittest.mock import Mock

from module.ui.ui import UI
from module.ui_white.assets import MAIN_GOTO_CAMPAIGN_WHITE


class UIRedroidNavigationTest(unittest.TestCase):
    def _ui(self, method='MaaTouch'):
        ui = UI.__new__(UI)
        ui.device = Mock()
        ui.config = Mock()
        ui.config.DEVICE_CONTROL_METHOD = method
        return ui

    def test_white_campaign_entry_uses_native_adb_with_maatouch(self):
        ui = self._ui('MaaTouch')

        ui._click_navigation_button(MAIN_GOTO_CAMPAIGN_WHITE)

        ui.device.handle_control_check.assert_called_once_with(
            MAIN_GOTO_CAMPAIGN_WHITE
        )
        ui.device.adb_shell.assert_called_once_with(
            ['input', 'tap', 1192, 508]
        )
        ui.device.click.assert_not_called()

    def test_other_control_methods_keep_normal_click(self):
        ui = self._ui('ADB')

        ui._click_navigation_button(MAIN_GOTO_CAMPAIGN_WHITE)

        ui.device.click.assert_called_once_with(MAIN_GOTO_CAMPAIGN_WHITE)
        ui.device.adb_shell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
