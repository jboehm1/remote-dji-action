"""Owner field calibration must distinguish accelerated video and capture time."""

import unittest

from tools.action5_calibrate import estimate


class CalibrationTests(unittest.TestCase):
    def test_14_min_movie_one_second_interval(self):
        result = estimate(interval_s=1, fps=30)
        self.assertAlmostEqual(result["capture_hours"], 7)
        self.assertAlmostEqual(result["inferred_available_wh"], 29.355)
        self.assertAlmostEqual(result["inferred_average_w"], 29.355 / 7)
        self.assertAlmostEqual(result["next_power_source_wh"], 66.65)

    def test_14_min_movie_two_second_interval(self):
        result = estimate(interval_s=2, fps=30)
        self.assertEqual(result["capture_hours"], 14)
        self.assertAlmostEqual(result["inferred_average_w"], 29.355 / 14)

    def test_25_fps(self):
        self.assertAlmostEqual(estimate(interval_s=1, fps=25)["capture_hours"], 35 / 6)

    def test_input_checks(self):
        for config in ({"interval_s": 0, "fps": 30},
                       {"interval_s": 1, "fps": 30, "bank_end": 95},
                       {"interval_s": 1, "fps": 30, "bank_efficiency": 1.1},
                       {"interval_s": 1, "fps": 30, "next_camera_start": -1}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                estimate(**config)


if __name__ == "__main__":
    unittest.main()
