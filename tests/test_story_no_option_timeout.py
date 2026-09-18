import unittest
from unittest.mock import Mock, patch

from module.handler.assets import STORY_SKIP, STORY_SKIP_3
from module.handler.info_handler import InfoHandler


class StoryNoOptionTimeoutTest(unittest.TestCase):
    def _handler(self):
        handler = InfoHandler.__new__(InfoHandler)
        handler.device = Mock()
        handler.config = Mock()
        handler.config.STORY_ALLOW_SKIP = False
        handler.story_popup_timeout = Mock()
        handler.story_popup_timeout.started.return_value = False
        handler._story_option_timer = Mock()
        handler._story_option_timer.reached.return_value = True
        handler._story_option_record = 0
        handler._story_option_confirm = Mock()
        handler._story_confirm = Mock()
        handler._story_no_option_timeout = Mock()
        handler.appear = Mock(side_effect=lambda button, **kwargs: button is STORY_SKIP_3)
        handler.appear_then_click = Mock(return_value=False)
        handler.interval_reset = Mock()
        handler.interval_clear = Mock()
        handler._is_story_black = Mock(return_value=False)
        handler._story_option_buttons_2 = Mock(return_value=[])
        return handler

    def test_no_options_for_timeout_clicks_visible_skip(self):
        handler = self._handler()
        handler._story_no_option_timeout.reached.return_value = True

        self.assertTrue(handler.story_skip())
        handler.device.click.assert_called_once_with(STORY_SKIP)
        handler._story_no_option_timeout.reset.assert_called_once_with()

    def test_no_options_before_timeout_keeps_normal_story_handling(self):
        handler = self._handler()
        handler._story_no_option_timeout.reached.return_value = False
        handler._story_confirm.reached.return_value = False

        self.assertFalse(handler.story_skip())
        self.assertNotIn(
            ((STORY_SKIP,), {}),
            handler.device.click.call_args_list,
        )

    def test_interval_throttled_second_check_does_not_reset_no_option_timeout(self):
        handler = self._handler()
        handler._story_no_option_timeout.reached.return_value = False
        handler._story_confirm.reached.return_value = False
        handler.appear.side_effect = [True, False]

        self.assertFalse(handler.story_skip())
        handler._story_no_option_timeout.reset.assert_not_called()

    def test_visible_options_reset_no_option_timeout(self):
        handler = self._handler()
        option = Mock()
        handler._story_option_buttons_2.return_value = [option]
        handler._story_option_record = 0
        handler._story_confirm.reached.return_value = False

        self.assertFalse(handler.story_skip())
        handler._story_no_option_timeout.reset.assert_called_once_with()
        self.assertNotIn(
            ((STORY_SKIP,), {}),
            handler.device.click.call_args_list,
        )


if __name__ == '__main__':
    unittest.main()
