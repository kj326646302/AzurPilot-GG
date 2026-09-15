import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MultiplierLuaVisibilityTest(unittest.TestCase):
    def test_every_terminal_path_hides_gameguardian(self):
        source = (PROJECT_ROOT / 'bin/Lua/Multiplier.lua').read_text(
            encoding='utf-8'
        )

        self.assertGreaterEqual(source.count('gg.setVisible(false)'), 4)
        self.assertIn('writeStatus("ok", results)', source)
        self.assertIn('writeStatus("not_found", 0)', source)
        self.assertIn('writeStatus("cancel", 0)', source)
        self.assertNotIn('gg.alert("未找到倍率数据', source)


if __name__ == '__main__':
    unittest.main()
