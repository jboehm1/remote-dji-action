"""Reproducible *estimates* of ESP32-C6 daily energy, not measured hardware power.

References:
- ESP32-C6 datasheet: deep sleep 7 uA chip-only, BLE RX 71 mA peak,
  BLE TX 94--315 mA peak (power setting dependent).
- The ESP-IDF proof-of-concept CURRENTLY RUNS WIFI/BLE AND DOES NOT
  CALL esp_deep_sleep_start(). Its energy is closer to always-on cases.
- Real board leakage, regulators, power source and camera wake retries
  require measurements. These are engineering scenarios, not warranties.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    sleep_ua: float
    active_ma: float
    awake_seconds_per_event: float
    events_per_day: int
    voltage_v: float = 3.3

    def energy_wh_day(self) -> float:
        if self.events_per_day < 0 or self.awake_seconds_per_event < 0:
            raise ValueError("durations must be nonnegative")
        active_hours = self.events_per_day * self.awake_seconds_per_event / 3600.0
        if active_hours > 24:
            raise ValueError("events add up to more than a day")
        sleep_hours = 24 - active_hours
        total_mah = (self.sleep_ua / 1000.0) * sleep_hours + self.active_ma * active_hours
        return total_mah * self.voltage_v / 1000.0

    def input_mah_day(self, supply_v: float = 5.0, efficiency: float = 0.85) -> float:
        if supply_v <= 0 or not 0 < efficiency <= 1:
            raise ValueError("invalid power supply assumptions")
        return 1000.0 * self.energy_wh_day() / (supply_v * efficiency)

    def battery_days(self, battery_mah: float = 1000, battery_v: float = 3.7,
                     efficiency: float = 0.85) -> float:
        if battery_mah <= 0 or battery_v <= 0 or not 0 < efficiency <= 1:
            raise ValueError("invalid battery assumptions")
        wh = self.energy_wh_day()
        return (battery_mah / 1000.0 * battery_v * efficiency) / wh if wh else float("inf")


SCENARIOS = [
    Scenario("ESP32-C6 chip ONLY theoretical, 2 x 30 s", 7, 100, 30, 2),
    Scenario("Low-leakage 30uA board, 2 x 60 s", 30, 100, 60, 2),
    Scenario("Conservative 100uA board, 2 x 120 s", 100, 150, 120, 2),
    Scenario("Every 15 min: 96 x 5 s (not proven to retain camera wake)", 30, 120, 5, 96),
    Scenario("Dev board 1mA sleep, 2 x 60 s", 1000, 100, 60, 2),
    Scenario("Dev board 5mA sleep, 2 x 60 s", 5000, 100, 60, 2),
    Scenario("Always on 20mA (idealized idle BLE example)", 20000, 20, 0, 0),
    Scenario("Always on 50mA (Wi-Fi / BLE controller example)", 50000, 50, 0, 0),
]


def main() -> None:
    print("Scenarios: controller energy only; no DJI camera energy.")
    print(f"{'Scenario':<68} {'Wh/day':>9} {'5V mAh/day':>12} {'1000mAh days':>14}")
    for s in SCENARIOS:
        print(f"{s.name:<68} {s.energy_wh_day():9.4f} "
              f"{s.input_mah_day():12.1f} {s.battery_days():14.1f}")
    print("Conversion assumes 85% DC efficiency and 3.3V controller rail.")
    print("Battery-days are idealized; capacity, self-discharge and low-temp effects excluded.")


if __name__ == "__main__":
    main()
