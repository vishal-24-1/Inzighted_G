@echo off
REM Remove tracked inzighted-twa/android.keystore from git index (keeps file on disk)
cd /d "%~dp0.."
if exist "inzighted-twa\android.keystore" (
  git rm --cached "inzighted-twa\android.keystore"
  git add .gitignore
  echo "Please commit the change with: git commit -m \"Remove tracked android.keystore and ignore it\""
) else (
  echo "No inzighted-twa\android.keystore found in working folder."
)
pause
