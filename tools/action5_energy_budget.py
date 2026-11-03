#!/usr/bin/env python3
"""Illustrative Action 5 Pro 8h/day energy budget; uses user-supplied watts.

DJI 0.5W spec means standby/low-power only, not measured 1s/2s Timelapse.
"""

import argparse


def budget(day_w: float, night_w: float, day_hours: float = 8,
           days: int = 7, bank_mah: float = 20000,
           cell_v: float = 3.7, efficiency: float = 0.85) -> dict:
    if min(day_w, night_w, day_hours, bank_mah, cell_v) < 0:
        raise ValueError("power, hours, mAh and cell voltage cannot be negative")
    if day_hours > 24 or days < 1 or not 0 < efficiency <= 1:
        raise ValueError("day_hours must be <=24, days >=1, efficiency in (0,1]")
    daytime_wh = day_w * day_hours * days
    nighttime_wh = night_w * (24 - day_hours) * days
    bank_usable_wh = bank_mah / 1000 * cell_v * efficiency
    needed_wh = daytime_wh + nighttime_wh
    return {"day_wh": daytime_wh, "night_wh": nighttime_wh,
            "total_wh": needed_wh, "bank_usable_wh": bank_usable_wh,
            "bank_only_coverage_ratio": (bank_usable_wh / needed_wh) if needed_wh else None}


def main():
    parser = argparse.ArgumentParser(description="Hypothetical Action 5 energy scenarios")
    parser.add_argument("--day-w", type=float, required=True, help="Measured or hypothetical capture W")
    parser.add_argument("--night-w", type=float, required=True, help="Measured or hypothetical idle W")
    parser.add_argument("--day-hours", type=float, default=8)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--bank-mah", type=float, default=20000)
    parser.add_argument("--cell-v", type=float, default=3.7)
    parser.add_argument("--efficiency", type=float, default=0.85)
    args = parser.parse_args()
    try:
        result = budget(args.day_w, args.night_w, args.day_hours,
                        args.days, args.bank_mah, args.cell_v, args.efficiency)
    except ValueError as exc:
        parser.error(str(exc))
    for key, value in result.items():
        print(f"{key}: {value:.2f}" if value is not None else f"{key}: undefined")
    print("These are scenario inputs, not measured DJI Timelapse watts.")


if __name__ == "__main__":
    main()
