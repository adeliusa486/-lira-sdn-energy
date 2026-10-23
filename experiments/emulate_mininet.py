#!/usr/bin/env python3
"""E11: Mininet / Open vSwitch emulation of configuration transitions (run inside WSL as root).

Replays one method's configuration sequence (exported by emu_export.py). One host per switch,
static OpenFlow 1.3 rules per (src,dst) installed with ovs-ofctl (no controller).
Transition procedure (make-before-break):
  1. wake links that the new configuration needs (ip link up) and wait WAKE_S (modeled wake-up delay),
  2. replace the flow table of every switch whose rules changed, one switch after another
     (non-atomic, like a controller pushing flow-mods),
  3. put links that are no longer used to sleep (ip link down).
UDP probes (100 pkt/s) run on the 8 largest OD pairs during the whole replay and give loss and
one-way delay (all hosts share one clock).
Usage: sudo python3 emulate_mininet.py INPUT.json METHOD OUTDIR [SECONDS_PER_INTERVAL] [WAKE_S]
"""
import json
import os
import struct
import subprocess
import sys
import time

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel

PROBE_HZ = 100
PORT = 5001


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


PROBE_SCRIPT = r'''
import socket, struct, sys, time
role, ip, port, hz, end, logf = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recs = []
if role == "tx":
    seq, nxt = 0, time.time()
    while time.time() < end:
        now = time.time()
        if now >= nxt:
            s.sendto(struct.pack("!Id", seq, now) + b"x" * 40, (ip, port))
            recs.append((seq, now)); seq += 1; nxt += 1.0 / hz
        else:
            time.sleep(min(0.002, nxt - now))
else:
    s.bind(("", port)); s.settimeout(0.5)
    while time.time() < end + 3:
        try:
            d, _ = s.recvfrom(2048)
        except socket.timeout:
            continue
        seq, tx = struct.unpack("!Id", d[:12]); recs.append((seq, tx, time.time()))
with open(logf, "wb") as f:
    for r in recs:
        f.write(struct.pack("!" + "Id" if role == "tx" else "!Idd", *r))
'''


