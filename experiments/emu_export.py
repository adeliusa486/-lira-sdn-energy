"""Export the inputs of the Mininet emulation (E11): topology, per-method decision sequences
for the busiest B4 day of Nobel-Germany (base scenario), and the dominant path of every OD
pair in each library configuration that is used."""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa

topo_name, sc = "nobel", "base"
ctx = build_ctx(topo_name, 32)
z = np.load(OUT / "E1_main" / f"{topo_name}_{sc}_seqs.npz")
a, b = ctx.rng_idx("test")
b4 = z["B4_s0"]
ch = np.concatenate([[0], (b4[1:] != b4[:-1]).astype(int)])
n = ctx.per_day
days = [(int(ch[i:i + n].sum()), i) for i in range(0, len(b4) - n + 1, n)]
changes, d0 = max(days)
sl = slice(d0, d0 + n)
methods = {m: z[f"{m}_s0"][sl].tolist() for m in ("B4", "B6", "LiRA", "O*", "B0")}
used = sorted({c for s in methods.values() for c in s})
topo = ctx.topo
paths = {}
for c in used:
    split = ctx.library[c].split
    per_od = {}
    for o, (lo, hi) in enumerate(topo.od_slices):
        p = lo + int(np.argmax(split[lo:hi]))
        per_od[o] = [int(v) for v in topo.path_nodes[p]]
    paths[str(c)] = per_od
# probe pairs: the 8 largest ODs on the chosen day
dem = ctx.od[a + d0:a + d0 + n].mean(axis=0)
probe = [int(o) for o in np.argsort(dem)[::-1][:8]]
out = {"topology": topo_name, "scenario": sc, "day_start_interval": int(d0), "intervals": n,
       "b4_changes_in_day": changes, "nodes": topo.nodes,
       "links": [[int(u), int(v)] for u, v in topo.links],
       "od": topo.od.tolist(), "probe_od": probe,
       "config_links_on": {str(c): ctx.library[c].x.astype(int).tolist() for c in used},
       "paths": paths, "methods": methods}
Path(OUT / "E11_emulation" / "input.json").write_text(json.dumps(out))
print("busiest B4 day:", d0 // n, "changes", changes, "configs used", used)
for m, s in methods.items():
    s = np.array(s)
    print(m, "changes", int((s[1:] != s[:-1]).sum()))
