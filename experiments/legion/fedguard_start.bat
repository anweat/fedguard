@echo off
title fedguard - auto experiments running (use fedguard_stop.bat to stop)
rem Starts or resumes the automatic experiment loop (10 hour budget per start).
rem Finished jobs are skipped; an interrupted training run continues from its last finished round.
wsl -d Ubuntu --cd /root/innovation -- bash -lc "envs/fl311/.venv/bin/python experiments/auto/loop.py --budget-hours 10"
echo.
echo Loop stopped or finished. Double-click fedguard_start.bat to continue.
pause