def main():
    inp, method, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    spi = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    wake_s = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    cfg = json.load(open(inp))
    os.makedirs(outdir, exist_ok=True)
    seq = cfg["methods"][method]
    if int(os.environ.get("EMU_LIM", 0)):
        seq = seq[:int(os.environ["EMU_LIM"])]
    N = len(cfg["nodes"])
    sh("mn -c >/dev/null 2>&1; service openvswitch-switch start >/dev/null 2>&1")
    setLogLevel("warning")
    net = Mininet(controller=None, switch=lambda n, **k: OVSSwitch(n, protocols="OpenFlow13",
                                                                   failMode="secure", **k),
                  autoSetMacs=True, waitConnected=False)
    sws = [net.addSwitch(f"s{i}") for i in range(N)]
    hosts = [net.addHost(f"h{i}", ip=f"10.0.0.{i + 1}/24") for i in range(N)]
    for i in range(N):
        net.addLink(hosts[i], sws[i])
    links = []
    for (u, v) in cfg["links"]:
        links.append(net.addLink(sws[u], sws[v]))
    net.start()
    for h in hosts:
        for j, g in enumerate(hosts):
            if g is not h:
                h.setARP(f"10.0.0.{j + 1}", g.MAC())
    # port numbers
    hostport = []
    for i in range(N):
        hl = net.linksBetween(hosts[i], sws[i])[0]
        hostport.append(sws[i].ports[hl.intf1 if hl.intf1.node == sws[i] else hl.intf2])
    lport = {}
    for k, (u, v) in enumerate(cfg["links"]):
        l = links[k]
        lport[(u, v)] = sws[u].ports[l.intf1 if l.intf1.node == sws[u] else l.intf2]
        lport[(v, u)] = sws[v].ports[l.intf1 if l.intf1.node == sws[v] else l.intf2]
    lintf = {}
    for k, (u, v) in enumerate(cfg["links"]):
        lintf[k] = (links[k].intf1.name, links[k].intf2.name)

    def rules_for(c):
        """{switch: [flow strings]} for configuration c (single dominant path per OD)."""
        out = {i: [] for i in range(N)}
        for o, path in cfg["paths"][str(c)].items():
            s_, d_ = cfg["od"][int(o)]
            for a, b in zip(path[:-1], path[1:]):
                out[a].append(f"priority=100,ip,nw_src=10.0.0.{s_ + 1},nw_dst=10.0.0.{d_ + 1},actions=output:{lport[(a, b)]}")
            out[path[-1]].append(f"priority=100,ip,nw_src=10.0.0.{s_ + 1},nw_dst=10.0.0.{d_ + 1},actions=output:{hostport[path[-1]]}")
        return out

    cache = {c: rules_for(c) for c in set(seq)}

    def install(sw_idx, flows):
        fn = f"/tmp/flows_{os.getpid()}_{sw_idx}.txt"
        open(fn, "w").write("\n".join(flows) + "\n")
        r = sh(f"ovs-ofctl -O OpenFlow13 replace-flows s{sw_idx} {fn}")
        return r.returncode

    def link_state(k, up):
        for nm, sw in zip(lintf[k], (cfg["links"][k][0], cfg["links"][k][1])):
            sh(f"ip link set dev {nm} {'up' if up else 'down'}")

    # initial configuration
    cur = seq[0]
    on = cfg["config_links_on"][str(cur)]
    for k, st in enumerate(on):
        link_state(k, bool(st))
    for i in range(N):
        install(i, cache[cur][i])
    time.sleep(1.0)
    # probes
    total = len(seq) * spi
    t0 = time.time() + 2.0
    end = t0 + total
    open("/tmp/probe_emul.py", "w").write(PROBE_SCRIPT)
    procs, logs = [], []
    for j, o in enumerate(cfg["probe_od"]):
        s_, d_ = cfg["od"][o]
        rxlog, txlog = f"{outdir}/{method}_rx{j}.bin", f"{outdir}/{method}_tx{j}.bin"
        procs.append(hosts[d_].popen(f"python3 /tmp/probe_emul.py rx 10.0.0.{d_ + 1} {PORT + j} {PROBE_HZ} {end} {rxlog}", shell=True))
        logs.append((o, s_, d_, txlog, rxlog))
    time.sleep(1.0)
    for j, (o, s_, d_, txlog, rxlog) in enumerate(logs):
        procs.append(hosts[s_].popen(f"python3 /tmp/probe_emul.py tx 10.0.0.{d_ + 1} {PORT + j} {PROBE_HZ} {end} {txlog}", shell=True))
    while time.time() < t0:
        time.sleep(0.01)
    events = []
    for t, c in enumerate(seq):
        tgt = t0 + t * spi
        while time.time() < tgt:
            time.sleep(0.005)
        if c != cur:
            ev = {"interval": t, "from": cur, "to": c, "t_start": time.time()}
            old_on, new_on = cfg["config_links_on"][str(cur)], cfg["config_links_on"][str(c)]
            wake = [k for k in range(len(new_on)) if new_on[k] and not old_on[k]]
            sleep_ = [k for k in range(len(new_on)) if old_on[k] and not new_on[k]]
            for k in wake:
                link_state(k, True)
            if wake:
                time.sleep(wake_s)                      # modeled wake-up delay
            ev["t_rules_start"] = time.time()
            changed = [i for i in range(N) if sorted(cache[c][i]) != sorted(cache[cur][i])]
            for i in changed:
                install(i, cache[c][i])
            ev["t_rules_end"] = time.time()
            for k in sleep_:
                link_state(k, False)
            ev.update({"t_end": time.time(), "links_woken": len(wake), "links_slept": len(sleep_),
                       "switches_updated": len(changed),
                       "rule_install_ms": 1000 * (ev["t_rules_end"] - ev["t_rules_start"])})
            events.append(ev)
            cur = c
    while time.time() < end + 3.5:
        time.sleep(0.05)
    for p in procs:
        p.wait()
    meta = {"method": method, "spi": spi, "wake_s": wake_s, "t0": t0, "end": end, "events": events,
            "probes": [{"od": o, "src": s_, "dst": d_, "tx": txlog, "rx": rxlog} for o, s_, d_, txlog, rxlog in logs],
            "probe_hz": PROBE_HZ, "intervals": len(seq),
            "link_on_seconds": sum(sum(cfg["config_links_on"][str(c)]) * spi for c in seq)}
    json.dump(meta, open(f"{outdir}/{method}_meta.json", "w"))
    net.stop()
    sh("mn -c >/dev/null 2>&1")


if __name__ == "__main__":
    main()
