import unittest
from unittest.mock import Mock

from module.config.config import AzurLaneConfig, Function


class SchedulerFairnessTest(unittest.TestCase):
    def _config(self):
        config = AzurLaneConfig.__new__(AzurLaneConfig)
        config.task = Function({
            'Scheduler': {
                'Enable': True,
                'Command': 'Event',
                'NextRun': '2020-01-01 00:00:00',
            }
        })
        config._task_switch_owner = config.task
        config.stop_event = None
        config.load = Mock()
        config.get_next_task = Mock()
        config.get_next = Mock(return_value=config.task)
        config.task_delay = Mock()
        config.cross_get = Mock(return_value=0)
        return config

    def test_zero_interval_farming_yields_to_other_pending_task(self):
        config = self._config()
        config.pending_task = []

        def populate():
            config.pending_task = [
                config.task,
                Function({
                    'Scheduler': {
                        'Enable': True,
                        'Command': 'Commission',
                        'NextRun': '2026-09-15 15:55:50',
                    }
                }),
            ]

        config.get_next_task.side_effect = populate

        self.assertTrue(config.task_switched())
        config.task_delay.assert_called_once_with(minute=5, task='Event')
        config.get_next.assert_not_called()

    def test_zero_interval_farming_continues_without_backlog(self):
        config = self._config()
        config.get_next_task.side_effect = lambda: setattr(
            config, 'pending_task', [config.task]
        )

        self.assertFalse(config.task_switched())
        config.task_delay.assert_not_called()
        config.get_next.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
