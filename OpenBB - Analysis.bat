@echo off

:: 启动 OpenBB MCP Server
start "OpenBB MCP" cmd /k "python -m openbb_mcp_server.app.app --port 8002"

:: 启动前端（先进入 frontend 目录）
start "Frontend" cmd /k "cd /d desktop && npm run dev"

:: 启动后端（进入 Django 项目）
start "Backend" cmd /k "cd /d market_analysis_api && python manage.py runserver 8003"

pause
