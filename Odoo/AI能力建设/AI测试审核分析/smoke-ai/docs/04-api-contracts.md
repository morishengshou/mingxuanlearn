## 7.1 Odoo 与 Apexive 的接入建议

我检查了 Apexive 的 `odoo-llm` 项目：

- 存在 `18.0` 分支和 `llm_mcp_server` 模块。
- README 描述了 `/mcp`、Bearer API Key、工具发现和调用。
- 本次读取的 manifest 声明依赖 `base`、`llm`、`llm_tool`、`web_json_editor`，以及 Python `mcp` 包。不能只按 README 的简化依赖清单安装。([raw.githubusercontent.com](https://raw.githubusercontent.com/apexive/odoo-llm/18.0/llm_mcp_server/README.md))
- `llm_tool` 文档提供装饰器及 XML 配置两种工具扩展方式，同时存在通用记录修改、删除和模型方法执行能力。([raw.githubusercontent.com](https://raw.githubusercontent.com/apexive/odoo-llm/18.0/llm_tool/README.md))

因此建议：

```text
smoke_ai_core
    纯业务模型、服务、规则
    不依赖 Apexive

smoke_ai_mcp
    依赖 Apexive 的 llm_mcp_server / llm_tool
    注册受限的冒烟业务工具

smoke_ai_dashboard_bridge
    连接你已经存在的看板模型和页面
```

这样未来更换 MCP 实现时，不必重写冒烟业务。

**不要因为模块名称带 MCP，就认为与所有客户端天然兼容。**需要锁定实际 commit、依赖版本，并测试初始化、协议协商、工具调用和断线恢复。MCP 的 HTTP 传输、会话和协议版本处理有明确要求；这些应作为兼容性验证项。([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports))

如果 Apexive 的依赖或兼容性不符合你现有项目，可以改用独立 Python MCP 服务连接 Odoo 业务服务；官方 Python SDK 提供客户端和服务端能力。它应作为备用适配方式，而不是首期同时维护两套服务。([github.com](https://github.com/modelcontextprotocol/python-sdk))

## 7.2 接口分类

建议区分：

### A. 系统接入 API

面向 Collector 和任务系统：

- 创建批次。
- 导入执行记录。
- 登记制品。
- 封存批次输入。
- 查询补传状态。

它们不必使用 MCP，可以使用你们现有的鉴权 HTTP API。

### B. AI／Worker MCP 工具

面向复核流程：

| 工具名，拟定 | 功能 | 调用权限 |
|---|---|---|
| `smoke_get_context` | 查询批次、用例、特性和环境上下文 | 读 |
| `smoke_get_evidence` | 读取授权的证据片段 | 读 |
| `smoke_search_issues` | 查询相同或相似问题 | 读 |
| `smoke_claim_review_job` | 领取复核任务 | Worker |
| `smoke_renew_review_lease` | 续租 | Worker |
| `smoke_create_or_link_issue` | 原子创建问题或关联已有问题 | 受控写 |
| `smoke_mark_case_result` | 提交某次执行的复核结果 | 受控写 |
| `smoke_generate_report` | 按快照生成结构化报告 | 受控写 |
| `smoke_publish_report` | 发布报告 | 审批／发布角色 |

这覆盖了你提出的四类接口，同时补齐了实际运行必需的上下文、证据和任务能力。

## 7.3 不建议让 LLM 直接持有发布权限

推荐调用链：

```text
AI Agent
  ├─ 可查询上下文
  ├─ 可读取证据
  ├─ 可搜索已知问题
  └─ 输出 AnalysisResult
             │
             ▼
       Worker 校验和策略判断
             │
             ▼
       MCP 受控写入
             │
             ▼
       Odoo 再次校验并落库
```

即使 Agent 更换为权限更强的实现，也不能绕过服务端规则。

## 7.4 所有写操作的公共要求

建议包含：

```json
{
  "schema_version": "1.0",
  "idempotency_key": "由调用方稳定生成的操作标识",
  "run_id": "批次外部标识",
  "attempt_id": "执行外部标识",
  "expected_revision": 3,
  "lease_token": "服务端签发的任务租约标识"
}
```

约束：

- `idempotency_key` 绑定调用主体、操作类型和请求摘要。
- 同一 key、相同内容：返回原结果。
- 同一 key、不同内容：返回冲突，不能静默成功。
- `expected_revision` 防止覆盖较新的人工结果。
- `lease_token` 绑定任务、Worker、租约代次与期限，拒绝过期 Worker。
- 产品、批次、执行之间的关系必须由服务端校验，不能相信调用方提交的 ID 组合。

## 7.5 标记用例复核结果

拟定输入：

```json
{
  "schema_version": "1.0",
  "idempotency_key": "review-attempt-001-generation-1",
  "run_id": "RUN-EXAMPLE",
  "attempt_id": "ATTEMPT-001",
  "expected_revision": 0,
  "lease_token": "LEASE-EXAMPLE",
  "analysis": {
    "category": "PRODUCT_DEFECT",
    "proposed_verdict": "FAIL",
    "confidence": 0.91,
    "summary": "目标进程在验证阶段发生崩溃，导致用例断言失败。",
    "evidence": [
      {
        "artifact_id": "ART-001",
        "line_start": 120,
        "line_end": 136,
        "excerpt_hash": "sha256:EXAMPLE"
      }
    ],
    "issue_id": "ISSUE-001",
    "missing_evidence": [],
    "alternative_hypotheses": []
  }
}
```

上述为合成示例，不代表真实问题。

返回结果建议明确区分“已存建议”和“已生效”：

```json
{
  "ok": true,
  "review_id": "REVIEW-001",
  "stored": true,
  "applied": false,
  "effective_verdict": "NEEDS_REVIEW",
  "approval_state": "PENDING",
  "revision": 1,
  "reason_code": "SHADOW_MODE"
}
```

不能只返回 `success: true`，让调用方误以为已经更新正式看板。

## 7.6 问题查询与创建

查询应返回：

- 问题 ID、状态、标题。
- 签名匹配方式。
- 适用产品、模块和版本范围。
- 首次／最近出现版本。
- 修复版本。
- 是否经过人工确认。
- 支持复用的关键证据条件。
- 排除条件。
- 可读取的历史证据引用。

创建问题必须记录：

```text
问题描述
问题类别
当前结论：候选／确认
影响特性
责任团队候选
关键日志引用
诊断签名
签名算法版本
适用范围
排除条件
首次出现的执行记录
```

其中：

> “责任团队候选”可以由 AI 建议；正式归属优先按特性与团队映射决定。

## 7.7 生成报告

建议参数：

```text
run_id
expected_run_revision
template_version
mode = draft | final
```

返回：

```text
report_id
snapshot_revision
report_status
structured_report
rendered_attachment_id
```

设计原则：

- 数量和状态由服务端计算。
- AI 只能提供受约束的摘要、风险解释和建议。
- 最终报告必须标明是否还有未完成复核。
- 有迟到日志或人工更正时生成新版本，不篡改已发布快照。
- 不因达到日报时间就将未完成项自动判为通过。
