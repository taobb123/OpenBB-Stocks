# 快速启动指南

## 问题解决

如果遇到 `ModuleNotFoundError`，请确保安装所有依赖：

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 完整设置步骤

### 1. 激活虚拟环境
```bash
cd market_analysis_api
.\venv\Scripts\activate
```

### 2. 安装依赖（如果还没安装）
```bash
pip install -r requirements.txt
```

如果安装过程中断，可以继续运行上面的命令，pip 会跳过已安装的包。

### 3. 运行数据库迁移
```bash
python manage.py migrate
```

### 4. 启动服务器
```bash
python manage.py runserver 8000
```

或者直接运行：
```bash
start_server.bat
```

## 常见问题

### 问题1：ModuleNotFoundError: No module named 'httpx'

**解决**：运行 `pip install httpx pandas`

### 问题2：ModuleNotFoundError: No module named 'pandas'

**解决**：运行 `pip install pandas`

### 问题3：其他模块缺失

**解决**：运行 `pip install -r requirements.txt` 安装所有依赖

## 验证安装

运行以下命令检查 Django 是否正常工作：

```bash
python manage.py check
```

如果看到 "System check identified no issues"，说明安装成功！

## 下一步

1. 确保后端服务器运行在 `http://localhost:8000`
2. 启动前端：`cd desktop && npm run dev`
3. 访问：`http://localhost:1470/market-analysis-rest`

