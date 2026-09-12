import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from module.gg_handler.gg_u2 import GGU2


class GgU2LocaleTest(unittest.TestCase):
    def test_native_file_dialog_uses_fixed_execute_button(self):
        handler = GGU2.__new__(GGU2)
        handler.device = Mock()
        handler.d = Mock()
        handler.config = SimpleNamespace(data={
            'GGManager': {'GGHandler': {'RepushLua': False}},
        })
        handler.gg_package_name = 'com.example.gg'
        handler.factor = 2000
        file_input = Mock()
        file_input.exists = True
        file_input.get_text.return_value = '/sdcard/Notes/Multiplier.lua'
        handler.d.return_value = file_input

        handler.device.sleep.side_effect = [None, None, None, RuntimeError('stop')]
        with self.assertRaisesRegex(RuntimeError, 'stop'):
            handler._run()

        self.assertEqual(
            [
                ((['input', 'keyevent', 66],), {}),
                ((['input', 'tap', 685, 190],), {}),
                ((['input', 'tap', 960, 176],), {}),
            ],
            handler.device.adb_shell.call_args_list,
        )
        file_input.send_keys.assert_not_called()

    def test_execute_selector_accepts_english_label(self):
        handler = GGU2.__new__(GGU2)
        handler.device = Mock()
        handler.d = Mock()
        handler.config = SimpleNamespace(data={
            'GGManager': {'GGHandler': {'RepushLua': False}},
        })
        handler.gg_package_name = 'com.example.gg'
        handler.factor = 2000

        xpath_selectors = {}

        def xpath(value):
            selector = xpath_selectors.setdefault(value, Mock())
            selector.exists = 'EXECUTE' in value
            return selector

        handler.d.xpath.side_effect = xpath
        handler.d.return_value.exists = False
        handler._click_xpath = Mock()
        handler._run = GGU2._run.__get__(handler)

        # Stop after the execute click by making sleep raise a sentinel.
        handler.device.sleep.side_effect = [None, RuntimeError('stop')]
        with self.assertRaisesRegex(RuntimeError, 'stop'):
            handler._run()

        execute_xpath = '//*[@text="执行" or @text="EXECUTE" or @text="Execute"]'
        handler._click_xpath.assert_called_once_with(execute_xpath)


if __name__ == '__main__':
    unittest.main()
