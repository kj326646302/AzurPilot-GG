import unittest
from unittest.mock import Mock

from module.handler.login import LoginHandler


class LoginBilibiliRedroidTest(unittest.TestCase):
    def _handler(self):
        handler = LoginHandler.__new__(LoginHandler)
        handler.device = Mock()
        return handler

    def test_login_record_uses_native_adb_coordinates(self):
        handler = self._handler()
        handler._foreground_activity = Mock(
            return_value=(
                'com.bilibili.azurlane/'
                'com.gsc.login_record.LoginRecordActivity'
            )
        )

        self.assertTrue(handler._handle_bilibili_sdk_activity())

        handler.device.handle_control_check.assert_called_once_with(
            'BILIBILI_LOGIN_RECORD'
        )
        handler.device.adb_shell.assert_called_once_with(
            ['input', 'tap', 640, 420]
        )
        handler.device.sleep.assert_called_once_with(2)

    def test_other_activity_is_not_touched(self):
        handler = self._handler()
        handler._foreground_activity = Mock(
            return_value=(
                'com.bilibili.azurlane/'
                'com.manjuu.azurlane.MainActivity'
            )
        )

        self.assertFalse(handler._handle_bilibili_sdk_activity())

        handler.device.adb_shell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
