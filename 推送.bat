@echo off
cd /d "C:\Users\王翌哲\Desktop\农大玄鉴"

echo === Xuanjian Deploy ===

git config user.email "wyz2795206085@outlook.com"
git config user.name "TheFool0521"

git remote remove origin 2>nul
git remote add origin https://github.com/TheFool0521/xuanjian

git add .
git commit -m "deploy %date%"

git push -u origin main --force

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS - Vercel will auto-deploy
) else (
    echo FAILED - check network/VPN
)

pause
