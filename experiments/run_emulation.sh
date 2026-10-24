#!/bin/bash
# Run inside WSL as root:  bash experiments/run_emulation.sh
cd "/mnt/e/Work/SDN energy aware 1"
IN=results/E11_emulation/input.json
for run in "B4 1" "LiRA 1" "B0 1" "B4 2" "B4 3"; do
  set -- $run
  python3 experiments/emulate_mininet.py $IN $1 results/E11_emulation/runs/$1_rep$2 2.0 1.0 > results/E11_emulation/runs_$1_rep$2.log 2>&1
  echo "done $1 rep$2 $(date +%H:%M)"
done
