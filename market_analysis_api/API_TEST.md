# API 测试指南

## ✅ 正确的 API 使用方式

所有 API 端点都**只接受 POST 请求**，不能直接在浏览器中访问（会返回 405 错误）。

## 📡 API 端点

### 1. 健康检查（GET 请求）
```bash
# 可以直接在浏览器访问
http://localhost:8003/api/
```

### 2. 提取股票代码（POST 请求）
```bash
curl -X POST http://localhost:8003/api/extract-stock-codes/ \
  -H "Content-Type: application/json" \
  -d '{"content": "立讯精密（002475）、歌尔股份（002241）"}'
```

### 3. 分析自定义股票列表（完整，POST）
与历史行为一致：K 线、指标、报告等（`scope=full`）。
```bash
curl -X POST http://localhost:8003/api/analyze-custom-stocks/ \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["600519", "000001"], "market_type": "A股"}'
```

### 4. 仅走势图 / K 线（charts，POST）
请求体与上面相同；响应侧重历史 K 线与绘图数据，不做完整时机/基本面/MCP。返回 JSON 中含 `scope: "charts"`，`report` 为空字符串。
```bash
curl -X POST http://localhost:8003/api/analyze-custom-stocks/charts/ \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["600519", "000001"], "market_type": "A股"}'
```

### 5. 买入/时机分析报告（report，POST）
请求体相同；生成文本报告并写入 `Buy.txt` 等逻辑；响应中通常不含 `price_series`（`scope=report`）。返回 JSON 中含 `scope: "report"`。
```bash
curl -X POST http://localhost:8003/api/analyze-custom-stocks/report/ \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["600519", "000001"], "market_type": "A股"}'
```

### 6. 运行完整市场分析（POST 请求）
```bash
curl -X POST http://localhost:8003/api/run-full-analysis/ \
  -H "Content-Type: application/json" \
  -d '{"index_query": "China", "market_type": "A股"}'
```

## ⚠️ 常见错误

### 405 Method Not Allowed
- **原因**：使用 GET 请求访问只支持 POST 的端点
- **解决**：使用 POST 请求，并在 body 中传递 JSON 数据

### 404 Not Found
- **原因**：URL 拼写错误或缺少尾部斜杠
- **解决**：检查 URL 是否正确，确保有尾部斜杠

## 🔍 测试工具

推荐使用：
- **Postman** - 图形化 API 测试工具
- **curl** - 命令行工具
- **前端页面** - `http://localhost:1472/market-analysis-rest`

