*Thinking...*

> **Clarifying skill recommendations**
> 
> I need to clarify what "skill" refers to — maybe it’s about Claude skills? The user is asking for high-quality skill recommendations specifically related to SELinux rule auditing. Since "skill" is a bit ambiguous, I think it’s important to search the web for current recommendations. It could mean something like Agent Skill found on skills.sh. So, searching online seems like the best approach to get accurate and updated information!
> 
> **Exploring tools for inspection**
> 
> I'm looking into the selinux-policy-auditor tool and wondering how best to inspect it further. I think I should check GitHub to find more detailed information and possibly explore other tools, even though I’m not entirely sure what skills I might need for this. It's exciting to think about diving deeper, but I want to ensure I’m thorough in my search and not missing anything important!
> 
> **Evaluating security tools**
> 
> I need to distinguish between Linux and Android for my recommendations. First, I think SETools MCP is a solid foundation, though it’s not exactly a skill itself. Then, I could suggest creating a custom SELinux Policy Review skill that combines selint, setools, checkpolicy/secilc, and audit2why. Another good option is the Cloudflare security-audit skill, but it needs some customization. For AOSP, I'll mention the jonaschen L2 skill as a beta option, and share a practical audit workflow.

有，但**目前专门用于“SELinux 规则审核”的成熟 Agent Skill 很少**。更靠谱的方案是：用 SELinux 官方分析工具作为事实依据，再用 Skill 编排审核流程，而不是让模型直接凭经验判断规则。

## 推荐顺序

### 1. SETools + `setools-mcp`：最值得推荐

SETools 是 SELinuxProject 官方维护的策略分析工具集，包含：

- `sesearch`：查询 `allow`、`type_transition` 等规则
- `seinfo`：查看类型、属性、角色和布尔值
- `sediff`：比较两个编译策略的语义差异
- `sedta`：分析 domain transition
- `seinfoflow`：分析信息流
- `sechecker`：自动化策略检查
- **`setools-mcp`**：直接向 LLM 提供策略分析能力

