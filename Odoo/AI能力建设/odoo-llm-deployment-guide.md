# odoo-llm 部署指南

> **框架：** apexive/odoo-llm（Odoo 18.0）
> **文档版本：** 2026-05
> **适用场景：** 公司内网部署，接入内部 AI 推理服务（GLM-4、DeepSeek、Qwen 等），零外网依赖

---

## 目录

1. [环境要求](#一环境要求)
2. [安装 odoo-llm 模块](#二安装-odoo-llm-模块)
3. [内网 AI 推理服务部署](#三内网-ai-推理服务部署)
4. [Odoo 后台配置 Provider](#四odoo-后台配置-provider)
5. [配置 AI 模型](#五配置-ai-模型)
6. [配置 AI 助手（Assistant）](#六配置-ai-助手assistant)
7. [知识库（RAG）配置](#七知识库rag配置)
8. [生产环境优化](#八生产环境优化)
9. [验证与测试](#九验证与测试)
10. [故障排查](#十故障排查)

---

## 一、环境要求

### 基础软件

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Odoo | 18.0 | 18.0 latest | 框架仅支持 18.0 |
| Python | 3.10 | 3.11+ | Odoo 18 依赖 |
| PostgreSQL | 14 | 16 | 若用 RAG 需装 pgvector 扩展 |
| Node.js | 18 | 20 LTS | 前端资源编译 |

### 服务器资源（Odoo 主机）

| 配置 | 最低 | 推荐（生产） |
|------|------|------------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 50 GB | 200 GB+（存储附件和向量数据） |

### AI 推理服务器（独立部署）

| 模型规模 | GPU 显存 | CPU 可运行 |
|---------|---------|-----------|
| 7B 模型（如 DeepSeek-R1-7B、Qwen2.5-7B） | 16 GB VRAM | 可（慢） |
| 14B 模型（如 Qwen2.5-14B） | 24 GB VRAM | 不推荐 |
| 32B+ 模型 | 2×24 GB+ | 否 |

---

## 二、安装 odoo-llm 模块

### 2.1 获取源码

```bash
# 方式 A：克隆到 addons 目录（推荐）
cd /opt/odoo/addons
git clone https://github.com/apexive/odoo-llm.git odoo-llm
# 国内可用镜像（若 GitHub 访问慢）：
# git clone https://gitee.com/mirrors/odoo-llm.git odoo-llm

# 方式 B：直接下载压缩包
wget https://github.com/apexive/odoo-llm/archive/refs/heads/18.0.zip
unzip 18.0.zip -d /opt/odoo/addons/
mv /opt/odoo/addons/odoo-llm-18.0 /opt/odoo/addons/odoo-llm
```

### 2.2 安装 Python 依赖（按需选择）

**内网部署最小依赖（接入 OpenAI 协议兼容模型）：**

```bash
# 激活 Odoo 虚拟环境
source /opt/odoo/venv/bin/activate

# 最小安装（OpenAI 协议 + Ollama + 向量存储）
pip install openai ollama pgvector numpy pydantic>=2.0.0 jinja2 jsonschema pyyaml

# 若使用知识库（RAG）文档处理
pip install markdownify PyMuPDF markdown2 requests
```

**完整安装（所有模块）：**

```bash
pip install -r /opt/odoo/addons/odoo-llm/requirements.txt
```

> **内网注意：** 若无法访问 PyPI，需预先下载 whl 包或搭建内网 pip mirror（如 devpi、bandersnatch）。

### 2.3 配置 Odoo addons_path

编辑 Odoo 配置文件（通常位于 `/etc/odoo/odoo.conf`）：

```ini
[options]
addons_path = /opt/odoo/odoo/addons,
              /opt/odoo/addons,
              /opt/odoo/addons/odoo-llm   ; ← 添加此行

; 或者将各模块目录加入（二选一）
; addons_path = ..., /opt/odoo/addons/odoo-llm/llm,
;                    /opt/odoo/addons/odoo-llm/llm_thread,
;                    ...
```

> **推荐做法：** 将 `odoo-llm` 目录作为顶级 addons 目录，Odoo 会自动扫描子目录。

### 2.4 重启并安装模块

```bash
# 重启 Odoo 服务
sudo systemctl restart odoo

# 或手动启动（调试模式）
python /opt/odoo/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf \
    -d your_database \
    --dev=all
```

在 Odoo 后台：**应用 → 搜索并更新应用列表 → 安装以下模块（按顺序）：**

**最小化安装（内网 AI，推荐）：**

```
必装：
  llm                  # 核心基础
  llm_thread           # 对话界面
  llm_tool             # 工具框架
  llm_assistant        # AI 助手
  llm_generate         # 内容生成

AI 接入（二选一）：
  llm_openai           # ← 用于接入 DeepSeek/GLM-4/vLLM（OpenAI 协议）
  llm_ollama           # ← 用于接入本地 Ollama 服务

向量存储（如需 RAG）：
  llm_store
  llm_pgvector         # 基于 PostgreSQL，推荐内网使用

知识库（如需 RAG）：
  llm_knowledge
```

> **安装顺序：** Odoo 依赖管理会自动处理顺序，只需安装终端模块（如 `llm_assistant`），依赖会自动安装。

---

## 三、内网 AI 推理服务部署

选择以下任一方式部署内网 AI 服务：

### 方式 A：vLLM（推荐生产环境，GPU 服务器）

**安装：**

```bash
pip install vllm
```

**启动 DeepSeek 模型（OpenAI 兼容接口）：**

```bash
python -m vllm.entrypoints.openai.api_server \
    --model /models/DeepSeek-R1-Distill-Qwen-7B \
    --served-model-name deepseek-r1-7b \
    --host 0.0.0.0 \
    --port 8000 \
    --api-key your-internal-api-key \
    --max-model-len 8192 \
    --dtype float16
```

**使用 systemd 守护进程：**

```ini
# /etc/systemd/system/vllm.service
[Unit]
Description=vLLM AI Inference Server
After=network.target

[Service]
Type=simple
User=ai
WorkingDirectory=/opt/ai
ExecStart=/opt/ai/venv/bin/python -m vllm.entrypoints.openai.api_server \
    --model /models/DeepSeek-R1-Distill-Qwen-7B \
    --served-model-name deepseek-r1-7b \
    --host 0.0.0.0 \
    --port 8000 \
    --api-key your-internal-api-key
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm
sudo systemctl start vllm
```

**验证：**

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer your-internal-api-key"
# 应返回模型列表 JSON
```

---

### 方式 B：Ollama（推荐开发/测试，CPU 或 GPU 均可）

**安装：**

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# 或离线安装（内网）
# 从官网下载对应平台安装包后：
sudo dpkg -i ollama_linux_amd64.deb
```

**配置监听地址（允许内网其他主机访问）：**

```bash
# 编辑 systemd service
sudo systemctl edit ollama

# 添加环境变量
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

**拉取并运行模型（需先从外网下载，再传入内网）：**

```bash
# 有外网时拉取
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b
ollama pull nomic-embed-text   # Embedding 模型（RAG 需要）

# 内网离线导入（将 ~/.ollama/models 目录复制到目标机器）
```

**验证：**

```bash
curl http://localhost:11434/api/tags
# 应返回已安装的模型列表
```

---

### 方式 C：GLM-4 / ChatGLM（智谱 AI 本地部署）

GLM 系列模型提供 OpenAI 兼容接口，可直接用 vLLM 托管：

```bash
# 下载模型（需要 HuggingFace 或 ModelScope）
# ModelScope（国内）：
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('ZhipuAI/glm-4-9b-chat', local_dir='/models/glm-4-9b')"

# 使用 vLLM 启动
python -m vllm.entrypoints.openai.api_server \
    --model /models/glm-4-9b \
    --served-model-name glm-4-9b \
    --host 0.0.0.0 \
    --port 8001 \
    --trust-remote-code \
    --api-key your-internal-api-key
```

---

## 四、Odoo 后台配置 Provider

### 4.1 进入配置菜单

**AI → 配置 → 提供商（Providers）→ 新建**

### 4.2 配置 OpenAI 协议 Provider（接入 vLLM/DeepSeek/GLM-4）

| 字段 | 值 | 说明 |
|------|-----|------|
| 名称 | `DeepSeek-内网` | 显示名称，随意填写 |
| 服务 | `OpenAI` | 选择 OpenAI 协议 |
| API 密钥 | `your-internal-api-key` | 与 vLLM 启动时设置的一致 |
| API Base URL | `http://192.168.1.100:8000/v1` | ⚠️ 必填，内网 vLLM 地址 |

> **重要：** `API Base URL` 必须填写，否则 SDK 会尝试连接外网 `api.openai.com`。

### 4.3 配置 Ollama Provider

| 字段 | 值 |
|------|-----|
| 名称 | `Ollama-本地` |
| 服务 | `Ollama` |
| API Base URL | `http://localhost:11434`（或内网 Ollama 服务器地址） |
| API 密钥 | （留空，Ollama 不需要） |

### 4.4 配置多个 Provider（推荐）

建议同时配置一个**对话模型** Provider 和一个**Embedding 模型** Provider：

```
Provider 1：主力对话模型
  服务：OpenAI
  API Base：http://192.168.1.100:8000/v1
  用途：日常对话、工具调用

Provider 2：Embedding 模型（RAG 使用）
  服务：Ollama
  API Base：http://localhost:11434
  用途：文档向量化
```

---

## 五、配置 AI 模型

### 5.1 同步模型列表

在 Provider 详情页，点击 **"同步模型（Sync Models）"** 按钮，框架会自动从推理服务拉取可用模型并注册到 `llm.model`。

若 vLLM 返回正确的模型列表，稍等片刻后刷新页面即可看到模型。

### 5.2 手动创建模型（同步失败时）

**AI → 配置 → 模型 → 新建：**

| 字段 | 示例值 | 说明 |
|------|-------|------|
| 名称（技术名） | `deepseek-r1-7b` | 必须与推理服务的模型名一致 |
| 提供商 | `DeepSeek-内网` | 选择对应 Provider |
| 用途 | `对话（Chat）` | chat / embedding / multimodal |
| 设为默认 | ✅ | 该类型的默认选择 |
| 激活 | ✅ | |

### 5.3 模型用途说明

| 用途值 | 使用场景 | 典型模型 |
|--------|---------|---------|
| `chat` | 对话、工具调用、文本生成 | DeepSeek-R1、GLM-4、Qwen2.5 |
| `embedding` | 知识库向量化（RAG） | nomic-embed-text、bge-m3 |
| `multimodal` | 图文理解（需模型支持） | Qwen2.5-VL |

---

## 六、配置 AI 助手（Assistant）

助手是 AI 能力的核心配置入口，将 Provider、模型、工具和提示词组合在一起。

### 6.1 创建助手

**AI → 助手 → 新建：**

| 字段 | 说明 |
|------|------|
| 名称 | 助手显示名称 |
| 提供商 | 选择已配置的 Provider |
| 模型 | 选择 chat 类型模型 |
| 系统提示词 | AI 的行为指令（支持 Jinja2 模板） |
| 工具 | 勾选允许 AI 调用的工具 |

### 6.2 系统提示词模板变量

在系统提示词中可使用以下 Jinja2 变量：

```jinja2
你是一个专业的 Odoo 业务助手。

系统信息：
- 当前日期：{{ current_date }}
- 当前用户：{{ user.name }}
- 所在公司：{{ company.name }}

{% if related_record %}
当前业务记录：
- 模型：{{ related_model }}
- 名称：{{ related_record.display_name }}
- ID：{{ related_res_id }}
{% endif %}

请用中文回答，保持专业简洁。
```

### 6.3 为助手配置工具

在助手编辑页面的 **工具** 标签页，勾选需要开放给 AI 的工具。

建议按业务场景划分多个助手：

| 助手名称 | 开放工具 | 适用场景 |
|---------|---------|---------|
| 销售助手 | 订单查询、客户搜索 | 销售团队 |
| 财务助手 | 账户余额、发票查询 | 财务团队 |
| 通用助手 | 基础查询工具 | 所有用户 |

---

## 七、知识库（RAG）配置

让 AI 能够检索公司内部文档，实现智能问答。

### 7.1 激活 pgvector

在 PostgreSQL 服务器上：

```bash
# Ubuntu/Debian 安装 pgvector
sudo apt install -y postgresql-16-pgvector

# 或从源码编译
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

在数据库中激活扩展：

```sql
-- 以 postgres 超级用户连接数据库执行
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 7.2 配置向量存储

**AI → 配置 → 向量存储 → 新建：**

| 字段 | 值 |
|------|-----|
| 名称 | `内部知识库` |
| 类型 | `pgvector` |
| Embedding 提供商 | 选择配置了 embedding 模型的 Provider |
| Embedding 模型 | 选择 embedding 类型的模型 |

> **推荐 Embedding 模型：**
> - Ollama：`nomic-embed-text`（768 维，中英文均可）
> - vLLM：`BAAI/bge-m3`（1024 维，中文效果更好）
>
> 在 Ollama 中预先拉取：`ollama pull nomic-embed-text`

### 7.3 创建知识集合（Collection）

**AI → 知识库 → 知识集合 → 新建：**

| 字段 | 值 |
|------|-----|
| 名称 | `产品手册` |
| 向量存储 | 选择上一步创建的向量存储 |
| 描述 | 说明该集合包含的内容 |

### 7.4 上传文档

**AI → 知识库 → 资源 → 上传文件：**

支持的文件格式：
- PDF（需要 `PyMuPDF`）
- Word（.docx）
- 纯文本（.txt）
- Markdown（.md）

上传后，资源会经历以下处理流程：

```
上传 → draft（待处理）
     → retrieved（已获取内容）
     → parsed（已解析为文本）
     → chunked（已分块）
     → ready（已生成向量，可检索）
```

处理时间取决于文档大小和 Embedding 模型速度，可在资源详情页查看当前状态。

### 7.5 在助手中启用知识库检索

安装 `llm_tool_knowledge` 模块后，在助手的工具列表中会出现 **knowledge_search** 工具，勾选后 AI 即可检索知识库。

---

## 八、生产环境优化

### 8.1 Nginx 反向代理配置（流式响应支持）

```nginx
# /etc/nginx/sites-available/odoo
upstream odoo {
    server 127.0.0.1:8069;
}

upstream odoochat {
    server 127.0.0.1:8072;
}

server {
    listen 443 ssl http2;
    server_name odoo.your-company.internal;

    ssl_certificate     /etc/ssl/odoo/cert.pem;
    ssl_certificate_key /etc/ssl/odoo/key.pem;

    # ── AI 流式响应（Server-Sent Events）──
    location /web/llm/ {
        proxy_pass http://odoo;
        proxy_buffering off;        # ⚠️ 必须关闭，否则流式输出会卡顿
        proxy_cache off;
        proxy_read_timeout 300s;    # AI 响应可能较长，增加超时
        proxy_send_timeout 300s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ── 普通 HTTP 请求 ──
    location / {
        proxy_pass http://odoo;
        proxy_read_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # ── WebSocket（Odoo 实时通知）──
    location /websocket {
        proxy_pass http://odoochat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }

    # ── 静态文件 ──
    location ~* /web/static/ {
        proxy_pass http://odoo;
        proxy_cache_valid 200 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name odoo.your-company.internal;
    return 301 https://$host$request_uri;
}
```

### 8.2 Odoo 配置文件优化

```ini
# /etc/odoo/odoo.conf
[options]
; 数据库
db_host = localhost
db_port = 5432
db_user = odoo
db_password = your_db_password
db_name = your_database

; addons 路径
addons_path = /opt/odoo/odoo/addons,
              /opt/odoo/addons,
              /opt/odoo/addons/odoo-llm

; 性能：Worker 进程数 = CPU 核心数 × 2 + 1
workers = 9
; 长轮询 Worker（WebSocket/SSE 连接）
longpolling_port = 8072

; 内存限制（防止 AI 处理大文档时 OOM）
limit_memory_hard = 4294967296   ; 4 GB
limit_memory_soft = 2147483648   ; 2 GB
limit_time_cpu = 600             ; AI 推理可能耗时较长
limit_time_real = 1200

; 日志
logfile = /var/log/odoo/odoo.log
log_level = info

; 安全
proxy_mode = True                ; 启用了 Nginx 代理时必须设置
```

### 8.3 PostgreSQL 向量索引优化（RAG 性能）

```sql
-- 为向量字段创建 IVFFlat 索引（适合大规模检索）
-- 在 odoo 数据库中执行

-- 查找向量字段所在表（通常是 llm_resource_chunk 类似的表）
\d+ llm*

-- 创建近似最近邻索引（文档量超过 10 万 chunk 时推荐）
CREATE INDEX CONCURRENTLY idx_chunk_embedding
ON llm_resource_chunk USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 设置查询时的探测列表数（精度与速度的平衡）
SET ivfflat.probes = 10;
```

### 8.4 AI 推理服务调优（vLLM）

```bash
# 生产环境 vLLM 启动参数
python -m vllm.entrypoints.openai.api_server \
    --model /models/deepseek-r1-7b \
    --served-model-name deepseek-r1-7b \
    --host 0.0.0.0 \
    --port 8000 \
    --api-key your-internal-api-key \
    --max-model-len 16384 \
    --max-num-seqs 32 \          # 最大并发请求数
    --gpu-memory-utilization 0.9 \  # GPU 内存利用率
    --dtype float16 \
    --enable-chunked-prefill \   # 提升长文本处理速度
    --trust-remote-code
```

### 8.5 定时清理过期对话

在 Odoo 系统参数中配置：

```
# AI → 配置 → 系统参数
llm.thread.auto_delete_days = 90   # 90 天后归档对话
```

或通过计划任务清理：

```python
# 在 ir.cron 中添加定时任务（每月执行）
self.env["llm.thread"].search([
    ("create_date", "<", fields.Datetime.now() - timedelta(days=90)),
    ("message_ids", "=", False),  # 空对话
]).unlink()
```

---

## 九、验证与测试

### 9.1 基础连通性测试

```bash
# 1. 测试 vLLM 服务可达
curl http://192.168.1.100:8000/v1/models \
  -H "Authorization: Bearer your-internal-api-key"

# 2. 测试 Ollama 服务可达
curl http://localhost:11434/api/tags

# 3. 测试对话功能
curl http://192.168.1.100:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-internal-api-key" \
  -d '{
    "model": "deepseek-r1-7b",
    "messages": [{"role": "user", "content": "你好，请介绍一下你自己"}],
    "stream": false
  }'
```

### 9.2 Odoo 内功能验证

**步骤 1：在 Odoo 中发起对话**

1. 进入 **AI → 助手 → 对话**
2. 选择已配置的助手
3. 发送消息："你好，请告诉我今天的日期"
4. 预期：AI 返回正确响应，无报错

**步骤 2：验证工具调用**

1. 在对话中输入："帮我查询最新的 10 条销售订单"
2. 预期：AI 调用工具并返回订单数据

**步骤 3：验证知识库检索（若已配置 RAG）**

1. 上传一份包含特定内容的 PDF
2. 等待状态变为 `ready`
3. 在对话中提问 PDF 中的内容
4. 预期：AI 引用文档内容回答

### 9.3 确认无外网请求（安全验证）

```bash
# 在 Odoo 服务器上监控网络连接
# 发起一次 AI 对话，同时观察是否有外网连接

# 方法1：实时监控
watch -n 1 "ss -tnp | grep $(pgrep -f odoo) | grep -v '127.0.0.1\|192.168'"

# 方法2：tcpdump 抓包（确认只有内网流量）
tcpdump -i any -n 'host not 192.168.0.0/16 and host not 127.0.0.1' \
  and port not 443 and port not 80

# 方法3：检查防火墙日志
journalctl -u ufw --since "5 minutes ago" | grep BLOCK
```

---

## 十、故障排查

### 10.1 模块安装失败

**现象：** 安装 `llm` 模块时报错

**排查：**

```bash
# 查看 Odoo 日志
tail -f /var/log/odoo/odoo.log | grep -E "ERROR|CRITICAL|llm"

# 常见原因1：Python 依赖缺失
pip show openai pydantic jinja2

# 常见原因2：addons_path 未正确配置
grep addons_path /etc/odoo/odoo.conf

# 常见原因3：权限问题
ls -la /opt/odoo/addons/odoo-llm/llm/__manifest__.py
```

### 10.2 Provider 连接失败（无法同步模型）

**现象：** 点击"同步模型"后报错或无响应

**排查：**

```bash
# 在 Odoo 服务器上测试 Provider 连通性
curl -v http://192.168.1.100:8000/v1/models \
  -H "Authorization: Bearer your-api-key"

# 检查防火墙是否允许 Odoo 服务器访问推理服务
telnet 192.168.1.100 8000
```

**常见原因：**
- `api_base` 填写了尾部带 `/` 的地址（应为 `http://host:port/v1`，不要加 `/`）
- vLLM 服务未启动或绑定了不同端口
- 防火墙拦截了 Odoo 到推理服务器的请求

### 10.3 AI 对话无响应/超时

**现象：** 发送消息后 Loading 一直转，最终超时

**排查：**

```bash
# 查看 Odoo worker 日志
tail -f /var/log/odoo/odoo.log | grep -E "timeout|TimeoutError|ConnectionError"

# 检查 Nginx 超时配置
grep proxy_read_timeout /etc/nginx/sites-enabled/odoo

# 检查推理服务响应时间
time curl -X POST http://192.168.1.100:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-key" \
  -d '{"model":"deepseek-r1-7b","messages":[{"role":"user","content":"hi"}]}'
```

### 10.4 流式响应不实时（整段输出）

**现象：** AI 回复不是逐字流出，而是等待完成后一次性显示

**原因：** Nginx `proxy_buffering` 未关闭

**解决：**

```nginx
location /web/llm/ {
    proxy_pass http://odoo;
    proxy_buffering off;   # ← 确保这行存在且未被覆盖
    proxy_cache off;
}
```

重载 Nginx：`sudo nginx -s reload`

### 10.5 RAG 文档处理卡在某个状态

**现象：** 知识资源一直停留在 `parsed` 或 `chunked` 状态

**排查：**

```bash
# 查看是否有 Embedding 相关错误
tail -f /var/log/odoo/odoo.log | grep -iE "embed|vector|pgvector"

# 检查 pgvector 扩展是否激活
psql -d your_database -c "SELECT * FROM pg_extension WHERE extname='vector';"

# 检查 Embedding 模型是否可用
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}'
```

### 10.6 工具注册后找不到

**现象：** 添加了 `@llm_tool` 方法但在后台工具列表中看不到

**解决：**

```bash
# 更新模块以重新注册工具
odoo-bin -d your_database -u your_module --stop-after-init

# 检查日志中是否有工具注册信息
grep -i "llm_tool\|decorator" /var/log/odoo/odoo.log
```

---

## 附录：内网部署检查清单

### 安装阶段

- [ ] Python 依赖已安装（`openai`、`ollama`、`pgvector`、`numpy` 等）
- [ ] `addons_path` 已包含 `odoo-llm` 目录
- [ ] Odoo 重启后模块列表中可见 `llm` 相关模块
- [ ] 已安装最小化模块集（`llm` + `llm_thread` + `llm_tool` + `llm_assistant`）
- [ ] 已安装 AI 接入模块（`llm_openai` 或 `llm_ollama`）

### 配置阶段

- [ ] Provider 已创建，`API Base URL` 填写内网地址（非空！）
- [ ] 点击"同步模型"成功，可看到模型列表
- [ ] 至少一个 `chat` 类型模型已配置并设为默认
- [ ] AI 助手已创建，关联了 Provider 和模型
- [ ] 助手的系统提示词已填写

### RAG（若启用）

- [ ] `pgvector` 扩展已在 PostgreSQL 中激活
- [ ] `llm_store` + `llm_pgvector` 模块已安装
- [ ] 向量存储配置了 Embedding Provider 和模型
- [ ] 测试文档上传，状态最终变为 `ready`

### 安全阶段

- [ ] 所有 Provider 的 `API Base URL` 指向内网地址
- [ ] 服务器出站防火墙规则已配置（只允许访问内网 AI 服务）
- [ ] 已确认 Odoo 服务器无法直接访问外网 AI 服务
- [ ] 未安装 `llm_anthropic`、`llm_mistral`、`llm_fal_ai`、`llm_letta`、`llm_replicate` 等外网模块

### 生产阶段

- [ ] Nginx `proxy_buffering off` 已配置（流式响应）
- [ ] Nginx `proxy_read_timeout` 设置为 300s+
- [ ] Odoo workers 数量已根据 CPU 核心数调整
- [ ] vLLM/Ollama 已配置为系统服务（systemd）并设为开机自启

---

*参考资源：*
- *[apexive/odoo-llm GitHub](https://github.com/apexive/odoo-llm)*
- *[vLLM 官方文档](https://docs.vllm.ai)*
- *[Ollama 官方文档](https://ollama.com/docs)*
- *[pgvector GitHub](https://github.com/pgvector/pgvector)*
