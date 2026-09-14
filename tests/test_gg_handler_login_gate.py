import unittest
from unittest.mock import Mock, patch

from module.gg_handler.gg_handler import GGHandler


class GGHandlerLoginGateTest(unittest.TestCase):
    def test_login_completes_before_enabling_multiplier(self):
        handler = GGHandler.__new__(GGHandler)
        handler.config = Mock()
        handler.config.data = {
            'GGManager': {
                'GGHandler': {
                    'AutoRestartGG': True,
                }
            }
        }
        handler.device = Mock()
        handler.set = Mock()
        events = []

        login = Mock()
        login.handle_app_login.side_effect = lambda: events.append('login')
        handler.set.side_effect = lambda mode: events.append(('set', mode))

        with patch(
            'module.gg_handler.gg_handler.GGData.get_data',
            return_value={
                'gg_enable': True,
                'gg_auto': True,
                'gg_on': False,
            },
        ), patch(
            'module.handler.login.LoginHandler',
            return_value=login,
        ):
            handler.check_status(True)

        self.assertEqual(['login', ('set', True)], events)


if __name__ == '__main__':
    unittest.main()
