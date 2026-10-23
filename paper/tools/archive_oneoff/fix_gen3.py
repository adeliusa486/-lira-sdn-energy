from pathlib import Path
root = Path(__file__).resolve().parents[2]
p = root / "paper" / "tools" / "make_paper_assets.py"
s = p.read_text(encoding="utf-8")
add = '''
# ---- how often the trained LiRA policy degenerates to a constant classifier
import glob
_tot = _const = 0
for _f in glob.glob(str(R / "E1_main" / "*_info.json")):
    _runs = json.loads(Path(_f).read_text())["runs"]
    _tot += len(_runs)
    _const += sum(r["lira_model"] == "ConstantModel" for r in _runs)
macros["liraConstRuns"] = str(_const)
macros["liraTotalRuns"] = str(_tot)
'''
marker = 'write("results_macros.tex"'
assert marker in s and "liraConstRuns" not in s
s = s.replace(marker, add + "\n" + marker, 1)
p.write_text(s, encoding="utf-8")
