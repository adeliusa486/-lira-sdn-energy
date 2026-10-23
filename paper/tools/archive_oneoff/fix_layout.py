from pathlib import Path
p = Path(__file__).resolve().parents[1] / "main_v2.tex"
s = p.read_text(encoding="utf-8")
BS = chr(92)

def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b)

# eq (fallback)
rep(BS + "begin{equation}" + BS + "label{eq:fallback}\nc_t=" + BS + "mathop{" + BS + "arg" + BS + "min}_{c" + BS + "in" + BS + "mathcal{C}:" + BS + ",",
    BS + "begin{equation}" + BS + "label{eq:fallback}\nc_t=" + BS + "mathop{" + BS + "arg" + BS + "min}_{c" + BS + "in" + BS + "mathcal{C}:" + BS + ",")
i = s.index(BS + "begin{equation}" + BS + "label{eq:fallback}")
j = s.index(BS + "end{equation}", i)
s = s[:i] + (BS + "begin{equation}" + BS + "label{eq:fallback}\n"
             + BS + "begin{split}c_t=" + BS + "mathop{" + BS + "arg" + BS + "min}_{c" + BS + "in" + BS + "mathcal{C}:" + BS + ",\mathrm{MLU}(c,"
             + BS + "hat D_t)" + BS + "le" + BS + "theta}" + BS + "Big[&E(c," + BS + "hat D_t)+" + BS + "lambda_R R(c_{t-1},c)" + BS + BS + "\n"
             + "&+" + BS + "lambda_W W(c_{t-1},c)" + BS + "Big],"
             + BS + "end{split}\n") + s[j:]
# eq (proxy)
i = s.index(BS + "begin{equation}" + BS + "label{eq:proxy}")
j = s.index(BS + "end{equation}", i)
s = s[:i] + (BS + "begin{equation}" + BS + "label{eq:proxy}\n"
             + BS + "begin{split}" + BS + "rho_t=&E(c_t,D_t)-" + BS + "min_{c" + BS + "in" + BS + "mathcal{C}:" + BS + ",\mathrm{MLU}(c,D_t)" + BS + "le" + BS + "theta}E(c,D_t)" + BS + BS + "\n"
             + "&+" + BS + "mathbb{1}[" + BS + "mathrm{MLU}(c_t,D_t)>" + BS + "theta],"
             + BS + "end{split}\n") + s[j:]
s = s.replace(BS + "mathrm{MLU}(c," + BS + "hat D_t)", BS + "mathrm{MLU}(c," + BS + "hat D_t)")
# data table across both columns
rep(BS + "begin{table}[t]\n" + BS + "centering\n" + BS + "caption{Topologies and Traffic Data}", BS + "begin{table*}[t]\n" + BS + "centering\n" + BS + "caption{Topologies and Traffic Data}")
i = s.index(BS + "caption{Topologies and Traffic Data}")
j = s.index(BS + "end{table}", i)
s = s[:j] + BS + "end{table*}" + s[j + len(BS + "end{table}"):]
rep("B4 changes configuration " + BS + "caseBFourchg" + BS + " times during the week, B6 and LiRA together hold their configuration, and LiRA makes " + BS + "caseLiRAchg" + BS + " changes.",
    "B4 changes configuration " + BS + "caseBFourchg" + BS + " times during the week, whereas LiRA makes only " + BS + "caseLiRAchg" + BS + " changes.")
p.write_text(s, encoding="utf-8")
print("layout fixes applied")
