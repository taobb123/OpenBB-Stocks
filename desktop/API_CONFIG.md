# API 配置指南

## 📡 如何修改后端端口

如果 Django 后端运行在不同端口，前端需要相应配置。

## 方法 1：使用环境变量（推荐）

1. **创建 `.env` 文件**（在 `desktop` 目录下）：
```bash
# 复制示例文件
cp .env.example .env
```

2. **编辑 `.env` 文件**，设置你的端口：
```env
VITE_API_BASE_URL=http://localhost:8080/api
```

3. **重启前端开发服务器**：
```bash
npm run dev
```

## 方法 2：使用 localStorage（临时）

在浏览器控制台运行：
```javascript
localStorage.setItem('api_base_url', 'http://localhost:8080/api');
location.reload();
```

## 方法 3：修改配置文件

直接编辑 `desktop/src/config/api.ts` 中的默认值。

## 🔍 检查当前配置

前端会自动显示当前配置的 API 地址。如果连接失败，会在页面上显示当前配置的地址。

## 📝 示例

### 后端运行在 8000 端口（默认）
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 后端运行在 8003 端口
```env
VITE_API_BASE_URL=http://localhost:8003/api
```

### 后端运行在 8080 端口
```env
VITE_API_BASE_URL=http://localhost:8080/api
```

### 后端运行在其他机器
```env
VITE_API_BASE_URL=http://192.168.1.100:8000/api
```

## ⚠️ 注意事项

- 环境变量需要以 `VITE_` 开头才能在 Vite 中使用
- 修改 `.env` 后需要重启开发服务器
- 确保后端 CORS 配置允许前端域名访问

