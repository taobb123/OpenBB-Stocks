# 市场分析系统 - REST API 方案设置指南

## 📋 概述

这是一个使用 Django + REST API + React 前端的市场分析系统，**完全稳定，不会再有 invoke undefined 错误**。

## 🚀 快速开始

### 第一步：设置 Django 后端

1. **进入后端目录**：
```bash
cd market_analysis_api
```

2. **创建虚拟环境（推荐）**：
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **安装依赖**：
```bash
pip install -r requirements.txt
```

4. **运行数据库迁移**：
```bash
python manage.py migrate
```

5. **启动服务器**：
```bash
# 默认端口 8000
python manage.py runserver 8000

# 或指定其他端口（例如 8003）
python manage.py runserver 8003
```

或者直接运行：
```bash
start_server.bat
```

服务器将在 `http://localhost:8000` 启动（或你指定的端口）。

**⚠️ 重要**：如果修改了端口，需要在前端配置相应的 API URL（见下方"端口配置"部分）。

### 第二步：启动前端

1. **进入前端目录**：
```bash
cd desktop
```

2. **安装依赖（如果还没安装）**：
```bash
npm install
```

3. **启动开发服务器**：
```bash
npm run dev
```

前端将在 `http://localhost:1470` 启动。

### 第三步：访问应用

在浏览器中访问：`http://localhost:1470/market-analysis-rest`

## 📡 API 端点

### 1. 提取股票代码
- **URL**: `POST http://localhost:8000/api/extract-stock-codes/`
- **Body**:
```json
{
  "content": "立讯精密（002475）、歌尔股份（002241）..."
}
```

### 2. 分析自定义股票列表（选项2）
- **URL**: `POST http://localhost:8000/api/analyze-custom-stocks/`
- **Body**:
```json
{
  "stock_codes": ["600519", "000001"],
  "market_type": "A股"
}
```

### 3. 运行完整市场分析（选项4）
- **URL**: `POST http://localhost:8000/api/run-full-analysis/`
- **Body**:
```json
{
  "index_query": "China",
  "market_type": "A股"
}
```

## ✅ 优势

1. **完全稳定**：不依赖 Tauri invoke，不会有 undefined 错误
2. **易于调试**：前后端分离，可以独立调试
3. **跨平台**：可以在任何支持 Python 和 Node.js 的环境运行
4. **易于扩展**：可以轻松添加新的 API 端点
5. **标准化**：使用 REST API 标准，易于集成

## 🔧 端口配置

### 如果后端运行在不同端口

如果 Django 后端运行在非 8000 端口，需要配置前端：

**方法 1：使用环境变量（推荐）**

1. 在 `desktop` 目录创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://localhost:8003/api
```

2. 重启前端开发服务器

**方法 2：使用浏览器控制台**

在浏览器控制台运行：
```javascript
localStorage.setItem('api_base_url', 'http://localhost:8003/api');
location.reload();
```

详细说明请查看：`desktop/API_CONFIG.md`

## 🔧 故障排除

### 问题1：无法连接到后端 API

**解决方案**：
- 确保 Django 服务器正在运行：`python manage.py runserver 8000`
- 检查端口 8000 是否被占用
- 检查防火墙设置

### 问题2：CORS 错误

**解决方案**：
- 确保 `django-cors-headers` 已安装
- 检查 `settings.py` 中的 CORS 配置

### 问题3：导入错误

**解决方案**：
- 确保 `interactive_analysis.py` 和 `extract_stock_codes.py` 在项目根目录
- 检查 Python 路径设置

## 📝 注意事项

- 开发环境允许所有 CORS 来源，生产环境需要限制
- 确保 MCP 服务器已启动（如果使用 MCP 功能）
- 首次运行可能需要下载依赖，请耐心等待

## 🎯 下一步

可以添加：
- 图表可视化（ECharts/Plotly）
- 数据缓存
- 用户认证
- 更多分析功能

