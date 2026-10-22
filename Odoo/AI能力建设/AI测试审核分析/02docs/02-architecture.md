# 二、总体架构与部署

建议保存为：`docs/02-architecture.md`

## 2.1 架构图

```text
现有任务下发系统
       │
       ▼
Windows Flask 测试 Agent
       │
       ▼
自研 Python 测试框架 ──────► Android 设备
       │
       ├─ 原有结果回传：保持不变
       │
       └─ 完成钩子／最后控制步骤
                    │
                    ▼
           Collector 结果采集器
            ├─ 输出标准 JSON
            ├─ 制品登记与上传
            ├─ 本地持久化补传
            └─ 提交批次封存请求
                    │
                    ▼
                Odoo18
            ├─ 既有看板业务模型
            ├─ 复核任务与审计
            ├─ 诊断知识和问题关联
            ├─ 特性汇总
            ├─ 人工确认
            └─ 报告快照
                    ▲
                    │ MCP
                    ▼
          独立 Python Review Worker
            ├─ 领取任务／续租
            ├─ 获取证据
            ├─ 检索历史诊断
            ├─ 调用可替换 Agent
            ├─ 校验结论
            └─ 提交复核结果

共享制品存储
    └─ 保存日志、截图、录像等；Odoo 保存引用和元信息
```

## 2.2 推荐部署

**默认选择：集中部署一个 Review Worker 服务。**

理由是首期不操作设备，分析过程没有必须运行在执行机上的要求。建议从一个 Worker 进程、较小并发开始测量。

但保留以下能力：

```text
同一套 Worker
    可以部署在中央服务器
    也可以部署在 Windows 执行机
```

部署位置不影响业务接口和问题复用机制。

如果暂时没有共享存储，可以先采用：

```text
Windows Collector
    → 上传到公司现有文件服务器
    → Worker 通过受控接口读取
```

不要让其他执行机依赖某台 Windows 的本地绝对路径。

## 2.3 四个核心隔离接口

| 接口 | 隔离什么 | 推荐模式 |
|---|---|---|
| `TestResultAdapter` | 自研测试框架及未来替换框架 | 适配器模式 |
| `AgentPort` | 不同 AI Agent 实现 | 策略＋适配器模式 |
| `ModelPort` | 不同模型服务 | 适配器模式 |
| `BoardPort` | MCP 客户端与看板业务交互 | 门面＋适配器模式 |

还应保留：

- `ArtifactPort`：制品存储。
- `KnownIssuePort`：外部问题系统。
- `DashboardBridge`：现有 Odoo 模型映射。

### Agent 与模型分开替换

两者不是同一个变化点：

```text
Agent：
    如何组织检索、阅读证据、调用工具和输出结论。

模型：
    实际使用哪个推理服务。
```

首期推荐：

> **受限工具循环的单 Agent＋确定性工作流，不引入多 Agent 协作框架。**

Agent 可以按需读取更多日志，但只允许使用只读工具。写入和发布由 Worker 的确定性代码执行。

## 2.4 Odoo 模块划分

```text
smoke_ai_core
    复核任务、复核记录、诊断知识、规则、报告快照
    不依赖 Apexive 或模型 SDK

smoke_ai_ingest
    Collector 接入、批次封存、制品登记

smoke_ai_mcp
    Apexive 工具注册与调用边界

smoke_ai_dashboard_bridge
    扩展你现有看板模型

smoke_ai_demo
    仅开发／测试使用的假业务数据与演示映射
```

`smoke_ai_demo` 不作为生产业务模型替代品。