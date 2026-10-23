from pathlib import Path

root = Path(__file__).resolve().parents[2]
p = root / "paper" / "tools" / "make_paper_assets.py"
s = p.read_text(encoding="utf-8")
anchor = '    macros["emuHaveData"] = "1"'
assert anchor in s and "emuLostPerTrans" not in s
add = '''    macros["emuLostPerTrans"] = f(b4.lost_pkts.mean() / max(b4.transitions.mean(), 1), 1)
    b0 = e[e.method == "B0"]
    if len(b0) and len(li):
        macros["emuLinkSave"] = f(100 * (1 - li.link_on_seconds.mean() / b0.link_on_seconds.mean()), 0)
    macros["emuProbePkts"] = "{:,}".format(int(b4.probe_pkts.mean())).replace(",", "\\\\,")
'''
s = s.replace(anchor, add + anchor)
p.write_text(s, encoding="utf-8")

m = root / "paper" / "main_v2.tex"
t = m.read_text(encoding="utf-8")
bs = chr(92)
old = "Table~" + bs + "ref{tab:emu} reports the probe loss: in the windows around a transition, B4 loses " + bs + "emuLossWin" + bs + "% of the probe packets, and over the whole day " + bs + "emuLossAll" + bs + "%."
assert old in t
new = ("Table~" + bs + "ref{tab:emu} reports the probe loss. Each run sends " + bs + "emuProbePkts" + bs + " probe packets. B4 loses " + bs + "emuLostPerTrans"
       + bs + " packets per transition on average, all of them inside the windows around a transition: " + bs + "emuLossWin" + bs + "% of the probes in those windows and "
       + bs + "emuLossAll" + bs + "% over the whole day. The always-on control and LiRA lose no probe packets, and LiRA keeps the same emulated link-hours as B4, which are "
       + bs + "emuLinkSave" + bs + "% fewer than the always-on network.")
t = t.replace(old, new)
old2 = "and a Mininet emulation of " + bs + "emuTrans" + bs + " transitions measures the cost of each change."
assert old2 in t
t = t.replace(old2, "and a Mininet emulation of " + bs + "emuTrans" + bs + " transitions shows that each change takes about " + bs + "emuTransS" + bs + "\\,s and loses a few probe packets.")
m.write_text(t, encoding="utf-8")
print("ok")
