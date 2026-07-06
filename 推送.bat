@echo off
chcp 65001 >nul
echo ========================================
echo    Git 推送最终脚本
echo ========================================
echo.

cd /d "C:\Users\王翌哲\Desktop\农大玄鉴"

echo [1/6] 设置 Git 身份...
git config --global user.email "wyz2795206085@outlook.com"
git config --global user.name "TheFool0521"

echo.
echo [2/6] 设置 Git 缓存大小（解决网络超时）...
git config --global http.postBuffer 524288000

echo.
echo [3/6] 移除旧远程连接（如果有）...
git remote remove origin 2>nul

echo.
echo [4/6] 添加正确的远程仓库...
git remote add origin https://github.com/TheFool0521/xuanjian

echo.
echo [5/6] 添加所有文件并提交...
git add .
git commit -m "first deploy"

echo.
echo [6/6] 推送到远程仓库（使用 main 分支）...
git push -u origin main --force

echo.
echo ========================================
echo    执行完毕！按任意键关闭窗口
echo ========================================
pause >nul