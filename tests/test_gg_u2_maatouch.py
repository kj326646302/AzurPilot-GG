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

        handler._return_to_game()

        handler.device.app_start.assert_called_once_with()
        handler.d.app_stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
