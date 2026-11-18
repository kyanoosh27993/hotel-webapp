@echo off
REM ارسال سورس به گیت‌هاب — https://github.com/kyanoosh27993/hotel-webapp
REM استفاده:  push-to-github.bat <TOKEN>
REM TOKEN = یک Personal Access Token از GitHub (Settings - Developer settings - Tokens)
REM باید دسترسی repo (Contents: Read and write) داشته باشد.
if "%~1"=="" (
  echo Usage: push-to-github.bat ^<GITHUB_TOKEN^>
  pause
  exit /b 1
)
git init
git add -A
git -c user.name="Arian Kavir Rafsanjan" -c user.email="kyanoosh27993@users.noreply.github.com" commit -m "v0.7.0 - Payroll System full source"
git branch -M main
git remote remove hotel 2>nul
git remote add hotel https://kyanoosh27993:%1@github.com/kyanoosh27993/hotel-webapp.git
git push -u hotel main --force
echo Done - source pushed to github.com/kyanoosh27993/hotel-webapp
pause
