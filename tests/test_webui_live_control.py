import unittest
from unittest.mock import patch

from module.webui.api import LiveControlDevice, _select_live_control_target


class LiveControlTargetTest(unittest.TestCase):
    @patch('module.webui.api.LiveControlDevice')
    @patch('module.webui.api.LiveWsScrcpySession.get')
    @patch('module.webui.api.LiveScrcpySession.get')
    def test_control_uses_local_adb_even_when_video_session_exists(
        self, raw_session_get, ws_session_get, control_device
    ):
        ws_session_get.return_value = object()
        raw_session_get.return_value = object()
        expected = control_device.return_value

        actual = _select_live_control_target('alas')

        self.assertIs(expected, actual)
        control_device.assert_called_once_with('alas')
        ws_session_get.assert_not_called()
        raw_session_get.assert_not_called()

    def test_return_type_is_documented_control_adapter(self):
        self.assertTrue(hasattr(LiveControlDevice, 'tap'))
        self.assertTrue(hasattr(LiveControlDevice, 'drag'))
        self.assertTrue(hasattr(LiveControlDevice, 'keycode'))
        self.assertTrue(hasattr(LiveControlDevice, 'text'))


if __name__ == '__main__':
    unittest.main()
