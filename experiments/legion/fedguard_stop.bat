@echo off
title fedguard - stopping
rem Graceful stop: the current training round finishes (about 2 minutes), then the loop exits.
wsl -d Ubuntu --cd /root/innovation -- bash -lc "mkdir -p runs/auto; touch runs/auto/STOP; echo Stop requested. Waiting for the current round to finish...; for i in $(seq 1 60); do pgrep -f auto/loop.py > /dev/null || break; sleep 5; done; if pgrep -f auto/loop.py > /dev/null; then echo Still running. It will stop after the current round or safety evaluation. Check again with fedguard_progress.bat; else echo Stopped. Double-click fedguard_start.bat to continue.; fi"
echo.
pause
