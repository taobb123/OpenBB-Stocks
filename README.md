<br />
<img src="https://github.com/OpenBB-finance/OpenBB/blob/develop/images/odp-light.svg?raw=true#gh-light-mode-only" alt="OpenBB 开放数据平台标志" width="600">
<img src="https://github.com/OpenBB-finance/OpenBB/blob/develop/images/odp-dark.svg?raw=true#gh-dark-mode-only" alt="OpenBB 开放数据平台标志" width="600">
<br />
<br />

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/openbb_finance.svg?style=social&label=Follow%20%40openbb_finance)](https://x.com/openbb_finance)
[![Discord Shield](https://img.shields.io/discord/831165782750789672)](https://discord.com/invite/xPHTuHCmuV)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/OpenBB-finance/OpenBB)
<a href="https://codespaces.new/OpenBB-finance/OpenBB">
  <img src="https://github.com/codespaces/badge.svg" height="20" />
</a>
<a target="_blank" href="https://colab.research.google.com/github/OpenBB-finance/OpenBB/blob/develop/examples/googleColab.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="在 Colab 中打开"/>
</a>
[![PyPI](https://img.shields.io/pypi/v/openbb?color=blue&label=PyPI%20Package)](https://pypi.org/project/openbb/)

OpenBB 开放数据平台（ODP）是一个开源工具集，帮助数据工程师将专有、授权和公共数据源集成到下游应用程序中，如 AI 副驾驶和研究仪表板。

ODP 作为"一次连接，随处使用"的基础设施层，可同时将数据整合并暴露给多个界面：面向量化分析师的 Python 环境、面向分析师的 OpenBB Workspace 和 Excel、面向 AI 代理的 MCP 服务器，以及面向其他应用程序的 REST API。

<a href="https://pro.openbb.co">
  <div align="center">
  <img src="https://openbb-cms.directus.app/assets/70b971ef-7a7e-486e-b5ae-1cc602f2162c.png" alt="Logo" width="1000">
  </div>
</a>

开始使用：`pip install openbb`

```python
from openbb import obb
output = obb.equity.price.historical("AAPL")
df = output.to_dataframe()
```

可用的数据集成可以在这里找到：<https://docs.openbb.co/python/reference>

---

## OpenBB Workspace

虽然开放数据平台提供了开源的数据集成基础，但 **OpenBB Workspace** 为分析师提供了企业级 UI，用于可视化数据集并利用 AI 代理。该平台的"一次连接，随处使用"架构使两者之间能够无缝集成。

您可以在 <https://pro.openbb.co> 找到 OpenBB Workspace。

### 访问方式说明

**方式 1：直接访问云端版本（无需本地后端）**

- 直接访问 <https://pro.openbb.co> 即可使用
- 使用 OpenBB 提供的云端数据源和功能
- **不需要**运行本地后端服务器
- 适合：快速开始、使用标准数据源、不需要自定义数据

**方式 2：连接本地后端（需要运行本地后端）**

如果您需要：
- 使用本地数据源或自定义数据
- 连接本地 MCP 服务器
- 使用自定义后端服务
- 访问私有数据源

则需要：
1. 运行本地 ODP 后端（`openbb-api`）或 MCP 服务器
2. 在 OpenBB Workspace 中添加并连接本地后端
3. 保持后端服务运行（不要关闭终端窗口）

**总结**：
- ✅ **仅使用云端功能**：直接访问 pro.openbb.co，**无需**本地后端
- ✅ **使用本地数据/自定义后端**：需要运行本地后端并连接到 Workspace
<a href="https://pro.openbb.co">
  <div align="center">
  <img src="https://openbb-cms.directus.app/assets/f69b6aaf-0821-4bc8-a43c-715e03a924ef.png" alt="Logo" width="1000">
  </div>
</a>

数据集成：

- 您可以从[文档](https://docs.openbb.co/workspace)或[此开源仓库](https://github.com/OpenBB-finance/backends-for-openbb)了解更多关于向 OpenBB workspace 添加数据的信息。

AI 代理集成：

- 您可以从[此开源仓库](https://github.com/OpenBB-finance/agents-for-openbb)了解更多关于向 OpenBB workspace 添加 AI 代理的信息。

### 添加 MCP 服务器

MCP（Model Context Protocol）服务器允许 OpenBB Workspace 连接到外部数据和工具。**仅支持 HTTP/SSE 协议（不支持 stdio 协议）**。

#### 正确的 URL 格式

MCP 服务器的 URL 必须是标准的 HTTP 或 HTTPS URL，格式如下：

**本地服务器示例：**
- `http://127.0.0.1:8001/mcp`
- `http://localhost:8001/mcp`

**远程服务器示例：**
- `https://example.com/mcp`
- `https://api.example.com/mcp`
- `http://192.168.1.100:8001/mcp`

#### 常见错误

❌ **错误的 URL 格式：**
- `https://mcp:financialdatasets.ai/mcp` - `mcp:` 不是有效的协议前缀
- `mcp://example.com` - MCP 协议不支持，必须使用 HTTP/HTTPS

✅ **正确的 URL 格式：**
- `https://financialdatasets.ai/mcp` - 正确的 HTTPS URL
- `http://127.0.0.1:8001/mcp` - 正确的本地服务器 URL

#### 添加步骤

1. 在 OpenBB Workspace 中，转到"Apps"（应用）标签
2. 点击"添加 MCP 服务器"或类似选项
3. 填写表单：
   - **名称**：为服务器起一个描述性名称（例如："Financial Datasets"）
   - **URL**：输入完整的 HTTP/HTTPS URL，通常以 `/mcp` 或 `/sse` 结尾
   - **客户名称**（可选）：可以留空或填写自定义名称
4. 如果是本地服务器，勾选"本地服务器?"选项
5. 点击"添加"按钮

#### 运行本地 MCP 服务器

如果您想运行 OpenBB 自己的 MCP 服务器：

**步骤 1：安装 MCP 服务器包**

```sh
pip install openbb-mcp-server
```

**步骤 2：启动服务器**

**方法 1：使用命令（推荐，如果可用）**

```sh
# 启动服务器（默认在 http://127.0.0.1:8001/mcp）
openbb-mcp

# 或使用 SSE 传输协议
openbb-mcp --transport sse

# 自定义端口
openbb-mcp --port 9000
```

**方法 2：使用 Python 模块方式（Windows 推荐）**

如果 `openbb-mcp` 命令无法识别（Windows 常见问题），使用以下方式：

```sh
# 启动服务器（默认在 http://127.0.0.1:8001/mcp）
python -m openbb_mcp_server.app.app

# 或使用 SSE 传输协议
python -m openbb_mcp_server.app.app --transport sse

# 自定义端口和主机
python -m openbb_mcp_server.app.app --host 0.0.0.0 --port 9000
```

> **Windows 用户提示**：如果 `openbb-mcp` 命令无法识别，请确保：
> 1. Python Scripts 目录已添加到系统 PATH 中（通常位于 `C:\Users\你的用户名\AppData\Local\Programs\Python\Python3.x\Scripts`）
> 2. 或者直接使用 `python -m openbb_mcp_server.app.app` 方式启动

**服务器启动后，您会看到类似以下的信息：**
```
INFO     Starting MCP server 'OpenBB MCP' with transport 'streamable-http' on http://127.0.0.1:8001/mcp
```

**步骤 3：在 OpenBB Workspace 中添加并连接**

1. **添加 MCP 服务器**：
   - 在 OpenBB Workspace 中，转到"Apps"（应用）标签
   - 点击"添加 MCP 服务器"
   - 填写表单：
     - **名称**：OpenBB-mcp（或您喜欢的名称）
     - **URL**：`http://127.0.0.1:8001/mcp`
     - **客户名称**（可选）：可以留空
   - **重要**：如果是本地服务器，请勾选"本地服务器?"选项
   - 点击"添加"按钮

2. **连接服务器**：
   - 添加后，您会看到服务器列表中出现 "OpenBB-mcp (0)"
   - 点击右侧的"连接"按钮
   - 连接成功后，工具数会从 (0) 变为实际数字，表示已发现可用工具
   - 如果显示"您需要先连接到 MCP 服务器,才能发现可用的工具。"，说明需要点击"连接"按钮

**验证连接**：
- 连接成功后，服务器名称旁边的数字会显示发现的工具数量
- 如果显示 (0)，可能是服务器未启动或连接失败，请检查服务器是否正在运行

**常用启动选项：**

```sh
# 查看帮助信息
python -m openbb_mcp_server.app.app --help

# 指定传输协议（streamable-http 或 sse）
python -m openbb_mcp_server.app.app --transport sse

# 指定主机和端口
python -m openbb_mcp_server.app.app --host 127.0.0.1 --port 8001

# 指定默认工具类别
python -m openbb_mcp_server.app.app --default-categories equity,news
```

### 将开放数据平台集成到 OpenBB Workspace

在 Python (3.9.21 - 3.12) 环境中，通过几个简单的命令将此库连接到 OpenBB Workspace。

#### 运行 ODP 后端

- 安装软件包。

在 Windows PowerShell 或 CMD 中运行：

```sh
pip install "openbb[all]"
```

> **注意**：在 Windows 上，如果使用 PowerShell，也可以使用单引号：`pip install 'openbb[all]'`

**如果遇到网络连接错误（SSL/HTTP 读取失败）：**

1. **首先升级 pip**（错误提示中建议的操作）：
   ```sh
   python.exe -m pip install --upgrade pip
   ```

2. **然后重试安装**：
   ```sh
   pip install "openbb[all]"
   ```

3. **如果仍然失败，可以尝试**：
   - 使用国内镜像源（如果在中国）：
     ```sh
     pip install "openbb[all]" -i https://pypi.tuna.tsinghua.edu.cn/simple
     ```
   - 或者增加超时时间：
     ```sh
     pip install "openbb[all]" --default-timeout=100
     ```
   - 或者使用代理（如果有）：
     ```sh
     pip install "openbb[all]" --proxy http://代理地址:端口
     ```

- 在 localhost 上启动 API 服务器。

```sh
openbb-api
```

> **Windows 用户提示**：如果 `openbb-api` 命令无法识别，请尝试以下方法：
> 
> 1. **确保 Python Scripts 目录已添加到系统 PATH 中**。通常位于 `C:\Users\你的用户名\AppData\Local\Programs\Python\Python3.x\Scripts`
> 
> 2. **或者使用 Python 模块方式启动**（注意模块名使用下划线，不是连字符）：
>    ```sh
>    python -m openbb_platform_api.main
>    ```
> 
> 3. **如果仍然失败，可能是包未正确安装**，请重新安装：
>    ```sh
>    pip install "openbb[all]"
>    ```

这将在 `127.0.0.1:6900` 通过 Uvicorn 启动一个 FastAPI 服务器。

您可以通过访问 <http://127.0.0.1:6900> 来检查它是否正常工作。

#### 将 ODP 后端集成到 OpenBB Workspace

登录 [OpenBB Workspace](https://pro.openbb.co/)，然后按照以下步骤操作：

![CleanShot 2025-05-17 at 09 51 56@2x](https://github.com/user-attachments/assets/75cffb4a-5e95-470a-b9d0-6ffd4067e069)

1. 转到"Apps"（应用）标签
2. 点击"Connect backend"（连接后端）
3. 填写表单：
   名称：Open Data Platform
   URL：<http://127.0.0.1:6900>
4. 点击"Test"（测试）。您应该会看到"Test successful"（测试成功）以及找到的应用数量。
5. 点击"Add"（添加）。

就这样。

---

<!-- TABLE OF CONTENTS -->
<details closed="closed">
  <summary><h2 style="display: inline-block">目录</h2></summary>
  <ol>
    <li><a href="#1-installation">安装</a></li>
    <li><a href="#2-contributing">贡献</a></li>
    <li><a href="#3-license">许可证</a></li>
    <li><a href="#4-disclaimer">免责声明</a></li>
    <li><a href="#5-contacts">联系方式</a></li>
    <li><a href="#6-star-history">Star 历史</a></li>
    <li><a href="#7-contributors">贡献者</a></li>
  </ol>
</details>

## 1. 安装

ODP Python 包可以通过运行 `pip install openbb` 从 [PyPI 包](https://pypi.org/project/openbb/)安装

或通过直接克隆仓库 `git clone https://github.com/OpenBB-finance/OpenBB.git`。

有关安装过程的更多信息，请参阅 [OpenBB 文档](https://docs.openbb.co/python/installation)。

### ODP CLI 安装

ODP CLI 是一个命令行界面，允许您直接从命令行访问 ODP。

可以通过运行 `pip install openbb-cli` 安装

或通过直接克隆仓库 `git clone https://github.com/OpenBB-finance/OpenBB.git`。

有关安装过程的更多信息，请参阅 [OpenBB 文档](https://docs.openbb.co/cli/installation)。

## 2. 贡献

有三种主要方式为这个项目做出贡献。（希望您现在已经为项目点星了 ⭐️）

### 成为贡献者

- 更多信息请参阅我们的[开发者文档](https://docs.openbb.co/python/developer)。

### 创建 GitHub 工单

在创建工单之前，请确保您要创建的工单在[现有问题](https://github.com/OpenBB-finance/OpenBB/issues)中不存在

- [报告错误](https://github.com/OpenBB-finance/OpenBB/issues/new?assignees=&labels=bug&template=bug_report.md&title=%5BBug%5D)
- [建议改进](https://github.com/OpenBB-finance/OpenBB/issues/new?assignees=&labels=enhancement&template=enhancement.md&title=%5BIMPROVE%5D)
- [请求功能](https://github.com/OpenBB-finance/OpenBB/issues/new?assignees=&labels=new+feature&template=feature_request.md&title=%5BFR%5D)

### 提供反馈

我们在[我们的 Discord](https://openbb.co/discord) 上最活跃，但您也可以随时通过[我们的社交媒体](https://openbb.co/links)联系我们提供反馈。

## 3. 许可证

根据 AGPLv3 许可证分发。更多信息请参阅
[LICENSE](https://github.com/OpenBB-finance/OpenBB/blob/main/LICENSE)。

## 4. 免责声明

金融工具交易涉及高风险，包括可能损失部分或全部投资金额的风险，可能不适合所有投资者。

在决定交易金融工具之前，您应该充分了解与交易金融市场相关的风险和成本，仔细考虑您的投资目标、经验水平和风险承受能力，并在需要时寻求专业建议。

开放数据平台中包含的数据不一定准确。

OpenBB 以及本网站中包含的数据的任何提供者不对因您的交易或您对所显示信息的依赖而造成的任何损失或损害承担责任。

在我们的网站、产品或文档中可能引用的所有第三方名称、徽标和品牌均为其各自所有者的商标。除非另有说明，OpenBB 及其产品和服务不受这些第三方的认可、赞助或关联。

我们对这些名称、徽标和品牌的使用仅用于识别目的，并不意味着任何此类认可、赞助或关联。

## 5. 联系方式

如果您对平台或 OpenBB 有任何疑问，请随时通过 `support@openbb.co` 给我们发邮件

如果您想打个招呼，或有意与我们合作，请随时通过 `hello@openbb.co` 联系我们

我们的任何社交媒体平台：[openbb.co/links](https://openbb.co/links)

## 6. Star 历史

这是我们成长的见证，我们才刚刚开始。

但有关对我们重要的更多指标，请查看 [openbb.co/open](https://openbb.co/open)。

[![Star History Chart](https://api.star-history.com/svg?repos=openbb-finance/OpenBB&type=Date&theme=dark)](https://api.star-history.com/svg?repos=openbb-finance/OpenBB&type=Date&theme=dark)

## 7. 贡献者

没有您，OpenBB 就不会是 OpenBB。如果我们要颠覆金融行业，每一份贡献都很重要。感谢您成为这段旅程的一部分。

<a href="https://github.com/OpenBB-finance/OpenBB/graphs/contributors">
   <img src="https://contributors-img.web.app/image?repo=OpenBB-finance/OpenBB" width="800"/>
</a>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[contributors-shield]: https://img.shields.io/github/contributors/OpenBB-finance/OpenBB.svg?style=for-the-badge
[contributors-url]: https://github.com/OpenBB-finance/OpenBB/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/OpenBB-finance/OpenBB.svg?style=for-the-badge
[forks-url]: https://github.com/OpenBB-finance/OpenBB/network/members
[stars-shield]: https://img.shields.io/github/stars/OpenBB-finance/OpenBB.svg?style=for-the-badge
[stars-url]: https://github.com/OpenBB-finance/OpenBB/stargazers
[issues-shield]: https://img.shields.io/github/issues/OpenBB-finance/OpenBB.svg?style=for-the-badge&color=blue
[issues-url]: https://github.com/OpenBB-finance/OpenBB/issues
[bugs-open-shield]: https://img.shields.io/github/issues/OpenBB-finance/OpenBB/bug.svg?style=for-the-badge&color=yellow
[bugs-open-url]: https://github.com/OpenBB-finance/OpenBB/issues?q=is%3Aissue+label%3Abug+is%3Aopen
[bugs-closed-shield]: https://img.shields.io/github/issues-closed/OpenBB-finance/OpenBB/bug.svg?style=for-the-badge&color=success
[bugs-closed-url]: https://github.com/OpenBB-finance/OpenBB/issues?q=is%3Aissue+label%3Abug+is%3Aclosed
[license-shield]: https://img.shields.io/github/license/OpenBB-finance/OpenBB.svg?style=for-the-badge
[license-url]: https://github.com/OpenBB-finance/OpenBB/blob/main/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/DidierRLopes
