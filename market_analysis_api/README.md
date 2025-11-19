# 市场分析 API 后端

Django REST API 后端，提供市场分析功能。

## 安装

1. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行数据库迁移：
```bash
python manage.py migrate
```

4. 启动开发服务器：
```bash
# 默认端口 8000
python manage.py runserver 8000

# 或指定其他端口
python manage.py runserver 8080
```

API 将在 `http://localhost:8000/api/` 可用（或你指定的端口）。

**注意**：如果修改了端口，需要在前端配置相应的 API URL（见 `desktop/API_CONFIG.md`）。

## API 端点

### 1. 提取股票代码
- **URL**: `/api/extract-stock-codes/`
- **方法**: POST
- **Body**:
```json
{
  "content": "立讯精密（002475）、歌尔股份（002241）..."
}
```

### 2. 分析自定义股票列表（选项2）
- **URL**: `/api/analyze-custom-stocks/`
- **方法**: POST
- **Body**:
```json
{
  "stock_codes": ["600519", "000001"],
  "market_type": "A股"
}
```

### 3. 运行完整市场分析（选项4）
- **URL**: `/api/run-full-analysis/`
- **方法**: POST
- **Body**:
```json
{
  "index_query": "China",
  "market_type": "A股"
}
```

## 注意事项

- 确保 `interactive_analysis.py` 和 `extract_stock_codes.py` 在项目根目录
- 确保 MCP 服务器已启动（如果使用）
- 开发环境允许所有 CORS 来源，生产环境需要限制

