# odoo-llm 信息安全审计与内网部署方案

> **适用场景：** 公司内网部署 Odoo 18.0 + odoo-llm 模块组，接入内部部署的 AI 大模型（GLM-4、DeepSeek 等），满足信息安全与合规要求，**禁止任何公司数据发往外网**。
>
> **审计版本：** odoo-llm（apexive 开源框架，Odoo 18.0）
> **报告日期：** 2026-04-25

---

## 目录

1. [风险总览](#一风险总览)
2. [最高风险：代码层面的安全漏洞](#二最高风险代码层面的安全漏洞必须修改代码)
3. [可通过配置规避的风险](#三可通过配置规避的风险)
4. [推荐内网部署方案](#四推荐内网部署方案)
5. [分阶段实施步骤](#五分阶段实施步骤)
6. [防火墙规则建议](#六防火墙规则建议)

---

## 一、风险总览

| 优先级 | 风险点 | 影响模块 | 规避方式 |
|--------|--------|---------|---------|
| 🔴 代码 Bug | `anthropic_get_client()` 忽略 `api_base` 配置 | `llm_anthropic` | 不安装 |
| 🔴 代码 Bug | `_get_mistral_client()` OCR 忽略 `api_base` 配置 | `llm_mistral` | 不安装 |
| 🔴 代码漏洞 | Webhook 公开端点 + `sudo()` 无认证提权 | `llm_fal_ai` | **不安装** |
| 🔴 架构风险 | 全部对话数据发往外部 Letta 服务 | `llm_letta` | 不安装 |
| 🔴 设计缺陷 | HTTP 资源爬取无域名白名单（SSRF 风险） | `llm_knowledge` | 打补丁或禁用 HTTP 类型 |
| 🟠 云服务 | 硬编码 `api.fal.ai` / `comfy.icu` 外网地址 | `llm_fal_ai`, `llm_comfy_icu` | 不安装 |
| 🟠 数据外传 | 文件/文档内容发往 Mistral OCR 云服务 | `llm_knowledge_mistral` | 不安装 |
| 🟠 训练数据 | 数据集上传至外部 LLM Provider | `llm_training` | 不安装 |
| 🟡 配置依赖 | `api_base` 为空时 SDK 回落到外网默认地址 | `llm_openai` | 正确配置内网地址 |
| ✅ 安全 | 默认连接 `localhost:11434` | `llm_ollama` | 无需特殊处理 |
| ✅ 安全 | 纯本地 PostgreSQL 向量存储 | `llm_pgvector` | 无需特殊处理 |

---

## 二、最高风险：代码层面的安全漏洞（必须修改代码）

> 以下风险源于代码本身的逻辑缺陷，无论如何配置都会向第三方发送数据。**在你的使用场景中，不安装对应模块即可完全规避**；如果将来有需要使用这些模块，必须先打补丁。

### 🔴 漏洞 1：`llm_anthropic` — `api_base` 配置完全无效，强制连接外网

**文件：** `llm_anthropic/models/anthropic_provider.py` 第 26 行

**问题：** `anthropic_get_client()` 创建客户端时没有传入 `base_url` 参数，导致管理员在后台配置的 `api_base` 字段被完全忽略。Anthropic Python SDK 在未指定 `base_url` 时，始终连接 `https://api.anthropic.com`。

```python
# ❌ 现有代码 —— api_base 字段被完全忽略
def anthropic_get_client(self):
    return Anthropic(api_key=self.api_key)
    # SDK 内部默认: base_url = "https://api.anthropic.com"
```

**危害：** 完整的对话内容（用户消息、业务上下文、工具定义、system prompt）会被发往 `api.anthropic.com`，即使服务器处于内网环境也无法阻止（只要有出站网络权限）。

**修复方案：**

```python
# ✅ 修复后 —— 支持重定向到内部代理或自托管服务
def anthropic_get_client(self):
    return Anthropic(
        api_key=self.api_key,
        base_url=self.api_base or None,  # None 时 SDK 使用默认值
    )
```

---

### 🔴 漏洞 2：`llm_mistral` OCR — `api_base` 无效，文件内容发往 Mistral 云端

**文件：** `llm_mistral/models/mistral_provider.py` 第 72–77 行

**问题：** Mistral 的 Chat/Embedding 功能通过 `_dispatch` 复用了 `llm_openai` 的客户端（已正确传入 `base_url`），但 OCR 专用客户端 `_get_mistral_client()` 独立创建，同样忽略了 `api_base`。

```python
# ❌ 现有代码 —— OCR 客户端忽略 api_base
def _get_mistral_client(self):
    return Mistral(
        api_key=self.api_key,
        # api_base 未传入，SDK 默认连接 https://api.mistral.ai
    )
```

**危害：** `llm_knowledge_mistral` 模块会把**发票、合同、图片等文件的 base64 编码内容**发送至 Mistral OCR 云服务（`mistral_client.ocr.process()`）。

**修复方案：**

```python
# ✅ 修复后 —— Mistral SDK 的 base_url 参数名为 server_url
def _get_mistral_client(self):
    kwargs = {"api_key": self.api_key}
    if self.api_base:
        kwargs["server_url"] = self.api_base
    return Mistral(**kwargs)
```

---

### 🔴 漏洞 3：`llm_fal_ai` Webhook — 公开无认证端点 + `sudo()` 提权

**文件：** `llm_fal_ai/controllers/webhook_controller.py`

**问题：** Webhook 端点使用 `auth="public"` + `csrf=False` + 内部调用 `sudo()`，三者叠加形成严重安全漏洞。

```python
# ❌ 现有代码 —— 任何人无需登录即可触发数据库操作
@http.route('/llm/generate_job/webhook/<int:job_id>',
            auth="public", csrf=False, methods=["POST"])
def webhook(self, job_id, **kwargs):
    job = request.env['llm.generation.job'].sudo().search(...)
    # sudo() 让未认证的外部请求获得最高权限
```

**危害：**
- `job_id` 是自增整数，攻击者可枚举遍历所有任务
- 无需登录、无需 CSRF Token，直接 POST 即可触发
- `sudo()` 绕过所有 Odoo 权限控制，以管理员身份操作数据库
- **即使你不使用 FAL.AI 外部服务，只要安装了该模块，漏洞就存在**

**修复方案（若必须保留该模块）：**

```python
# ✅ 方案：增加签名验证 + IP 白名单
@http.route('/llm/generate_job/webhook/<int:job_id>',
            auth="none", csrf=False, methods=["POST"])
def webhook(self, job_id, **kwargs):
    # 1. IP 白名单检查
    allowed_ips = request.env['ir.config_parameter'].sudo().get_param(
        'llm.fal_ai.webhook_allowed_ips', ''
    ).split(',')
    if request.httprequest.remote_addr not in [ip.strip() for ip in allowed_ips]:
        return Response(status=403)

    # 2. 签名验证（使用 FAL.AI 提供的 webhook secret）
    signature = request.httprequest.headers.get('X-Fal-Signature', '')
    secret = request.env['ir.config_parameter'].sudo().get_param(
        'llm.fal_ai.webhook_secret', ''
    )
    expected = hmac.new(secret.encode(), request.httprequest.data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return Response(status=401)
    ...
```

> **推荐做法：直接不安装 `llm_fal_ai` 模块。**

---

### 🔴 漏洞 4：`llm_letta` — 双向数据通道，对话内容+业务数据全部外泄

**文件：** `llm_letta/models/letta_provider.py`

**问题：** Letta 是外部 AI Agent 托管平台，该模块与其形成双向数据通道：

```python
# 方向1：Odoo → Letta（发送对话消息）
stream = client.agents.messages.create(
    agent_id=agent_id,
    messages=[MessageCreateParam(role="user", content=user_content)],
    streaming=True,
)

# 方向2：Letta → Odoo MCP（Letta 反向调用 Odoo 查询业务数据）
config_param = CreateStreamableHTTPMcpServerParam(
    server_url=server_url,
    custom_headers={"Authorization": "Bearer {{ ODOO_API_KEY }}"},
)
client.mcp_servers.create(config=config_param, server_name=server_name)
```

**危害：**
1. 用户消息、system prompt、工具定义发往 Letta 服务器
2. Letta 获得授权后，可通过 MCP 接口反向查询 Odoo 中的任意业务数据
3. 构成完整的"数据出入双通道"，信息泄露面极大

**修复方案：不安装此模块。** 若确有 Agent 框架需求，改用支持完全内网部署的替代方案（如 Dify、Coze 私有版）。

---

### 🔴 漏洞 5：`llm_knowledge` HTTP 资源爬取 — 无域名白名单（SSRF 风险）

**文件：** `llm_knowledge/models/llm_resource_http.py` 第 104 行

**问题：** 对用户输入的 URL 没有任何域名白名单或内网地址过滤：

```python
# ❌ 现有代码 —— 向任意 URL 发起请求，包括内网其他服务
response = requests.get(
    initial_url,          # 来自用户输入，无验证
    timeout=30,
    headers=headers,
    allow_redirects=True  # 还会跟随重定向
)
```

**危害：**
- 用户可输入 `http://192.168.1.1/admin` 等内网地址，探测内网拓扑（SSRF）
- 跟随重定向可能导致请求链无限延伸
- 即使 Odoo 在内网，也会主动向外发起连接，暴露内网出口 IP

**修复方案（添加域名白名单）：**

在 `llm_knowledge/models/llm_resource_http.py` 的资源抓取入口处增加以下校验：

```python
def _validate_url_whitelist(self, url):
    """校验 URL 是否在允许的域名白名单内"""
    whitelist_param = self.env['ir.config_parameter'].sudo().get_param(
        'llm.knowledge.allowed_domains', ''
    )
    if not whitelist_param:
        raise UserError(_(
            "HTTP 资源抓取功能未配置域名白名单。\n"
            "请在系统参数中设置 'llm.knowledge.allowed_domains'，"
            "多个域名用逗号分隔，例如: intranet.company.com,docs.company.com"
        ))
    from urllib.parse import urlparse
    import ipaddress

    parsed = urlparse(url)
    domain = parsed.netloc.split(':')[0]  # 去掉端口号

    # 禁止内网 IP 段（防止 SSRF）
    try:
        ip = ipaddress.ip_address(domain)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise UserError(_("不允许访问内网 IP 地址: %s") % domain)
    except ValueError:
        pass  # 不是 IP，继续域名校验

    allowed = [d.strip().lower() for d in whitelist_param.split(',')]
    domain_lower = domain.lower()
    if not any(domain_lower == d or domain_lower.endswith('.' + d) for d in allowed):
        raise UserError(_("域名 '%s' 不在白名单内，操作被拒绝") % domain)
```

**系统参数配置（Odoo 后台 → 技术 → 系统参数）：**

```
键名：llm.knowledge.allowed_domains
值：  intranet.company.com,wiki.company.com
```

---

### 🟠 漏洞 6：`llm_comfy_icu` — 硬编码外网 URL

**文件：** `llm_comfy_icu/models/http_client.py` 第 16 行

```python
# ❌ 硬编码指向 comfy.icu 云服务
DEFAULT_BASE_URL = "https://comfy.icu/api/v1"
```

**修复方案：** 不使用图像生成则**不安装此模块**。如需图像生成，使用 `llm_comfyui`（指向内网 ComfyUI 服务器）代替。

---

## 三、可通过配置规避的风险

### 3.1 模块安装策略

按安全等级给出完整的模块取舍建议：

#### ✅ 可安全安装（零外网风险）

| 模块 | 说明 |
|------|------|
| `llm` | 基础框架，无任何外发逻辑 |
| `llm_thread` | 对话管理，无外发逻辑 |
| `llm_tool` | 工具框架，无外发逻辑 |
| `llm_assistant` | 助手配置，无外发逻辑 |
| `llm_generate` | 统一生成接口，无外发逻辑 |
| `llm_generate_job` | 异步任务队列，无额外外发 |
| `llm_store` | 向量存储抽象层，无外发逻辑 |
| `llm_pgvector` | 纯本地 PostgreSQL 向量存储 |
| `llm_ollama` | 默认 `localhost:11434`，天然内网 |
| `llm_tool_account` | 纯本地执行，调用 Odoo 会计模块 |
| `llm_tool_mis_builder` | 纯本地执行，调用 MIS 报表模块 |
| `llm_knowledge_automation` | 纯本地自动化触发 |

#### ⚠️ 可安装但需正确配置

| 模块 | 配置要求 | 风险说明 |
|------|---------|---------|
| `llm_openai` | `api_base` **必须**填写内网地址 | 若 `api_base` 为空，SDK 连接 `api.openai.com`；正确配置后 GLM-4/DeepSeek 均可接入 |
| `llm_knowledge` | **禁止**使用"HTTP URL"类型资源；如需使用，必须先打白名单补丁 | HTTP 资源爬取有 SSRF 风险 |
| `llm_mcp_server` | 仅在内网设备有需要时安装；防火墙禁止外网访问 `/mcp` 端点 | 暴露 Odoo 工具能力，需网络层隔离 |
| `llm_comfyui` | `api_base` 必须填写内网 ComfyUI 服务地址 | 若 ComfyUI 部署在内网则安全 |
| `llm_chroma` | ChromaDB 必须部署在内网 | 推荐用 `llm_pgvector` 替代，更简单安全 |
| `llm_qdrant` | Qdrant 必须部署在内网 | 同上 |
| `llm_knowledge_llama` | LlamaIndex 本地运行，但需注意 llama_index 库自身有遥测 | 建议在 Python 环境中设置 `POSTHOG_DISABLED=1` |
| `llm_document_page` | 纯本地 Odoo 文档集成 | 无外网风险 |

#### ❌ 禁止安装（会向外网发送数据）

| 模块 | 禁止原因 |
|------|---------|
| `llm_anthropic` | `base_url` Bug，始终连接 `api.anthropic.com` |
| `llm_mistral` | OCR 功能 `base_url` Bug，文件内容发往 `api.mistral.ai` |
| `llm_knowledge_mistral` | 文档/图片内容发往 Mistral OCR 云服务 |
| `llm_replicate` | 纯云端模型市场，无内网选项 |
| `llm_fal_ai` | 存在严重 Webhook 安全漏洞 + 纯云端服务 |
| `llm_comfy_icu` | 硬编码 `comfy.icu` 云服务地址 |
| `llm_letta` | 双向数据通道，对话内容+业务数据全部外泄 |
| `llm_training` | 将训练数据集上传至外部 LLM Provider |

### 3.2 运行期配置要点

即使安装了安全模块，以下配置若不正确仍会产生风险：

1. **`llm_openai` Provider 的 `api_base` 字段**
   - ❌ 禁止留空（SDK 会回落到 `api.openai.com`）
   - ✅ 必须填写内网推理服务地址，例如 `http://192.168.1.100:8000/v1`

2. **`llm_knowledge` 知识资源类型**
   - ❌ 禁止使用"外部 HTTP URL"类型的知识资源
   - ✅ 只使用文件上传（PDF、Word、TXT）方式导入文档

3. **`llm_mcp_server` 的网络访问控制**
   - ❌ 禁止外网访问 `/mcp` HTTP 端点
   - ✅ 在防火墙/Nginx 层面限制只有内网指定 IP 可访问

4. **LlamaIndex 遥测关闭（如安装 `llm_knowledge_llama`）**
   - 在 Odoo 服务启动脚本中添加环境变量：
   ```bash
   export POSTHOG_DISABLED=1
   export ANONYMIZED_TELEMETRY=False
   ```

---

## 四、推荐内网部署方案

### 4.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        公司内网（隔离区）                           │
│                                                                 │
│  ┌─────────────────────┐        ┌──────────────────────────┐    │
│  │     Odoo 18.0        │        │    内网 AI 推理服务        │    │
│  │                     │        │                          │    │
│  │  已安装模块：          │  HTTP  │  • vLLM / Ollama         │    │
│  │  llm（基础）          ├───────►│  • DeepSeek-R1 / V3      │    │
│  │  llm_thread         │  内网   │  • GLM-4 / ChatGLM3      │    │
│  │  llm_tool           │  仅限   │  • Qwen2.5 / Llama3      │    │
│  │  llm_assistant      │        │                          │    │
│  │  llm_generate       │        │  OpenAI 兼容 API          │    │
│  │  llm_openai ────────┘        │  http://内网IP:端口/v1     │    │
│  │  llm_ollama ─────────────────►  http://localhost:11434   │    │
│  │  llm_knowledge      │        └──────────────────────────┘    │
│  │  llm_store          │                                        │
│  │  llm_pgvector       │        ┌──────────────────────────┐    │
│  │  llm_tool_account   │        │    PostgreSQL 数据库       │    │
│  │  llm_tool_mis_*     ├───────►│    + pgvector 扩展        │    │
│  │                     │        │    （RAG 向量存储）         │    │
│  └─────────────────────┘        └──────────────────────────┘    │
│           ▲                                                      │
│           │ 员工浏览器访问（内网）                                   │
│           │                                                      │
│  ┌────────┴──────────┐                                          │
│  │  Nginx 反向代理    │  ← 禁止外网访问 /mcp 端点                    │
│  │  内网访问控制      │                                            │
│  └───────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │ 外网访问：完全阻断
         ✗ （防火墙默认拒绝 Odoo 服务器出站）
```

### 4.2 安装模块清单（推荐最小化安全集）

```
必装核心：
  llm
  llm_thread
  llm_tool
  llm_assistant
  llm_generate

AI 接入（二选一或同时安装）：
  llm_openai          ← 接入 GLM-4 / DeepSeek（OpenAI 协议兼容）
  llm_ollama          ← 接入 Ollama 本地部署模型

向量/知识库（全本地）：
  llm_store
  llm_pgvector        ← 推荐，复用现有 PostgreSQL

知识库（谨慎使用）：
  llm_knowledge       ← 只用文件上传，禁用 HTTP 资源类型

业务工具（按需选装）：
  llm_tool_account      ← 18 个会计相关工具
  llm_tool_mis_builder  ← 44 个 MIS 报表工具
  llm_document_page     ← 与 Odoo 文档模块集成
```

### 4.3 Provider 配置示例

#### DeepSeek（内网 vLLM 部署）

```
Provider 名称：DeepSeek-R1-内网
Service：      openai
API Key：      your-internal-key（vLLM 可配置不验证 key，填任意字符串即可）
API Base：     http://192.168.1.100:8000/v1
```

在 vLLM 启动命令中：
```bash
vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
  --host 0.0.0.0 \
  --port 8000 \
  --api-key your-internal-key
```

#### GLM-4（内网 API 服务）

```
Provider 名称：GLM-4-内网
Service：      openai
API Key：      your-internal-glm4-key
API Base：     http://192.168.1.101:8001/v1
```

#### Ollama（本机或内网）

```
Provider 名称：Ollama-本地
Service：      ollama
API Base：     http://localhost:11434
（API Key 留空）
```

在目标服务器安装 Ollama 并拉取模型：
```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取模型（在内网服务器上操作）
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b

# 允许外部访问（若 Odoo 与 Ollama 不在同一主机）
OLLAMA_HOST=0.0.0.0 ollama serve
```

### 4.4 pgvector 激活（RAG 向量存储）

```sql
-- 在 PostgreSQL 中执行（需要 PostgreSQL 12+ 且已安装 pgvector 扩展包）
CREATE EXTENSION IF NOT EXISTS vector;
```

Ubuntu/Debian 安装 pgvector：
```bash
sudo apt install postgresql-16-pgvector
# 或从源码编译
git clone https://github.com/pgvector/pgvector.git
cd pgvector && make && sudo make install
```

### 4.5 Nginx 安全配置（限制 MCP 端点访问）

若安装了 `llm_mcp_server` 模块，在 Nginx 中添加以下配置限制访问范围：

```nginx
server {
    listen 443 ssl;
    server_name odoo.company.internal;

    # 限制 MCP 端点只允许内网特定 IP 访问
    location /mcp {
        allow 192.168.1.0/24;   # 内网网段
        allow 10.0.0.0/8;       # 可选：扩展内网段
        deny all;               # 拒绝其他所有请求

        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 其他路由正常转发
    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 五、分阶段实施步骤

### 第一阶段：基础验证（约 1 天）

**目标：** 验证内网 AI 服务可正常通过 Odoo 调用

```bash
# 1. 安装核心模块
odoo-bin -d your_db -i llm,llm_thread,llm_tool,llm_assistant,llm_generate,llm_openai,llm_ollama

# 2. 验证 Python 依赖
pip install openai ollama

# 3. 配置 Provider（Odoo 后台操作）
#    Settings → LLM → Providers → New
#    Service: openai
#    API Base: http://192.168.1.100:8000/v1
#    API Key: your-internal-key

# 4. 同步模型列表
#    点击 Provider 的 "Sync Models" 按钮

# 5. 测试基本对话
#    创建一个 LLM Thread，发送测试消息
```

**验证点：**
- [ ] 对话正常响应
- [ ] 网络监控确认无外网请求（tcpdump 或防火墙日志）

---

### 第二阶段：RAG 知识库（约 2 天）

**目标：** 建立内部文档知识库，支持文档问答

```bash
# 1. 安装 pgvector 扩展
sudo apt install postgresql-16-pgvector

# 2. 在数据库中激活扩展
psql -d your_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. 安装知识库模块
odoo-bin -d your_db -i llm_store,llm_pgvector,llm_knowledge

# 4. 安装 Python 依赖
pip install pgvector numpy markdownify PyMuPDF

# 5. 配置 Embedding 模型（Odoo 后台）
#    在 Provider 中确认有 embedding 类型的模型
#    （Ollama 的 nomic-embed-text，或 vLLM 的 embedding 模型）
```

**操作流程：**
1. 进入 **LLM → Knowledge → Resources**
2. 点击 **Upload**，选择文件上传（PDF/Word/TXT）
3. 等待状态变为 `ready`（经历 parse → chunk → embed 流程）
4. 在对话中使用知识库检索

**验证点：**
- [ ] 文档上传成功，状态到达 `ready`
- [ ] 对话中引用知识库内容准确
- [ ] 确认未使用 HTTP URL 类型资源

---

### 第三阶段：业务工具（约 2 天）

**目标：** 让 AI 能够查询和操作 Odoo 业务数据

```bash
# 安装业务工具模块
odoo-bin -d your_db -i llm_tool_account
# 或（如已安装 MIS Builder）
odoo-bin -d your_db -i llm_tool_mis_builder
```

**配置 Assistant 启用工具：**
1. 进入 **LLM → Assistants → New**
2. 选择 Provider 和 Model
3. 在 **Tools** 标签页添加需要的工具
4. 设置 System Prompt，告知 AI 可用的工具能力

**验证点：**
- [ ] AI 能正确调用会计查询工具
- [ ] 工具执行结果正确返回到对话中
- [ ] 工具权限控制符合预期

---

### 第四阶段：安全加固（约 1 天）

**目标：** 完成所有安全配置，建立兜底防护

```bash
# 1. 配置 HTTP 知识资源白名单（如果使用了 llm_knowledge）
#    Settings → Technical → System Parameters → New
#    Key:   llm.knowledge.allowed_domains
#    Value: intranet.company.com,docs.company.com

# 2. 防火墙出站规则（在网络设备或服务器 iptables 上配置）
# 示例：iptables 规则
iptables -I OUTPUT -s <Odoo服务器IP> -d <AI推理服务IP> -p tcp --dport 8000 -j ACCEPT
iptables -I OUTPUT -s <Odoo服务器IP> -d <PostgreSQL IP> -p tcp --dport 5432 -j ACCEPT
iptables -A OUTPUT -s <Odoo服务器IP> -j DROP  # 默认拒绝所有出站

# 3. 验证无外网访问
curl -v --interface <Odoo服务器IP> https://api.openai.com
# 期望结果：连接被拒绝或超时
```

**验证清单：**
- [ ] `llm_anthropic`、`llm_mistral`、`llm_fal_ai`、`llm_letta`、`llm_replicate`、`llm_training` 均未安装
- [ ] 所有 Provider 的 `api_base` 已填写内网地址
- [ ] `llm_knowledge` 无 HTTP URL 类型的资源记录
- [ ] Odoo 服务器防火墙出站规则已生效
- [ ] 用 网络监控工具确认无外网连接

---

## 六、防火墙规则建议

### 服务器级别（iptables 示例）

```bash
#!/bin/bash
# Odoo 服务器出站规则（白名单策略）

ODOO_IP="192.168.1.50"       # Odoo 服务器 IP
AI_SERVER="192.168.1.100"    # AI 推理服务器 IP
DB_SERVER="192.168.1.200"    # PostgreSQL 服务器 IP
MAIL_SERVER="192.168.1.10"   # 内网邮件服务器 IP

# 允许访问内网 AI 服务
iptables -A OUTPUT -s $ODOO_IP -d $AI_SERVER -p tcp --dport 8000 -j ACCEPT
iptables -A OUTPUT -s $ODOO_IP -d $AI_SERVER -p tcp --dport 11434 -j ACCEPT  # Ollama

# 允许访问数据库
iptables -A OUTPUT -s $ODOO_IP -d $DB_SERVER -p tcp --dport 5432 -j ACCEPT

# 允许访问内网邮件服务器（如有需要）
iptables -A OUTPUT -s $ODOO_IP -d $MAIL_SERVER -p tcp --dport 465 -j ACCEPT

# 允许 DNS 解析（仅限内网 DNS）
iptables -A OUTPUT -s $ODOO_IP -p udp --dport 53 -d 192.168.1.1 -j ACCEPT

# 允许本机回环
iptables -A OUTPUT -s $ODOO_IP -d 127.0.0.0/8 -j ACCEPT

# 默认拒绝所有其他出站流量（包括所有外网）
iptables -A OUTPUT -s $ODOO_IP -j DROP
```

### 网络设备级别（策略说明）

```
出站规则（Odoo 服务器 → 目标）：
  允许：Odoo服务器 → 内网AI推理服务 (TCP:8000, TCP:11434)
  允许：Odoo服务器 → PostgreSQL数据库 (TCP:5432)
  允许：Odoo服务器 → 内网邮件服务器 (TCP:25/465/587)（如需发邮件）
  允许：Odoo服务器 → 内网DNS服务器 (UDP:53)
  拒绝：Odoo服务器 → 0.0.0.0/0（默认拒绝所有外网出站）

入站规则（外部 → Odoo 服务器）：
  允许：内网用户网段 → Odoo服务器 (TCP:443, TCP:8069)
  禁止：外网 → Odoo服务器 /mcp 端点（或通过 Nginx 限制）
  拒绝：0.0.0.0/0 → Odoo服务器（默认拒绝外网入站）
```

---

## 附录：安全配置核查清单

在上线前，逐项确认以下检查点：

### 模块安装检查

- [ ] `llm_anthropic` **未安装**
- [ ] `llm_mistral` **未安装**
- [ ] `llm_knowledge_mistral` **未安装**
- [ ] `llm_replicate` **未安装**
- [ ] `llm_fal_ai` **未安装**
- [ ] `llm_comfy_icu` **未安装**
- [ ] `llm_letta` **未安装**
- [ ] `llm_training` **未安装**

### Provider 配置检查

- [ ] 所有已配置的 Provider 的 `api_base` 字段**非空**
- [ ] `api_base` 填写的是**内网地址**（以 `http://192.168.` 或 `http://10.` 开头，或内网域名）
- [ ] `api_base` **不包含** `openai.com`、`anthropic.com`、`mistral.ai`、`replicate.com` 等外网域名

### 知识库配置检查

- [ ] `llm_knowledge` 中**没有** Source Type 为"HTTP URL"的资源记录
- [ ] 系统参数 `llm.knowledge.allowed_domains` 已按需配置（或该功能已禁用）

### 网络安全检查

- [ ] 防火墙出站规则已配置，Odoo 服务器**无法**访问外网
- [ ] 用 `curl` 测试外网连接**超时或被拒绝**：
  ```bash
  curl --max-time 5 https://api.openai.com  # 应该超时
  curl --max-time 5 https://api.anthropic.com  # 应该超时
  ```
- [ ] `/mcp` 端点已被 Nginx/防火墙限制为仅内网可访问（如安装了 `llm_mcp_server`）

### 功能验证

- [ ] 与内网 AI 模型对话正常（基本聊天功能）
- [ ] 知识库文档上传和检索正常
- [ ] 业务工具（如会计查询）调用正常
- [ ] 用网络监控工具（如 `tcpdump`）确认**无外网连接**产生

---

*文档生成时间：2026-04-25*
*适用框架版本：odoo-llm（apexive），Odoo 18.0*
