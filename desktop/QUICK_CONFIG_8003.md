# 快速配置：后端在 8003 端口

## 🚀 快速设置

### 方法 1：使用环境变量（推荐，永久生效）

1. **在 `desktop` 目录创建 `.env` 文件**：
```env
VITE_API_BASE_URL=http://localhost:8003/api
```

2. **重启前端开发服务器**：
```bash
npm run dev
```

### 方法 2：使用浏览器控制台（临时，刷新后失效）

1. 打开浏览器开发者工具（F12）
2. 在控制台运行：
```javascript
localStorage.setItem('api_base_url', 'http://localhost:8003/api');
location.reload();
```

## ✅ 验证配置

配置成功后，前端页面会显示：
- API 状态：已连接
- 服务器地址：`http://localhost:8003`

## 📝 注意事项

- 方法 1（环境变量）需要重启开发服务器
- 方法 2（localStorage）立即生效，但刷新页面后需要重新设置
- 确保 Django 后端正在 8003 端口运行

## 🔧 启动后端（8003 端口）

```bash
cd market_analysis_api
.\venv\Scripts\activate
python manage.py runserver 8003
```

