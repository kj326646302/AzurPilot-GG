import logging
import unittest
from unittest.mock import Mock, patch

from alas import AzurLaneAutoScript
from module.exception import GameNotRunningError, GameTooManyClickError
from module.logger import error_context


class TestErrorContext(unittest.TestCase):
    def test_can_log_exception_summary_without_traceback(self):
        error = GameNotRunningError('Game not running')

        with patch('module.logger.logger.log') as log:
            error_context(
                title='游戏进程未运行',
                reason='任务执行前未检测到碧蓝航线游戏进程。',
                impact='当前任务跳过。',
                action='自动重启游戏。',
                exc=error,
                level=logging.WARNING,
                with_traceback=False,
            )

        self.assertFalse(log.call_args.kwargs['exc_info'])
        self.assertIn('异常：GameNotRunningError: Game not running', log.call_args.args[1])


class TestGgTaskRouting(unittest.TestCase):
    def _script(self):
        script = AzurLaneAutoScript.__new__(AzurLaneAutoScript)
        script.config_name = 'test'
        script.__dict__['config'] = Mock()
        script.__dict__['device'] = Mock()
        script._channel_float_done = True
        return script

    @patch('module.gg_handler.gg_handler.GGHandler')
    def test_normal_task_applies_gg_policy_before_execution(self, gg_handler):
        script = self._script()
        script.__dict__['hard'] = Mock()

        self.assertTrue(script.run('hard', skip_first_screenshot=True))

        gg_handler.assert_called_once_with(config=script.config, device=script.device)
        gg_handler.return_value.check_then_set_gg_status.assert_called_once_with('hard')
        script.hard.assert_called_once_with()

    @patch('module.gg_handler.gg_handler.GGHandler')
    def test_restart_does_not_enable_gg_before_login(self, gg_handler):
        script = self._script()
        script.__dict__['restart'] = Mock()

        self.assertTrue(script.run('restart', skip_first_screenshot=True))

        gg_handler.assert_not_called()
        script.restart.assert_called_once_with()


class TestGameNotRunningErrorHandling(unittest.TestCase):
    def test_schedules_restart_without_requesting_traceback(self):
        script = AzurLaneAutoScript.__new__(AzurLaneAutoScript)
        script.config_name = 'test'
        script._channel_float_done = True
        script.__dict__['config'] = Mock()
        script.__dict__['device'] = Mock()
        script.config.cross_get.return_value = False
        error = GameNotRunningError('Game not running')
        script.__dict__['commission'] = Mock(side_effect=error)

        with (
            patch('alas.logger.error_context') as error_context_mock,
            patch('alas.handle_notify'),
            patch('alas.notify_webui'),
        ):
            result = script.run('commission', skip_first_screenshot=True)

        self.assertEqual('recoverable', result)
        script.config.task_delay.assert_called_once_with(success=False)
        script.config.task_call.assert_called_once_with('Restart')
        error_context_mock.assert_called_once_with(
            title='游戏进程未运行',
            reason='任务执行前未检测到碧蓝航线游戏进程。',
            impact='当前任务跳过，调度器将自动安排 Restart 任务。',
            action='通常无需处理；若反复发生，请检查游戏包名、模拟器状态和登录流程。',
            exc=error,
            level=30,
            with_traceback=False,
        )


class TestRecoverableFailureBackoff(unittest.TestCase):
    def test_too_many_clicks_delays_failed_task_before_restart(self):
        script = AzurLaneAutoScript.__new__(AzurLaneAutoScript)
        script.config_name = 'test'
        script._channel_float_done = True
        script.consecutive_game_stuck = 0
        script.__dict__['config'] = Mock()
        script.__dict__['device'] = Mock()
        script.config.cross_get.return_value = False
        script.config.Error_GameStuckRestart = False
        script.config.Error_OnePushConfig = None
        script.device.package = 'com.bilibili.azurlane'
        script.__dict__['opsi_shop'] = Mock(
            side_effect=GameTooManyClickError('PINNED_DISABLE')
        )
        script.save_error_log = Mock()

        with (
            patch('alas.logger.error_context'),
            patch('alas.handle_notify'),
            patch('alas.notify_webui'),
        ):
            result = script.run('opsi_shop', skip_first_screenshot=True)

        self.assertEqual('recoverable', result)
        script.config.task_delay.assert_called_once_with(success=False)
        script.config.task_call.assert_called_once_with('Restart')
