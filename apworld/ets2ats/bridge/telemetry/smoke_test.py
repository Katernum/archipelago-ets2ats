"""
Milestone 2 smoke test: open the SCSTelemetry shared memory (already populated by the
already-installed ETSSharedMemoryMapPlugin64v2.dll) and log gameplay events live -- Job
Delivered/Cancelled, Fined, Tollgate, Ferry, Train, Refuel -- as they happen in-game.

The shared memory is a plain snapshot of current state, not an event queue, so events are
detected by edge-triggering: `special_b.jobDelivered` (etc.) is true only for the instant
the event fires, so we poll and compare against the previous poll's flags.

Usage: py smoke_test.py   (run this while ETS2/ATS is running; deliver/cancel a job, get
fined, cross a toll/ferry/train, or refuel to see events logged)
"""

import ctypes
import time

from shared_memory_map import ScsTelemetryMap, MMF_NAME, MMF_SIZE
from win_mmf import ExistingFileMapping

POLL_HZ = 10


def _cstr(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def read_snapshot(mapping: ExistingFileMapping) -> ScsTelemetryMap:
    buf = mapping.read()[:ctypes.sizeof(ScsTelemetryMap)]
    return ScsTelemetryMap.from_buffer_copy(buf)


def describe_event(name: str, snap: ScsTelemetryMap) -> str:
    g_ui, g_i, g_f, g_ll, g_s = (
        snap.gameplay_ui, snap.gameplay_i, snap.gameplay_f, snap.gameplay_ll, snap.gameplay_s,
    )
    cfg_s = snap.config_s

    if name == "jobDelivered":
        return (
            f"revenue={g_ll.jobDeliveredRevenue} xp={g_i.jobDeliveredEarnedXp} "
            f"distanceKm={g_f.jobDeliveredDistanceKm:.1f} "
            f"cargoDamage={g_f.jobDeliveredCargoDamage:.3f} "
            f"cargo={_cstr(cfg_s.cargo)!r} "
            f"from={_cstr(cfg_s.citySrc)!r} to={_cstr(cfg_s.cityDst)!r}"
        )
    if name == "jobCancelled":
        return f"penalty={g_ll.jobCancelledPenalty}"
    if name == "fined":
        return f"amount={g_ll.fineAmount} offence={_cstr(g_s.fineOffence)!r}"
    if name == "tollgate":
        return f"amount={g_ll.tollgatePayAmount}"
    if name == "ferry":
        return (
            f"amount={g_ll.ferryPayAmount} "
            f"from={_cstr(g_s.ferrySourceName)!r} to={_cstr(g_s.ferryTargetName)!r}"
        )
    if name == "train":
        return (
            f"amount={g_ll.trainPayAmount} "
            f"from={_cstr(g_s.trainSourceName)!r} to={_cstr(g_s.trainTargetName)!r}"
        )
    if name == "refuel":
        return f"amount={snap.gameplay_f.refuelAmount:.1f}"
    if name == "refuelPayed":
        return f"amount={snap.gameplay_f.refuelAmount:.1f}"
    if name == "jobFinished":
        return f"jobFinishedTime={g_ui.jobFinishedTime}"
    if name == "onJob":
        return f"jobMarket={_cstr(cfg_s.jobMarket)!r} cargo={_cstr(cfg_s.cargo)!r}"
    return ""


def main() -> None:
    print(f"Opening existing shared memory {MMF_NAME!r} ({MMF_SIZE} bytes)...", flush=True)
    try:
        mm = ExistingFileMapping(MMF_NAME, MMF_SIZE)
    except OSError as exc:
        print(f"Could not open shared memory: {exc}", flush=True)
        print("Is the game running with ETSSharedMemoryMapPlugin64v2.dll in its plugins folder?",
              flush=True)
        return

    snap = read_snapshot(mm)
    if not snap.sdkActive:
        print("Shared memory opened, but sdkActive is False. Waiting up to 30s "
              "(telemetry may need a moment after launch)...", flush=True)
        for _ in range(30):
            time.sleep(1)
            snap = read_snapshot(mm)
            if snap.sdkActive:
                break
        else:
            print("Still not active after 30s.", flush=True)
            mm.close()
            return

    game_name = {0: "unknown", 1: "ETS2", 2: "ATS"}.get(snap.scs_values.game, "?")
    print(f"Connected. game={game_name} "
          f"version={snap.scs_values.version_major}.{snap.scs_values.version_minor} "
          f"telemetry_plugin_revision={snap.scs_values.telemetry_plugin_revision}", flush=True)
    print("Polling for events (Ctrl+C to stop)...\n", flush=True)

    event_names = [f[0] for f in type(snap.special_b)._fields_]
    prev = {name: False for name in event_names}

    try:
        while True:
            snap = read_snapshot(mm)
            special = snap.special_b
            for name in event_names:
                value = bool(getattr(special, name))
                if value and not prev[name]:
                    detail = describe_event(name, snap)
                    print(f"[{time.strftime('%H:%M:%S')}] EVENT {name}: {detail}", flush=True)
                prev[name] = value
            time.sleep(1.0 / POLL_HZ)
    except KeyboardInterrupt:
        pass
    finally:
        mm.close()


if __name__ == "__main__":
    main()
