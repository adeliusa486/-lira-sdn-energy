"""Check that every prose paragraph in main.tex is one source line, and that every label is referenced.

Usage (from paper/): python tools/check_paragraphs.py
"""
import re

src = open("main.tex", encoding="utf-8").read()
body = src.split("\\begin{document}", 1)[1]
# blank out environments whose source is code, not prose
for env in ["tikzpicture", "tabular", "algorithmic", "equation", "axis"]:
    body = re.sub(r"\\begin\{%s\*?\}.*?\\end\{%s\*?\}" % (env, env), lambda m: "\n" * m.group(0).count("\n"), body, flags=re.S)
lines = body.split("\n")
broken = []
for i in range(len(lines) - 1):
    a, b = lines[i].strip(), lines[i + 1].strip()
    prose = lambda s: bool(s) and not s.startswith(("\\", "%", "}", "{", "&"))
    if prose(a) and prose(b):
        broken.append(i)
print("paragraphs split across lines:", len(broken))
for i in broken[:10]:
    print("  ->", lines[i][:90])

labels = set(re.findall(r"\\label\{([^}]+)\}", src))
refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", src))
print("labels never referenced:", sorted(labels - refs))
print("references to missing labels:", sorted(refs - labels))
print("unescaped %% in prose lines:", sum(1 for l in src.split("\n") if re.search(r"[0-9a-zA-Z ]%[^\n]", l) and not l.lstrip().startswith("%") and "\\%" not in l.split("%")[0][-1:]))
