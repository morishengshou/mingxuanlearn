**Odoo Agent Pro Kit 是一套面向 Odoo 二次开发的开源 AI 编程工具包**。你可以把它理解为：给 Claude Code、Cursor 等 AI 编程助手配上“Odoo 开发规范、项目上下文和标准工作流程”，让它们不只是生成代码，还能按步骤分析需求、开发模块、执行测试。它支持 Odoo 17、18、19，项目由 VPerfectCS 团队维护，并非 Odoo 官方内置功能。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit?utm_source=openai))

## 1. 它主要解决什么问题？

它针对的是：**AI 会写 Python/XML，不等于它了解你的 Odoo 项目。** 不同 Odoo 版本的规范、已有模型和字段、模块依赖、权限规则，以及安装升级流程，都需要明确提供给 AI。

这个工具包把这些知识和操作流程打包起来，减少重复解释，以及“套错版本写法、不了解依赖就动手”的情况。它更接近一个 **AI 辅助开发框架**，而不是面向业务用户的聊天机器人。([vpcscloud.com](https://www.vpcscloud.com/blog/our-blog-1/odoo-agent-pro-kit-open-source-ai-development-odoo-17-18-19-16))

## 2. 核心功能

| 能力 | 用途 |
|---|---|
| **版本化开发规范** | 根据 Odoo 17/18/19 加载对应的编码、依赖和测试指导 |
| **实时 Odoo 上下文** | 通过 MCP 查询真实环境中的模型、字段和关系，而不只依赖模型记忆 |
| **标准开发流程** | 将需求分析、编码、测试串起来，并保留任务和文档 |
| **多种 AI 工具接入** | 提供 Claude Code、Codex、Cursor、Antigravity、VS Code Copilot、GitHub Copilot 等适配，也有 Hermes 原生插件 |
| **环境与沙箱管理** | 提供本地工作区初始化，以及隔离的 Docker Sandbox 开发会话 |  

上述能力均已列入当前仓库说明；不同工具的具体接入方式并不完全相同。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit))

截至 **2026 年 9 月 8 日**，仓库更新日志最上方记录的是 **0.6.0（2026 年 9 月 3 日）**，并明确将数量更新为 **22 个技能、5 个命令**。因此，旧介绍中“18 个技能、4 个命令”的说法已经不是当前口径。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit/blob/main/CHANGELOG.md))

## 3. 典型使用流程

它的主要命令分工是：

- **`/plan-analysis`**：分析业务需求，形成设计和任务清单。
- **`/start-coding`**：根据确认后的任务进行开发和验证。
- **`/testing`**：执行后端、前端或浏览器验证，并整理测试证据和文档。
- **`/fleet`**：协调多个任务；社区版侧重单机本地沙箱并发。([vpcscloud.com](https://www.vpcscloud.com/blog/our-blog-1/odoo-agent-pro-kit-open-source-ai-development-odoo-17-18-19-16))
- **`/rules-check-drift`**：检查项目规则文件是否与实际代码、任务状态发生偏离；这个检查是只读、建议性的，不会替你修改数据库或标记任务完成。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit/blob/main/CHANGELOG.md))

举个假设场景：你想做“采购订单超过一定金额后需要二次审批”。理想的使用方式不是直接让 AI 写完整模块，而是先让它分析现有采购模型和权限需求，确认设计，再编码，最后验证正常审批、越权操作和边界条件。

## 4. 适合谁？有哪些限制？

**比较适合已有 Odoo 开发基础、希望把 AI 纳入团队工程流程的人。** 仓库自身把主要受众定位为有一两年经验的 Odoo 开发者。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit))

需要注意：

- **不是无人审核的一键交付工具**：业务逻辑、权限、备份回滚和生产部署仍需人工审核。([vpcscloud.com](https://www.vpcscloud.com/blog/our-blog-1/odoo-agent-pro-kit-open-source-ai-development-odoo-17-18-19-16))
- **各平台验证程度不同**：Docker Sandbox 文档已有 Ubuntu KVM 验证记录，Apple Silicon 和 Windows 的流程仍属于待社区验证的候选方案。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit))
- **不同 Agent 的约束效果不同**：例如更新日志明确说明，部分检查在 Hermes 上只能提示，不能像 Claude Code 那样阻断操作。([github.com](https://github.com/infovpcs/odoo-agent-pro-kit/blob/main/CHANGELOG.md))
- **“Pro Kit”不等于整个项目收费**：公开社区代码采用 Apache-2.0；共享／远程任务调度、托管等另有商业化规划，需要区分。([vpcscloud.com](https://www.vpcscloud.com/blog/our-blog-1/odoo-agent-pro-kit-open-source-ai-development-odoo-17-18-19-16))

**我的判断：它的价值不在于“让 AI 多写几行 Odoo 代码”，而在于把 AI 开发变成可检查、可测试、可继续推进的流程。** 如果你已经在做 Odoo 定制开发，值得先拿一个小模块试用；如果你完全不懂 Odoo，它并不能替代必要的开发和业务知识。
