#!/usr/bin/env python3
"""Local Osmo Client API controller for Raspberry Pi 4 / Linux.

This does not talk directly to a camera: Osmo Client establishes BLE + Wi-Fi,
exposes its HTTP API on 127.0.0.1 and decodes status. No third-party Python
dependencies. Physical Action 5 Pro testing is still required.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


LOG = logging.getLogger("osmo_pi")
DAY_NUMBERS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class ControlError(RuntimeError):
    pass


class OsmoClient:
    def __init__(self, port: int = 8091):
        if not 1 <= port <= 65535:
            raise ValueError("invalid local port")
        # Security invariant: never send camera commands to a remote host.
        self.base = f"http://127.0.0.1:{port}"

    def request(self, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = Request(self.base + path, data=body, headers=headers,
                      method="POST" if body is not None else "GET")
        try:
            with urlopen(req, timeout=12) as response:
                answer = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise ControlError(f"Osmo Client API {path}: {exc}") from exc
        if not isinstance(answer, dict):
            raise ControlError(f"Unexpected JSON from {path}")
        return answer

    def status(self) -> dict:
        return self.request("/api/status")

    def command(self, path: str, payload: dict | None = None) -> dict:
        reply = self.request(path, {} if payload is None else payload)
        if not reply.get("ok"):
            raise ControlError(f"Camera rejected {path}: {reply}")
        return reply


def verify_status(status: dict, *, expected_model: str = "Osmo Action 5 Pro",
                  must_be_infinite: bool = False, assume_infinite: bool = False,
                  require_timelapse: bool = True) -> None:
    if not (status.get("connected") and status.get("fresh") and status.get("link") == "on"):
        raise ControlError("Camera not connected / status stale (check Osmo Client page)")
    active = status.get("active") or {}
    if active.get("model") != expected_model:
        raise ControlError(f"Wrong/unknown camera {active.get('model')!r}; expected {expected_model!r}")
    if require_timelapse and status.get("capture_mode") != 2:
        raise ControlError("Camera is not in native Timelapse mode (mode 2)")
    if must_be_infinite:
        lapse = status.get("lapse") or {}
        if lapse.get("duration") != 0 and not (assume_infinite and "duration" not in lapse):
            raise ControlError("Timelapse is not confirmed at infinity (duration=0). Set it on camera. "
                               "Use --assume-infinite ONLY if camera does not publish the value.")


def record_state(status: dict) -> str:
    return (status.get("record") or {}).get("state") or "unknown"


def wait_record_state(client: OsmoClient, target: str, *, model: str,
                      timeout: float = 15.0, monotonic=time.monotonic,
                      sleep=time.sleep) -> bool:
    end = monotonic() + timeout
    while monotonic() < end:
        sleep(0.7)
        status = client.status()
        try:
            verify_status(status, expected_model=model)
        except ControlError:
            continue
        if record_state(status) == target:
            return True
    return False


def hhmm(value: str) -> int:
    try:
        hour, minute = map(int, value.split(":"))
        if 0 <= hour < 24 and 0 <= minute < 60 and len(value.split(":")) == 2:
            return hour * 60 + minute
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("Time must be HH:MM (24-hour)")


def parse_days(value: str) -> set[int]:
    if value == "all":
        return set(range(7))
    names = [v.strip().lower() for v in value.split(",")]
    if not names or any(v not in DAY_NUMBERS for v in names):
        raise argparse.ArgumentTypeError("Use all or mon,tue,wed,thu,fri,sat,sun")
    return {DAY_NUMBERS[v] for v in names}


def session_for(now: dt.datetime, start: int, end: int,
                days: set[int]) -> str | None:
    """Return the local calendar day that opened this active time window."""
    if start == end:
        raise ValueError("Start and end cannot be equal")
    minute = now.hour * 60 + now.minute
    start_day = now.date()
    if start < end:
        if not start <= minute < end:
            return None
    elif minute >= start:
        pass
    elif minute < end:
        start_day -= dt.timedelta(days=1)
    else:
        return None
    return start_day.isoformat() if start_day.weekday() in days else None


def atomic_save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_name(path.name + ".tmp")
    with stage.open("w", encoding="utf-8") as output:
        json.dump(state, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    stage.replace(path)


def load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        return data
    except FileNotFoundError:
        return {"session": None, "attempts": 0, "maybe_ours": False}
    except (ValueError, OSError) as exc:
        raise ControlError(f"Schedule state unreadable ({path}): {exc}; refusing commands") from exc


def tick(client: OsmoClient, state: dict, *, now: dt.datetime, start: int,
         end: int, days: set[int], model: str, assume_infinite: bool,
         max_starts: int = 2, min_free_mb: int = 1024, dry_run: bool = False) -> str:
    """One idempotent scheduling decision. Caller persists state after each tick.

    Ownership is saved BEFORE START, including in the event the API loses its ACK.
    This matches the conservative embedded scheduler; never STOP unknown recordings.
    """
    if now.year < 2025:
        return "hold: system clock invalid"
    key = session_for(now, start, end, days)
    status = client.status()
    try:
        verify_status(status, expected_model=model)
    except ControlError as exc:
        return f"hold: {exc}"
    recording = record_state(status)
    if recording not in ("idle", "recording"):
        return f"hold: recording state {recording}"
    if key is not None:
        if state.get("session") != key:
            if state.get("maybe_ours") and recording == "recording":
                return "hold: previous session still recording; needs manual inspection"
            state.update(session=key, attempts=0, maybe_ours=False)
        if recording == "recording":
            return "hold: already recording"
        if int(state.get("attempts", 0)) >= max_starts:
            return "hold: retry budget used"
        try:
            verify_status(status, expected_model=model, must_be_infinite=True,
                          assume_infinite=assume_infinite)
        except ControlError as exc:
            return f"hold: {exc}"
        storage = status.get("storage") or {}
        if storage.get("free_mb") is None or storage["free_mb"] < min_free_mb:
            return "hold: free storage missing/insufficient"
        if dry_run:
            return "dry-run: would START"
        state["maybe_ours"] = True
        state["attempts"] = int(state.get("attempts", 0)) + 1
        return "START"
    if state.get("maybe_ours"):
        if recording == "recording":
            if dry_run:
                return "dry-run: would STOP"
            return "STOP"
        state["maybe_ours"] = False
        return "clear: owned recording already idle"
    return "hold: outside schedule"


def schedule_loop(args: argparse.Namespace, client: OsmoClient, *,
                  sleep=time.sleep, now_fn=None) -> None:
    if args.start == args.end:
        raise ControlError("--start and --end must differ")
    if now_fn is None:
        now_fn = lambda: dt.datetime.now(ZoneInfo(args.tz))
    state_path = Path(args.state_file).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(state_path.name + ".lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_fd)
        raise ControlError("Another daily scheduler already owns this state file") from exc
    # Keep lock_fd open for the process lifetime, so a second process cannot
    # issue duplicate commands. The OS releases this lock on exit or crash.
    state = load_state(state_path)
    last_message = None
    while True:
        now = now_fn()
        action = tick(client, state, now=now, start=args.start, end=args.end,
                      days=args.days, model=args.model, assume_infinite=args.assume_infinite,
                      max_starts=args.max_starts, min_free_mb=args.min_free_mb,
                      dry_run=args.dry_run)
        # Persist ownership BEFORE potentially irreversible START or STOP.
        if not args.dry_run:
            atomic_save(state_path, state)
        if action in ("START", "STOP"):
            try:
                reply = client.command(f"/api/record/{action.lower()}")
                LOG.warning("%s ACK=%s (waiting for camera status)", action, reply)
                target = "recording" if action == "START" else "idle"
                if wait_record_state(client, target, model=args.model):
                    LOG.warning("%s CONFIRMED by camera status", action)
                    if action == "STOP":
                        state["maybe_ours"] = False
                        atomic_save(state_path, state)
                else:
                    LOG.error("%s NOT CONFIRMED: do not assume success", action)
            except ControlError as exc:
                LOG.error("%s failed; state retained for cautious recovery: %s", action, exc)
        elif action != last_message:
            LOG.info("%s: %s", now.isoformat(timespec="seconds"), action)
        last_message = action
        sleep(args.poll)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Action 5 Pro control via local Osmo Client JSON API")
    parser.add_argument("action", choices=("status", "start", "stop", "set-timelapse", "probe-hours", "daily"))
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--model", default="Osmo Action 5 Pro")
    parser.add_argument("--start", type=hhmm, default=8 * 60)
    parser.add_argument("--end", type=hhmm, default=18 * 60)
    parser.add_argument("--days", type=parse_days, default=set(range(7)))
    parser.add_argument("--tz", default="Europe/Berlin")
    parser.add_argument("--poll", type=float, default=10.0)
    parser.add_argument("--max-starts", type=int, default=2)
    parser.add_argument("--min-free-mb", type=int, default=1024)
    parser.add_argument("--state-file", default=".osmo_pi_schedule_state.json")
    parser.add_argument("--assume-infinite", action="store_true",
                        help="Unsafe override if camera omits duration in status; check camera screen first")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--hours", type=float, default=8.0, help="probe 5.01–24h; requires patched Osmo Client")
    args = parser.parse_args(argv)
    if args.poll < 1 or args.max_starts < 1 or args.min_free_mb < 0:
        parser.error("poll and max-starts must be positive; min-free-mb >= 0")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    api = OsmoClient(args.port)
    try:
        if args.action == "status":
            print(json.dumps(api.status(), indent=2, ensure_ascii=False))
        elif args.action == "daily":
            schedule_loop(args, api)
        elif args.action == "probe-hours":
            seconds = round(args.hours * 3600)
            if not 5 * 3600 < seconds <= 24 * 3600:
                parser.error("--hours must be strictly greater than 5 and at most 24")
            state = api.status()
            verify_status(state, expected_model=args.model)
            if record_state(state) != "idle":
                raise ControlError("Probe requires camera idle; do not modify an ongoing recording")
            if args.dry_run:
                print(f"Would probe {seconds} seconds; no command sent")
            else:
                result = api.command("/api/lapse/probe", {"duration": seconds})
                print(json.dumps(result, indent=2))
                if not result.get("verified"):
                    raise ControlError("Probe ACK did NOT yield matching camera readback; "
                                       "unsupported or inconclusive (restore a standard setting)")
        elif args.action == "set-timelapse":
            state = api.status()
            verify_status(state, expected_model=args.model, require_timelapse=False)
            if record_state(state) != "idle":
                raise ControlError("Cannot change mode while recording")
            if args.dry_run:
                print("Would select native Timelapse; no command sent")
            else:
                print(json.dumps(api.command("/api/mode/2"), indent=2))
        else:
            state = api.status()
            verify_status(state, expected_model=args.model,
                          must_be_infinite=args.action == "start",
                          assume_infinite=args.assume_infinite)
            current = record_state(state)
            expected = "idle" if args.action == "start" else "recording"
            if current != expected:
                raise ControlError(f"Refusing {args.action}: camera is {current!r}, expected {expected!r}")
            if args.dry_run:
                print(f"Would {args.action}; no command sent")
            else:
                print(json.dumps(api.command(f"/api/record/{args.action}"), indent=2))
                if not wait_record_state(api, "recording" if args.action == "start" else "idle",
                                         model=args.model):
                    raise ControlError("ACK received but camera state was NOT confirmed")
                print("Camera state CONFIRMED (clip integrity still requires physical check)")
        return 0
    except (ControlError, KeyboardInterrupt) as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
