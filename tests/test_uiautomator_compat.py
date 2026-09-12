import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import uiautomator2 as u2
from packaging.version import Version

# Import applies the project compatibility patches.
import module.device.method.utils  # noqa: F401


class UiautomatorPackageVersionCompatTest(unittest.TestCase):
    def test_installed_helper_without_version_name_is_version_zero(self):
        device = object.__new__(u2._Device)
        device.shell = Mock(side_effect=[
            SimpleNamespace(exit_code=0),
            SimpleNamespace(output='versionCode=0\nversionName=null\n'),
            SimpleNamespace(exit_code=0),
        ])

        self.assertEqual(Version('0'), device._package_version('com.github.uiautomator.test'))

    def test_numeric_version_name_is_preserved(self):
        device = object.__new__(u2._Device)
        device.shell = Mock(side_effect=[
            SimpleNamespace(exit_code=0),
            SimpleNamespace(output='versionCode=2003003\nversionName=2.3.3\n'),
        ])

        self.assertEqual(Version('2.3.3'), device._package_version('com.github.uiautomator'))

    def test_missing_package_remains_none(self):
        device = object.__new__(u2._Device)
        device.shell = Mock(return_value=SimpleNamespace(exit_code=1))

        self.assertIsNone(device._package_version('missing.package'))


if __name__ == '__main__':
    unittest.main()
