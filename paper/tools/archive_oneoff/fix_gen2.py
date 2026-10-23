from pathlib import Path
BS = chr(92)
root = Path(__file__).resolve().parents[2]
p = root / "paper" / "tools" / "make_paper_assets.py"
s = p.read_text(encoding="utf-8")
a = 'piv.to_csv(G / "wear_chi.dat", sep=" ", index=False)'
assert a in s
s = s.replace(a, 'piv = piv[piv.chi > 0]  # chi = 0 cannot be drawn on a log axis (all methods equal 0.846 there)\n' + a)
# library-size table: show requested (actual)
a = 'lines.append(f"{int(g.K_actual.iloc[0])} & {f(g.val_coverage.iloc[0] * 100, 1)}'
assert a in s
s = s.replace(a, 'kreq, kact = int(K), int(g.K_actual.iloc[0])\n    klab = str(kact) if kreq == kact else f"{kreq} ({kact})"\n    lines.append(f"{klab} & {f(g.val_coverage.iloc[0] * 100, 1)}')
# drift table header shorter
s = s.replace("False alarms/1k (no shift)", "False alarms/1k")
p.write_text(s, encoding="utf-8")
m = root / "paper" / "main_v2.tex"
t = m.read_text(encoding="utf-8")
t = t.replace(",restrict x to domain=0.0005:1", "")
t = t.replace(BS + "caption{Injected Traffic Shifts: Post-Shift Cost $J$ of Static and Drift-Triggered LiRA}",
              BS + "caption{Injected Traffic Shifts: Post-Shift Cost $J$ of Static and Drift-Triggered LiRA. False Alarms per 1000 Intervals Are Measured on the Stream Without a Shift}")
t = t.replace(BS + "caption{Ablation of LiRA on Nobel-Germany at the Default Price (Mean over Three Seeds)}" + "\n" + BS + "label{tab:ablation}\n" + BS + "footnotesize\n" + BS + "setlength{" + BS + "tabcolsep}{3pt}",
              BS + "caption{Ablation of LiRA on Nobel-Germany at the Default Price (Mean over Three Seeds)}" + "\n" + BS + "label{tab:ablation}\n" + BS + "scriptsize\n" + BS + "setlength{" + BS + "tabcolsep}{2pt}")
t = t.replace("Table~" + BS + "ref{tab:K} shows the effect of the library size on Nobel-Germany. The library saturates at " + BS + "KactualMax" + BS + " configurations.",
              "Table~" + BS + "ref{tab:K} shows the effect of the library size on Nobel-Germany. Requested sizes above " + BS + "KactualMax" + BS + " yield the same library, because the greedy pruning stops when no configuration lowers the energy further.")
m.write_text(t, encoding="utf-8")
print("ok")
