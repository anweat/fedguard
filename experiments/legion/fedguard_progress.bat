@echo off
title fedguard - progress
wsl -d Ubuntu --cd /root/innovation -- bash -lc "for r in runs/auto runs/auto_smoke; do [ -f $r/report.md ] && { echo ===== $r; cat $r/report.md; echo; echo ----- last decisions; tail -5 $r/decisions.jsonl; }; done; nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader"
echo.
pause
