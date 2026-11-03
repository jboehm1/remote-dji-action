"""Offline tests for explicit (non-measured) Action 5 scenario arithmetic."""

import unittest

from tools.action5_energy_budget import budget


class Action5BudgetTests(unittest.TestCase):
    def test_weekly_budget(self):
        result = budget(1.5, 0.5)
        self.assertAlmostEqual(result["day_wh"], 84)
        self.assertAlmostEqual(result["night_wh"], 56)
        self.assertAlmostEqual(result["total_wh"], 140)
        self.assertAlmostEqual(result["bank_usable_wh"], 62.9)

    def test_switched_off_night(self):
        result = budget(1.0, 0.0)
        self.assertEqual(result["total_wh"], 56)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            budget(-1, 0)
        with self.assertRaises(ValueError):
            budget(1, 0, day_hours=25)
        with self.assertRaises(ValueError):
            budget(1, 0, efficiency=0)


if __name__ == "__main__":
    unittest.main()
