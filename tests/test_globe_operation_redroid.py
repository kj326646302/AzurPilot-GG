import unittest
from unittest.mock import Mock

from module.os.globe_operation import GlobeOperation
from module.os.globe_camera import GlobeCamera


class GlobeOperationRedroidTest(unittest.TestCase):
    def test_pinned_zone_uses_measured_native_adb_gesture(self):
        handler = GlobeOperation.__new__(GlobeOperation)
        handler.device = Mock()
        handler._zone_unpin_interval = Mock()
        handler._zone_unpin_interval.reached.return_value = True
        handler.is_zone_pinned = Mock(return_value=True)

        self.assertTrue(handler.handle_zone_pinned())

        handler.device.handle_control_check.assert_called_once_with('PINNED_DISABLE')
        handler.device.swipe_adb.assert_called_once_with(
            (460, 420), (300, 250), duration=0.7)
        handler._zone_unpin_interval.reset.assert_called_once_with()
        handler.device.swipe.assert_not_called()

    def test_pinned_zone_does_nothing_before_interval(self):
        handler = GlobeOperation.__new__(GlobeOperation)
        handler.device = Mock()
        handler._zone_unpin_interval = Mock()
        handler._zone_unpin_interval.reached.return_value = False
        handler.is_zone_pinned = Mock()

        self.assertFalse(handler.handle_zone_pinned())

        handler.is_zone_pinned.assert_not_called()
        handler.device.swipe_adb.assert_not_called()

    def test_pinned_zone_does_nothing_when_not_pinned(self):
        handler = GlobeOperation.__new__(GlobeOperation)
        handler.device = Mock()
        handler._zone_unpin_interval = Mock()
        handler._zone_unpin_interval.reached.return_value = True
        handler.is_zone_pinned = Mock(return_value=False)

        self.assertFalse(handler.handle_zone_pinned())

        handler.device.swipe_adb.assert_not_called()

    def test_globe_swipe_uses_adb_with_maatouch(self):
        handler = GlobeCamera.__new__(GlobeCamera)
        handler.device = Mock()
        handler.device.image = None
        handler.config = Mock()
        handler.config.DEVICE_CONTROL_METHOD = 'MaaTouch'
        handler.config.MAP_SWIPE_MULTIPLY_MAATOUCH = (1.0, 1.0)
        handler.globe_update = Mock()

        handler.globe_swipe((100, 80), box=(20, 220, 980, 620))

        handler.device.handle_control_check.assert_called_once()
        handler.device.swipe_adb.assert_called_once()
        handler.device.swipe_vector.assert_not_called()
        handler.globe_update.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
