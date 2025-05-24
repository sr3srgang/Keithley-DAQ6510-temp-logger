#!/usr/bin/env python3
# 2025-02-19  created by Joonseok Hur
# 2025-05-23  gateway edition by ChatGPT-o3
#
# Reads thermistor temperatures through a Keithley DAQ6510 with
# a 7701/7710 multiplexer **via the FastAPI VXI-11 gateway** and
# uploads them to the yemonitor InfluxDB.

from __future__ import annotations
import time, math, sys, traceback, requests
from datetime import datetime
from pathlib import Path
from typing import List

# ───────────────────────── Gateway settings ──────────────────────────
GATEWAY      = "http://192.168.1.13:8000"     # ← FastAPI base-URL
GATEWAY_TO   = 5.0                         # seconds per command

# Helper: atomic POST to /send_commands
def send_batch(cmds: List[dict[str, str | bool]], timeout: float = GATEWAY_TO) -> List[str]:
    r = requests.post(
        f"{GATEWAY.rstrip('/')}/send_commands",
        json={"commands": cmds, "timeout": timeout},
        timeout=timeout + 2,
    )
    r.raise_for_status()
    payload = r.json()
    if payload["status"] != "ok":
        raise RuntimeError(f"Gateway error: {payload.get('message')}")
    return [(entry.get("response") or "") for entry in payload["results"]]

# ────────────────────────── User parameters ─────────────────────────
MEASUREMENT_INTERVAL = 5      # s between loops
TOTAL_MEASUREMENTS   = None   # None → run forever

ASSIGNMENTS = [
    # channel, description, connection, thermistor type & params
    {"channel":"101","name":"Laser-side HVAC air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
    {"channel":"102","name":"Exp-side top layer air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
    {"channel":"103","name":"Exp-side middle layer air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
    {"channel":"104","name":"Exp-side bottom layer air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
    {"channel":"105","name":"Cavity homodyne section air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
    {"channel":"106","name":"Exp-side HVAC air",
     "thermistor_connection":"7710 multiplexer",
     "thermistor_model":"44008RC",
     "thermistor_params":{"B":3775.6,"R0":29939,"T0":273.15+25}},
]

# ─────────────── InfluxDB (yemonitor) credentials ───────────────────
url    = "http://yemonitor.colorado.edu:8086"
token  = "yelabtoken"
org    = "yelab"
bucket = "sr3"

from influxdb_client import InfluxDBClient       # noqa: E402
from influxdb_client.client.write_api import SYNCHRONOUS  # noqa: E402

# ────────────────────── derived constants ───────────────────────────
NCH        = len(ASSIGNMENTS)
BUFFERSIZE = max(NCH, 10)                # DAQ buffer size
CHANNELS   = [a["channel"] for a in ASSIGNMENTS]
CHSSTR     = ",".join(CHANNELS)

# ─────────────────── helper: R → °C for 44008RC ─────────────────────
def R_to_T(resistance: float, *, B: float, R0: float, T0: float) -> float:
    """Steinhart–Hart (β-form) conversion, returns °C."""
    temp_K = 1 / ((1 / B) * math.log(resistance / R0) + 1 / T0)
    return temp_K - 273.15

# ─────────────────────── diagnose connection once ───────────────────
IDN = send_batch([{"cmd": "*IDN?", "query": True}])[0].strip()
print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Connected via gateway – *IDN? → {IDN}")
try:
    DAQ_SN = IDN.split(",")[2]
except Exception:
    DAQ_SN = "UNKNOWN"

# ───────────────────────── main measurement loop ────────────────────
iteration = 0
print("Starting thermistor measurements…")

while TOTAL_MEASUREMENTS is None or iteration < TOTAL_MEASUREMENTS:
    t0 = datetime.now()
    print(f"[{t0:%Y-%m-%d %H:%M:%S}] Iteration {iteration}:")

    try:
        # -------- build full command batch (same sequence as before) ----------
        cmds = [
            {"cmd": "*RST",                                   "query": False},
            {"cmd": "TRAC:CLE 'defbuffer1'",                  "query": False},
            {"cmd": f"TRAC:POIN {BUFFERSIZE},'defbuffer1'",   "query": False},
            {"cmd": "ROUT:SCAN:BUFF 'defbuffer1'",            "query": False},
            {"cmd": f"FUNC 'RES', (@{CHSSTR})",               "query": False},
            {"cmd": f"ROUT:SCAN (@{CHSSTR})",                 "query": False},
            {"cmd": "ROUT:SCAN:COUN 1",                       "query": False},
            {"cmd": "INIT",                                   "query": False},
            {"cmd": "*WAI",                                   "query": False},
            {"cmd": "TRAC:ACT?",                              "query": True},   # active points
            {"cmd": f"TRAC:DATA? 1,{NCH}",                    "query": True},   # readings
        ]

        resp = send_batch(cmds)
        Nact = int(float(resp[-2].strip()))
        measstr = resp[-1].strip()
        resistances = [float(s) for s in measstr.split(",")][:Nact]

        # -------- convert to temperatures & print ----------------------------
        temps_C = []
        for ich, a in enumerate(ASSIGNMENTS):
            R = resistances[ich]
            T = R_to_T(R, **a["thermistor_params"])
            temps_C.append(T)
            print(f"\t{a['channel']}  R={R:,.2f} Ω  →  {T:.3f} °C  ({a['name']})")

        # -------- upload to InfluxDB -----------------------------------------
        records = [
            {
                "measurement": "Keithley DAQ6510",
                "tags": {
                    "DAQ SN": DAQ_SN,
                    "channel": a["channel"],
                    "name": a["name"],
                    "thermistor connection": a["thermistor_connection"],
                    "thermistor model": a["thermistor_model"],
                },
                "fields": {"Temp[degC]": temps_C[i]},
            }
            for i, a in enumerate(ASSIGNMENTS)
        ]

        with InfluxDBClient(url=url, token=token, org=org) as client:
            with client.write_api(write_options=SYNCHRONOUS) as writer:
                writer.write(bucket=bucket, record=records)

    except Exception as ex:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] ⚠️  Error in measurement loop"
        print(msg, file=sys.stdout)
        print(msg, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)

    iteration += 1
    time.sleep(MEASUREMENT_INTERVAL)

print("Measurement complete.")
