@echo off
title fedguard - smoke test (about 40 min, keep this window open)
wsl -d Ubuntu --cd /root/innovation -- bash -lc "rm -rf runs/auto_smoke && envs/fl311/.venv/bin/python experiments/auto/loop.py --root runs/auto_smoke --smoke --budget-hours 1.5"
echo.
echo Smoke test finished or stopped.
pause
