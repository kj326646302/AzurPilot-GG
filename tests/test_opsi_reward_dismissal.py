import unittest
from unittest.mock import Mock

from module.combat.assets import GET_ITEMS_1, GET_ITEMS_2, GET_ITEMS_3
from module.os_handler.assets import CLICK_SAFE_AREA, GET_ADAPTABILITY
from module.os_handler.map_event import MapEventHandler


class OpsiRewardDismissalTest(unittest.TestCase):
    def _handler_for(self, visible):
        handler = MapEventHandler.__new__(MapEventHandler)
        handler.device = Mock()
        handler.is_in_map = Mock(return_value=False)
        handler.appear = Mock(side_effect=lambda button, **kwargs: button is visible)
        return handler

    def test_regular_item_rewards_click_their_continue_button(self):
        for reward in (GET_ITEMS_1, GET_ITEMS_2, GET_ITEMS_3):
            with self.subTest(reward=reward.name):
                handler = self._handler_for(reward)
                self.assertTrue(handler.handle_map_get_items())
                handler.device.click.assert_called_once_with(reward)

    def test_adaptability_reward_keeps_safe_area_behavior(self):
        handler = self._handler_for(GET_ADAPTABILITY)
        self.assertTrue(handler.handle_map_get_items())
        handler.device.click.assert_called_once_with(CLICK_SAFE_AREA)


if __name__ == '__main__':
    unittest.main()
