@echo off
chcp 65001 >nul
echo ========================================
echo    Git 推送一键修复脚本
echo ========================================
echo.

cd /d "C:\Users\王翌哲\Desktop\农大玄鉴"

echo [1/6] 设置 Git 身份...
git config --global user.email "你的邮箱@example.com"
git config --global user.name "TheFool0521"

echo.
echo [2/6] 移除旧远程连接...
git remote remove origin

echo.
echo [3/6] 添加正确的远程仓库...
git remote add origin https://github.com/TheFool0521/xuanjian

echo.
echo [4/6] 添加所有文件...
git add .

echo.
echo [5/6] 提交代码...
git commit -m "first deploy"

echo.
echo [6/6] 推送代码...
git push -u origin master --force

echo.
echo ========================================
echo    执行完毕！按任意键关闭窗口
echo ========================================
pause >nul