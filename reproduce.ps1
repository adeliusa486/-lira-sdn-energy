# Rebuild every result and the manuscript's tables and plot data from the raw SNDlib downloads.
# Run from the project root in Windows PowerShell:  powershell -ExecutionPolicy Bypass -File reproduce.ps1
# Stages can be skipped with -From (data, library, labels, experiments, tables). Each experiment
# script skips outputs that already exist, so a stopped run can be restarted.
# Approximate wall time on an i9-13900H: data 10 min, libraries 4-6 h (ILP), experiments 6-8 h.
param([ValidateSet("data", "library", "labels", "experiments", "tables")][string]$From = "data")
$ErrorActionPreference = "Stop"
$stages = "data", "library", "labels", "experiments", "tables"
$start = [array]::IndexOf($stages, $From)
$topos = "abilene", "geant", "nobel"

function Run($cmd) { Write-Host ">> $cmd"; Invoke-Expression $cmd; if ($LASTEXITCODE) { throw "failed: $cmd" } }
function Scenario($load, $dyn, $theta) {
    $env:LIRA_LOAD = $load
    if ($dyn) { $env:LIRA_DYN = $dyn } else { Remove-Item Env:LIRA_DYN -ErrorAction SilentlyContinue }
    $env:LIRA_THETA = $theta
}
# (load, dynamic port power in W, theta): base, high load, high dynamic power, stress, theta sweep
$scenarios = @(@("1", "", "0.8"), @("1.6", "", "0.8"), @("1", "15", "0.8"), @("1.6", "15", "0.8"),
               @("1", "", "0.6"), @("1", "", "0.7"), @("1", "", "0.9"))

if ($start -le 0) {
    Run "python -m lira.data.download"                    # SNDlib files, SHA-256 in data/MANIFEST.json
    Run "python -m lira.data.preprocess abilene geant"     # Abilene first: Nobel uses its weekly profile
    Run "python -m lira.data.preprocess nobel"
    Run "python -m lira.data.features abilene geant nobel"
    Run "python -m pytest -q tests"
}
if ($start -le 1) {
    foreach ($s in $scenarios) {
        Scenario $s[0] $s[1] $s[2]
        foreach ($t in $topos) { Run "python -m lira.library.build_library $t" }
    }
}
if ($start -le 2) {
    foreach ($s in $scenarios[0..3]) {                     # labels and the DP-vs-MILP check (theta 0.8)
        Scenario $s[0] $s[1] $s[2]
        foreach ($t in $topos) { Run "python -m lira.oracle.make_labels $t --K 32" }
    }
}
Scenario "1" "" "0.8"
if ($start -le 3) {
    if ($start -gt 0) { Run "python -m lira.data.features abilene geant nobel" }   # feature matrices are not shipped
    Run "python experiments/run_main.py --exp E1 E2 E2b E6 E7"
    Run "python experiments/run_extra.py --exp E1b E5 E8 E10 E13 E14"
    Run "python experiments/run_milp.py"                   # E15 lower bound
    Run "python experiments/run_stale.py"                  # E16 one-interval-old traffic matrix
    Run "python experiments/run_static.py"                 # E17 static configuration + fallback
    Run "python experiments/run_variant.py --exp E18"     # E18 no wear price
    Run "python experiments/make_nobel_variants.py"       # E19 data
    Run "python -m lira.data.features nobel_ar05 nobel_ar09 nobel_s06"
    foreach ($v in "nobel_ar05","nobel_ar09","nobel_s06") { Run "python -m lira.library.build_library $v --K 32" }
    Run "python experiments/run_variant.py --exp E19 --topos nobel_ar05 nobel_ar09 nobel_s06"
    Write-Host "E11 (Mininet) runs in WSL as root:"
    Write-Host "  python experiments/emu_export.py; wsl -u root bash experiments/run_emulation.sh; python experiments/emu_analyze.py"
}
if ($start -le 4) {
    Run "python experiments/make_report.py"
    Run "python tools/make_paper_assets.py"                # macros, tables and plot data -> submission/generated
    if (Test-Path submission/manuscript.tex) {             # the manuscript is kept outside the repository
        Push-Location submission
        Run "latexmk -pdf -interaction=nonstopmode manuscript.tex"
        Pop-Location
    }
}
