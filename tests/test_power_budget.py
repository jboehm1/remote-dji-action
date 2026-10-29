"""Regression checks for the reproducible controller power model.

Run: python3 -m unittest discover -s tests -p 'test_power_budget.py' -v
"""
from pathlib import Path
import importlib.util
import unittest


MODULE = Path(__file__).resolve().parents[1] / "tools" / "esp32_power_budget.py"
SPEC = importlib.util.spec_from_file_location("esp32_power_budget", MODULE)
POWER = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = POWER
SPEC.loader.exec_module(POWER)


class PowerBudgetTests(unittest.TestCase):
    def test_low_leakage_board_two_daily_sessions(self):
        scenario = POWER.Scenario("baseline", 30, 100, 60, 2)
        self.assertAlmostEqual(scenario.energy_wh_day(), 0.0133667, places=6)
        self.assertAlmostEqual(scenario.input_mah_day(), 3.145, places=2)

    def test_always_on_dominates(self):
        scenario = POWER.Scenario("always_on", 50000, 50, 0, 0)
        self.assertAlmostEqual(scenario.energy_wh_day(), 3.96, places=6)
        self.assertLess(scenario.battery_days(), 1)

    def test_more_events_draw_more_energy(self):
        base = POWER.Scenario("base", 30, 100, 60, 2)
        extra = POWER.Scenario("extra", 30, 100, 60, 96)
        self.assertGreater(extra.energy_wh_day(), base.energy_wh_day())

    def test_bad_usage_is_rejected(self):
        with self.assertRaises(ValueError):
            POWER.Scenario("invalid", 30, 100, 3600, 25).energy_wh_day()
        with self.assertRaises(ValueError):
            POWER.Scenario("invalid", 30, 100, 60, -1).energy_wh_day()
        with self.assertRaises(ValueError):
            POWER.Scenario("bad", 30, 100, 60, 2).input_mah_day(efficiency=0)


if __name__ == "__main__":
    unittest.main()
