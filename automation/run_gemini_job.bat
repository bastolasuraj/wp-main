@echo off
setlocal

set ROOT=%~dp0..
pushd "%ROOT%"

if not exist "automation\logs" mkdir "automation\logs"

:: Ensure GEMINI_API_KEY is set in your system environment variables
:: OR uncomment the line below and paste it (not recommended for shared computers)
:: set GEMINI_API_KEY=AIzaSy...

python automation\gemini_autopost.py --post-status publish --model gemini-2.0-flash --min-sources 8
set EXIT_CODE=%ERRORLEVEL%

popd
exit /b %EXIT_CODE%