# One-off patch scripts (archived 2026-10-23)

These scripts edited `paper/main_v2.tex` and `paper/tools/make_paper_assets.py` once during the
2026-10-19 rewrite. Their asserts no longer match the current files, so they cannot run again.
They never touched result numbers. `fix_gen4.py` introduced the `\emuTransS\,s` typo in the
abstract, fixed in `main.tex` on 2026-10-23. `build_check.py` compiled a draft with zero-valued
stand-ins for macros that did not exist yet, and is not used for the real paper.
`main_v2_duplicate_of_main.tex` was a byte-identical copy of `paper/main.tex`.
