import logging
import unittest
from unittest.mock import Mock, patch

from alas import AzurLaneAutoScript
from module.exception import GameNotRunningError, ScriptEnd
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


class TestSensitiveTaskHandling(unittest.TestCase):
    def _script(self, strict_restart, sensitive):
        script = AzurLaneAutoScript.__new__(AzurLaneAutoScript)
        script.config_name = 'test'
        script.__dict__['config'] = Mock()
        script.config.Error_StrictRestart = strict_restart
        script.config.cross_get.return_value = sensitive
        return script

    def test_sensitive_task_does_not_exit_when_strict_restart_is_disabled(self):
        script = self._script(strict_restart=False, sensitive=True)

        self.assertFalse(script._check_sensitive_exit('opsi_obscure', RuntimeError('x')))

    def test_sensitive_task_exits_when_strict_restart_is_enabled(self):
        script = self._script(strict_restart=True, sensitive=True)

        with (
            patch('alas.logger.error_context'),
            patch('alas.handle_notify'),
            patch('alas.notify_webui'),
            self.assertRaises(SystemExit),
        ):
            script._check_sensitive_exit('opsi_obscure', RuntimeError('x'))


class TestIntentionalScriptEndHandling(unittest.TestCase):
    @patch('module.gg_handler.gg_handler.GGHandler')
    def test_script_end_is_successful_control_flow(self, gg_handler):
        script = AzurLaneAutoScript.__new__(AzurLaneAutoScript)
        script.config_name = 'test'
        script._channel_float_done = True
        script.__dict__['config'] = Mock()
        script.__dict__['device'] = Mock()
        script.__dict__['opsi_ash_beacon'] = Mock(
            side_effect=ScriptEnd('delayed by emotion guard')
        )

        result = script.run('opsi_ash_beacon', skip_first_screenshot=True)

        self.assertTrue(result)
        script.config.task_call.assert_not_called()


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
