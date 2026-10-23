"""Analyse the Mininet runs (E11): loss, delay, transition timing, emulated energy."""
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT  # noqa

D = OUT / "E11_emulation"
inp = json.loads((D / "input.json").read_text())
rows, ev_rows = [], []
WIN_PRE, WIN_POST = 0.2, 1.0          # seconds around a transition counted as "transition window"


def read(path, fmt):
    b = Path(path).read_bytes()
    n = struct.calcsize(fmt)
    return np.array([struct.unpack(fmt, b[i:i + n]) for i in range(0, len(b) - n + 1, n)])


for run in sorted((D / "runs").glob("*_rep*")):
    method = run.name.split("_rep")[0]
    if not (run / f"{method}_meta.json").exists():
        continue                                   # run still in progress
    meta = json.loads((run / f"{method}_meta.json").read_text())
    ev = meta["events"]
    lost_tot = sent_tot = 0
    lost_win = sent_win = 0
    delays, delays_win = [], []
    for p in meta["probes"]:
        tx = read(p["tx"].replace("paper/results/E11_emulation/runs/", str(D / "runs") + "/") if not Path(p["tx"]).exists() else p["tx"], "!Id")
        rx = read(p["rx"] if Path(p["rx"]).exists() else p["rx"].replace("paper/results/E11_emulation/runs/", str(D / "runs") + "/"), "!Idd")
        got = {int(s): (a, b) for s, a, b in rx}
        t0, end = meta["t0"], meta["end"]
        for seq, ts in tx:
            if ts < t0 or ts > end:
                continue                       # only the replay period
            in_win = any(e["t_start"] - WIN_PRE <= ts <= e["t_end"] + WIN_POST for e in ev)
            sent_tot += 1; sent_win += in_win
            if int(seq) in got:
                d = (got[int(seq)][1] - ts) * 1000
                delays.append(d)
                if in_win:
                    delays_win.append(d)
            else:
                lost_tot += 1; lost_win += in_win
    rows.append({"method": method, "rep": run.name.split("_rep")[1], "intervals": meta["intervals"],
                 "seconds_per_interval": meta["spi"], "wake_delay_s": meta["wake_s"],
                 "transitions": len(ev),
                 "links_toggled": sum(e["links_woken"] + e["links_slept"] for e in ev),
                 "probe_pkts": sent_tot, "lost_pkts": lost_tot, "loss_pct": 100 * lost_tot / max(sent_tot, 1),
                 "pkts_in_transition_windows": sent_win, "lost_in_transition_windows": lost_win,
                 "loss_pct_in_windows": 100 * lost_win / max(sent_win, 1),
                 "lost_outside_windows": lost_tot - lost_win,
                 "delay_ms_p50": float(np.percentile(delays, 50)) if delays else np.nan,
                 "delay_ms_p99": float(np.percentile(delays, 99)) if delays else np.nan,
                 "delay_ms_p99_in_windows": float(np.percentile(delays_win, 99)) if delays_win else np.nan,
                 "rule_install_ms_mean": float(np.mean([e["rule_install_ms"] for e in ev])) if ev else np.nan,
                 "transition_total_s_mean": float(np.mean([e["t_end"] - e["t_start"] for e in ev])) if ev else np.nan,
                 "link_on_seconds": meta["link_on_seconds"]})
    for e in ev:
        ev_rows.append({"method": method, "rep": run.name.split("_rep")[1], **{k: e[k] for k in (
            "interval", "from", "to", "links_woken", "links_slept", "switches_updated", "rule_install_ms")},
            "total_s": e["t_end"] - e["t_start"]})
df = pd.DataFrame(rows)
df.to_csv(D / "emulation_summary.csv", index=False)
pd.DataFrame(ev_rows).to_csv(D / "emulation_transitions.csv", index=False)
print(df.round(3).to_string())
