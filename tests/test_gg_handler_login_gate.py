import unittest
from unittest.mock import Mock, patch

from module.exception import GameStuckError
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

    def test_not_found_aborts_task_and_removes_gg_overlay(self):
        handler = GGHandler.__new__(GGHandler)
        handler.config = Mock()
        handler.config.data = {
            'GGManager': {
                'GGHandler': {
                    'GGPackageName': 'com.example.gg',
                    'Timeout': 30,
                }
            }
        }
        handler.device = Mock()
        handler.factor = 2000
        handler.handle_u2_restart = Mock()
        handler._kill_stale_gg_daemons = Mock()
        handler._ensure_frida = Mock()

        gg_u2 = Mock()
        gg_u2.set_on.return_value = -1
        with patch(
            'module.gg_handler.gg_handler.GGU2', return_value=gg_u2
        ), patch('module.gg_handler.gg_handler.GGData.set_data'):
            with self.assertRaises(GameStuckError):
                handler.set(True)

        handler.device.adb_shell.assert_any_call([
            'am', 'force-stop', 'com.example.gg'
        ])
        handler.device.app_start.assert_called_once_with()
        handler._ensure_frida.assert_not_called()


if __name__ == '__main__':
    unittest.main()
