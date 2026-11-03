#!/usr/bin/env python3
"""Estimate Action 5 Pro field draw from bank/battery percentages and MP4 duration.

Estimates only: no battery fuel gauge or voltage/current meter data are read.
"""

from __future__ import annotations

import argparse


def estimate(*, video_minutes: float = 14, interval_s: float = 1, fps: float = 30,
             bank_mah: float = 10000, bank_cell_v: float = 3.7,
             bank_start: float = 90, bank_end: float = 0,
             camera_wh: float = 7.5, camera_start: float = 14, camera_end: float = 0,
             bank_efficiency: float = 0.85, next_bank_mah: float = 20000,
             next_bank_start: float = 100, next_camera_start: float = 50) -> dict:
    if any(x <= 0 for x in (video_minutes, interval_s, fps, bank_mah,
                             bank_cell_v, camera_wh, next_bank_mah)):
        raise ValueError("all durations, sizes, voltages, FPS and interval must be positive")
    if any(not 0 <= x <= 100 for x in (bank_start, bank_end, camera_start,
                                       camera_end, next_bank_start, next_camera_start)):
        raise ValueError("battery percentage must be in the range 0..100")
    if bank_start < bank_end or camera_start < camera_end:
        raise ValueError("ending battery percentages cannot exceed starting percentages")
    if not 0 < bank_efficiency <= 1:
        raise ValueError("conversion efficiency must be in (0,1]")
    capture_h = video_minutes / 60 * fps * interval_s
    bank_wh = bank_mah / 1000 * bank_cell_v * (bank_start - bank_end) / 100 * bank_efficiency
    cam_wh = camera_wh * (camera_start - camera_end) / 100
    total_wh = bank_wh + cam_wh
    day_w = total_wh / capture_h
    next_wh = next_bank_mah / 1000 * bank_cell_v * next_bank_start / 100 * bank_efficiency
    next_wh += camera_wh * next_camera_start / 100
    return {"capture_hours": capture_h, "inferred_available_wh": total_wh,
            "inferred_average_w": day_w,
            "next_power_source_wh": next_wh,
            "next_continuous_runtime_hours": next_wh / day_w}


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate power from a DJI timelapse field run")
    parser.add_argument("--video-min", type=float, default=14)
    parser.add_argument("--interval-s", type=float, required=True)
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--bank-mah", type=float, default=10000)
    parser.add_argument("--bank-start", type=float, default=90)
    parser.add_argument("--bank-end", type=float, default=0)
    parser.add_argument("--camera-start", type=float, default=14)
    parser.add_argument("--camera-end", type=float, default=0)
    parser.add_argument("--bank-efficiency", type=float, default=0.85)
    parser.add_argument("--next-bank-mah", type=float, default=20000)
    parser.add_argument("--next-bank-start", type=float, default=100)
    parser.add_argument("--next-camera-start", type=float, default=50)
    args = parser.parse_args()
    try:
        result = estimate(video_minutes=args.video_min, interval_s=args.interval_s,
                          fps=args.fps, bank_mah=args.bank_mah,
                          bank_start=args.bank_start, bank_end=args.bank_end,
                          camera_start=args.camera_start, camera_end=args.camera_end,
                          bank_efficiency=args.bank_efficiency,
                          next_bank_mah=args.next_bank_mah,
                          next_bank_start=args.next_bank_start,
                          next_camera_start=args.next_camera_start)
    except ValueError as exc:
        parser.error(str(exc))
    for name, value in result.items():
        print(f"{name}: {value:.2f}")
    print("WARNING: estimates from percentage gauges and assumed conversion efficiency, not measured watts.")


if __name__ == "__main__":
    main()
