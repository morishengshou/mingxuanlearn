## 5.1 推荐架构

```text
                    现有任务下发系统
                     │         ▲
             下发任务│         │原始结果回传
                     ▼         │
┌──────────────── Windows 执行机 ────────────────┐
│                                               │
│  现有 Flask 测试 Agent                        │
│          │                                    │
│          ▼                                    │
│  测试框架 → Android 设备                       │
│          │                                    │
│          ▼                                    │
│  Collector：结果标准化、日志归档、断网补传      │
│                                               │
│  可选：部署独立 AI Review Worker               │
└──────────┬────────────────────────────────────┘
           │标准结果＋制品清单
           ▼
┌──────────────── 业务中心 ─────────────────────┐
│                                               │
│  Odoo18                                       │
│  ├─ 批次、执行记录、复核任务                    │
│  ├─ 问题库、签名、复用规则                      │
│  ├─ 特性状态汇总                               │
│  ├─ 报告、人工审批、审计                        │
│  └─ MCP 业务工具                               │
│                                               │
│  共享制品存储：日志、截图、tombstone 等          │
└───────────────▲───────────────────────────────┘
                │MCP
                ▼
┌──────────── 独立 AI Review Worker ─────────────┐
│                                               │
│  工作流控制器                                  │
│     ├─ 领取任务、续租、恢复                      │
│     ├─ 读取证据、检索历史问题                    │
│     ├─ AgentPort → 可替换 AI 实现               │
│     ├─ 校验结构化分析结果                        │
│     └─ 经 MCP 提交复核与发布请求                 │
└───────────────────────────────────────────────┘
```

### Worker 部署位置

同一套 Worker 支持：

- **集中部署**：运行于独立服务器。
- **分布部署**：运行于各 Windows 执行机。

建议优先集中部署，因为首期只分析已上传证据，不依赖现场设备。

如果日志暂时不能集中存储，可以先在 Windows 上部署 Worker，但**共享问题库和可共享证据不能只放在本机路径下**。

无论部署在哪里，都不建议把 LLM 长任务直接放进现有 Flask 请求或 Odoo Web 请求。

## 5.2 三类 Agent 必须区分

| 名称 | 职责 |
|---|---|
| 测试 Agent | 现有 Flask 服务，启动测试 |
| Review Worker | 确定性程序，调度 AI 复核、重试、调用 MCP |
| AI Agent | 阅读证据并产生结构化分析建议，可替换 |

**启动复核的应是可靠事件和 Worker，不是让大模型判断“现在要不要启动”。**

## 5.3 设计模式

| 变化点 | 设计方式 | 具体用途 |
|---|---|---|
| AI Agent 替换 | 策略模式＋适配器模式 | 将不同 Agent 包装为统一 `AgentPort` |
| 测试框架替换 | 适配器模式 | 各框架输出转换成统一执行记录 |
| 插件选择 | 工厂／注册表 | 通过配置选择具体实现 |
| 分析核心与外围系统隔离 | 六边形架构 | 业务核心依赖接口，不依赖 SDK |
| 看板访问 | 门面＋适配器 | Worker 只使用 `BoardPort` |
| 长流程执行 | 持久化状态机 | 中断后从检查点恢复 |
| 重复通知处理 | 幂等收件箱／发件箱 | 允许至少一次投递 |
| 特性汇总 | 确定性策略 | 汇总规则可配置，但不由 AI 临时发明 |

### 端口示意

以下为**概念接口，不是已验证的第三方 SDK 调用代码**：

```python
from typing import Protocol

class AgentPort(Protocol):
    async def analyze(
        self,
        request: "AnalysisRequest",
        tools: "ReadOnlyToolBroker",
    ) -> "AnalysisResult":
        ...

class TestResultAdapter(Protocol):
    def normalize(
        self,
        source: "FrameworkOutput",
    ) -> "NormalizedRun":
        ...

class BoardPort(Protocol):
    async def claim_job(self, request: "ClaimRequest") -> "JobLease":
        ...

    async def search_issues(
        self,
        query: "IssueQuery",
    ) -> "IssueCandidates":
        ...

    async def submit_review(
        self,
        command: "ReviewCommand",
    ) -> "ReviewReceipt":
        ...

class ArtifactPort(Protocol):
    async def read_excerpt(
        self,
        reference: "EvidenceReference",
    ) -> "EvidenceExcerpt":
        ...
```

### 为什么不只定义一个 `run_agent()`？

因为不同 Agent 可能存在：

- 同步与异步调用差异。
- 工具调用方式差异。
- JSON 输出能力差异。
- 运行超时和取消能力差异。
- 会话与上下文保存方式差异。

这些差异必须由适配器消化，不允许泄漏到业务流程中。

## 5.4 基础设施选择

建议第一阶段：

- Odoo：业务数据、任务状态、审计。
- Python Worker：AI 分析与工作流。
- Collector：执行机采集。
- 公司现有文件／对象存储：制品。
- Odoo 持久化任务记录：任务领取、租约、状态。
- Windows 本地持久化 spool：失败补传。

**暂不增加 Redis、Celery、Kafka、独立向量库和 Kubernetes。**

这里不是说它们不能用，而是暂时没有足够规模信息证明需要。
