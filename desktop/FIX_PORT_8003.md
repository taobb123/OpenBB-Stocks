# 快速修复：前端端口配置

## ✅ 已更新默认端口为 8003

默认配置已更新，但如果页面仍显示 8000，请按以下步骤操作：

## 🔧 方法 1：清除浏览器缓存（推荐）

1. **硬刷新页面**：
   - Windows: `Ctrl + Shift + R` 或 `Ctrl + F5`
   - Mac: `Cmd + Shift + R`

2. **清除 localStorage**：
   - 打开浏览器开发者工具（F12）
   - 在控制台运行：
   ```javascript
   localStorage.removeItem('api_base_url');
   location.reload();
   ```

## 🔧 方法 2：手动设置（如果方法1不行）

在浏览器控制台运行：
```javascript
localStorage.setItem('api_base_url', 'http://localhost:8003/api');
location.reload();
```

## 🔧 方法 3：使用环境变量（永久配置）

1. 在 `desktop` 目录创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://localhost:8003/api
```

2. 重启前端开发服务器：
```bash
npm run dev
```

## ✅ 验证

刷新页面后，应该显示：
- 服务器地址：`http://localhost:8003`
- API 状态：已连接（如果后端正在运行）

## 📝 注意

- 如果之前设置过 localStorage，需要清除或更新
- 环境变量的优先级最高
- 修改配置后需要刷新页面