它不是传统的 `SKILL.md`，但实际上比大部分社区 Skill 更适合做高可信审核，因为结论来自编译后的策略，而不是模型猜测。([github.com](https://github.com/SELinuxProject/setools))

**适合：**

- 检查某个 domain 实际拥有的权限
- 展开 attribute、interface 后分析最终授权
- 查找跨域访问路径
- 比较策略修改前后的权限增量
- 给 Claude Code、Codex 等 Agent 接入真实策略查询能力

**推荐程度：★★★★★**

---

### 2. SELint：源代码级规则审核必备

SELint 是 SELinuxProject 维护的静态分析工具，专门检查 refpolicy 风格的 `.te`、`.if` 等策略源文件，支持错误、警告、风格和 convention 等不同级别的检查。([github.com](https://github.com/SELinuxProject/selint))

例如：

```bash
selint -r -s --fail .
```

适合检查：

- 错误或不规范的 interface 使用
- `optional_policy`、`require` 等结构问题
- 冗余或可疑 AV rule
- 未使用的 interface/template
- refpolicy 风格和维护性问题

它非常适合作为一个 Agent Skill 的第一阶段：

```text
1. 编译检查
2. SELint 静态检查
3. SETools 语义分析
4. 权限增量与攻击面分析
5. 输出可验证的整改建议
```

**推荐程度：★★★★★**

---

### 3. Cloudflare `security-audit-skill`：适合作为审核框架改造

Cloudflare 的通用安全审计 Skill 有比较完整的多阶段流程，包括侦察、漏洞搜索、独立验证、结构化报告和二次复核，并强调“没有具体攻击场景就不报告漏洞”。([github.com](https://github.com/cloudflare/security-audit-skill))

安装：

```bash
npx skills add https://github.com/cloudflare/security-audit-skill \
  --skill security-audit
```

但它**并不原生理解 SELinux policy**。比较好的用法是 fork 后增加专门阶段：

- 调用 `selint`
- 调用 `checkmodule` / `secilc`
- 调用 `sesearch`、`seinfoflow`、`sediff`
- 检查新增权限是否突破 trust boundary
- 验证 `neverallow`
- 区分“真实安全问题”和“仅仅缺少纵深防御”

**推荐程度：★★★★☆，但需要二次开发**

---

### 4. AOSP/SEAndroid：`L2-security-selinux-expert`

如果审核对象是 Android/AOSP，可以看看 `jonaschen/Android-Software` 中的：

```text
L2-security-selinux-expert
```

它覆盖：

- `avc: denied`
- 新 daemon domain
- `neverallow` 违规
- `property_contexts`
- AOSP/vendor policy 路径

项目带有路由测试和 Skill lint，不过当前定位仍偏 Beta，而且主要用于 Android 15/AOSP 集成，不适合直接审核普通 RHEL/Fedora SELinux policy。([github.com](https://github.com/jonaschen/Android-Software))

**推荐程度：**

- AOSP：★★★★☆
- 通用 Linux：★★☆☆☆

---

### 5. `selinux-agent-confinement`：场景较窄，谨慎使用

这个社区 Skill 主要用于给 Claude Code、Aider、OpenCode 等 AI Agent 编写 SELinux 隔离策略，而不是进行全面规则审核。它围绕 process domain、entrypoint type 和 workspace type 构建策略。([skillsmp.com](https://skillsmp.com/creators/wargloom/opencode-selinux/claude-skills-selinux-agent-confinement))

安装：

```bash
npx skills add https://github.com/WarGloom/opencode-selinux \
  --skill selinux-agent-confinement
```

问题是：

- 场景非常专一
- 项目采用率和外部验证较少
- 一些表述偏模板化，不能作为通用 SELinux 设计原则
- 更擅长“生成策略”，不擅长证明策略是最小权限的

**推荐程度：★★★☆☆，只适合 AI Agent confinement**

---

## 可作为补充的运行时工具

`selinux-policy-auditor` 是一个较新的实验性项目，通过 eBPF/LSM 观察运行时实际使用的 SELinux 权限，尝试识别“策略允许但工作负载实际上没有使用”的权限。([reddit.com](https://www.reddit.com/r/linuxadmin/comments/1qmchua/update_i_built_selinuxpolicyauditor_a_high/?utm_source=openai))

它的思路很有价值，但要注意：

- 未观察到不代表不需要
- 审核质量取决于 workload 覆盖率
- 异常路径、升级路径、灾难恢复路径很容易漏测
- 更适合作为权限裁剪候选生成器，不能自动删除规则

因此应和 SETools 静态分析、测试用例及人工复核结合。

---

## 我的实际建议

如果你的目标是生产级审核，我会采用下面的组合：

```text
SELinux Audit Skill
├── checkmodule / secilc       # 语法、编译、neverallow
├── SELint                     # 源代码静态检查
├── SETools / setools-mcp
│   ├── sesearch               # 最终授权
│   ├── seinfo                 # 类型和属性展开
│   ├── sediff                 # 权限增量
│   ├── sedta                  # 域转换
│   └── seinfoflow             # 信息流
├── ausearch / audit2why       # 运行时拒绝分析
├── eBPF runtime observation   # 未使用权限候选
└── Agent independent review  # 独立复核
```

审核报告至少应该分别输出：

1. **确定存在的越权**
2. **高风险但需要业务确认的授权**
3. **疑似未使用权限**
4. **策略可维护性问题**
5. **AVC denial 和功能问题**
6. **建议删除或收紧规则后的验证命令**

另外，不建议设计成“读取 AVC 后直接执行 `audit2allow`”。`audit2allow` 的职责是从 AVC 生成允许规则，不等于证明这些权限符合最小权限原则；官方工具链也将 `audit2why` 和策略分析工具作为不同用途的组件。([github.com](https://github.com/SELinuxProject/selinux/wiki/Tools?utm_source=openai))

**结论：如果只选一个基础，我推荐 `setools-mcp`；如果要真正做成高质量 Skill，推荐以 `SELint + SETools + sediff + 独立复核` 自建一个专用 Skill。**