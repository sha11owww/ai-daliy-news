@echo off
title AI Daily Generator

set SESSION=%1
if "%SESSION%"=="" set SESSION=morning

cd /d "%~dp0"
echo Generating %SESSION% report...
python scripts/github_action_run.py --session %SESSION%

if errorlevel 1 (
    echo FAILED
) else (
    echo DONE
)
pause
