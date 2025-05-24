#!/usr/bin/env python3
# 2025-05-23  Resistance-test via FastAPI VXI-11 gateway
#
# --- What it does ---
#   • Talks to the DAQ6510 through the FastAPI gateway, *not* vxi11.
#   • Measures 2-wire resistance on one or more 7701 / 7710 channels.
#   • Prints the raw resistance value(s) every few seconds.
#
#   All SCPI commands remain exactly:
#     *RST
#     SENS:FUNC 'RES',(@ch)
#     SENS:RES:RANG 100000,(@ch)
#     SENS:RES:NPLC 1,(@ch)
#     ROUT:SCAN (@ch)
#     INIT
#     *WAI
#     FETC?
#   (Shortest mnemonics, no SYST:LOC.)

from __future__ import annotations
import time, requests, sys, traceback
from datetime import datetime
from typing import List

# ──────────────── user settings ────────────────
GATEWAY           = "http://192.168.1.13:8000"   # FastAPI base-URL
GATEWAY_TIMEOUT   = 5.0                       # s per batch
MEAS_INTERVAL_SEC = 5                         # pause between reads
CHANNELS          = ["101"]                   # change / add more if you like
# ───────────────────────────────────────────────

def send_batch(cmds: List[dict]) -> List[str]:
    """Helper: POST /send_commands and return list of responses."""
    r = requests.post(
        f"{GATEWAY.rstrip('/')}/send_commands",
        json={"commands": cmds, "timeout": GATEWAY_TIMEOUT},
        timeout=GATEWAY_TIMEOUT + 2,
    )
    r.raise_for_status()
    payload = r.json()
    if payload["status"] != "ok":
        raise RuntimeError(f"Gateway error: {payload.get('message')}")
    return [(ent.get("response") or "") for ent in payload["results"]]

def measure_resistance(ch: str) -> float:
    ch = str(ch)
    cmds = [
        {"cmd": "*RST",                          "query": False},
        {"cmd": f"SENS:FUNC 'RES',(@{ch})",      "query": False},
        {"cmd": f"SENS:RES:RANG 100000,(@{ch})", "query": False},
        {"cmd": f"SENS:RES:NPLC 1,(@{ch})",      "query": False},
        {"cmd": f"ROUT:SCAN (@{ch})",            "query": False},
        {"cmd": "INIT",                          "query": False},
        {"cmd": "*WAI",                          "query": False},
        {"cmd": "TRAC:DATA? 1,1",                "query": True},   # unchanged original
    ]
    *_, data = send_batch(cmds)
    return float(data.strip())


# ───────────────────────── main loop ─────────────────────────
idn = send_batch([{"cmd": "*IDN?", "query": True}])[0].strip()
print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Connected via gateway – *IDN? → {idn}")

print("\nStarting resistance test…  (Ctrl-C to stop)")
try:
    while True:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}]", end="")
        for ch in CHANNELS:
            try:
                R = measure_resistance(ch)
                print(f"  CH{ch}: {R:,.2f} Ω", end="")
            except Exception as e:
                print(f"  CH{ch}: ERROR ({e})", end="")
        print("")        # newline
        time.sleep(MEAS_INTERVAL_SEC)

except KeyboardInterrupt:
    print("\nUser stopped.")

except Exception:
    msg = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ⚠️  Unhandled error"
    print(msg, file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
