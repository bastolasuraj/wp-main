@echo off
setlocal

set ROOT=%~dp0..
pushd "%ROOT%"

if not exist "automation\logs" mkdir "automation\logs"
python automation\cybersecurity_autopost.py --post-status publish --codex-timeout-seconds 900
set EXIT_CODE=%ERRORLEVEL%

popd
exit /b %EXIT_CODE%
