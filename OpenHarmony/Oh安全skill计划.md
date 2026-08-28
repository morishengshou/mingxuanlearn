*Thinking...*

> **Clarifying Hongmeng kernel details**
> 
> I'm realizing I need to browse current information about the Hongmeng kernel and clarify if it's related to OpenHarmony or SELinux. Maybe the Hongmeng kernel is associated with HDF? That could indicate it has its own security policy, so I'll need to search for that. Plus, I should craft a benchmark skill architecture that's analogous and search for primary official documents and repositories for better queries. Let's dig into this!
> 
> **Organizing project setup**
> 
> I've got a great checklist in mind! I need to ensure there's an open repository, a solid README, and comprehensive documentation. Plus, I should include checks for any necessary build scripts or tools. This way, everything is well-organized and easy to follow. I wonder if there's anything else I’m missing, like ensuring all contributors know how to use it or if I need a usage guideline. I'm curious to see how it all comes together!
> 
> **Organizing skill structure**
> 
> I need to distinguish between source evidence and inferred checks. My skill structure includes various components like SKILL.md, references, script adapters, rules, outputs, and tests fixtures. I'll make sure to outline the inputs and outputs clearly, possibly including sample command invocations and JSON schemas. For the gate policy, severity levels should block any critical or high merges. I’ll develop a verification test matrix and map out the MVP roadmap in three phases.

可以。先明确一个关键边界：

- **如果你说的是 OpenHarmony 标准系统/Linux 内核上的 MAC**，目前公开实现就是 `security_selinux_adapter`，仍然使用 SELinux 的 TE/CIL、`neverallow`、contexts 和 `policy.31`，可以直接对标前面提到的 SELinux 审核方案。
- **如果你说的是商业 HarmonyOS 上原生鸿蒙内核的内部 MAC 机制**，公开资料不足以确认其策略语言、编译产物和查询接口是否与 OpenHarmony SELinux 一致。此时不要把工具写死为 SELinux，而应采用“**通用 MAC 审核核心 + OpenHarmony SELinux 适配器 + 鸿蒙内核适配器**”架构。

下面先给出一个能落地的 **OpenHarmony/HarmonyOS MAC Policy Audit Skill** 对标方案。

---

# 一、项目定位

建议 Skill 名称：

```text
ohos-mac-policy-auditor
```

目标不是“根据 AVC 自动补 allow”，而是：

> 审核 OpenHarmony/HarmonyOS MAC 策略变更是否满足最小权限、分层隔离、System/Vendor 边界、HAP 应用隔离、SA/HDF 服务保护、参数保护和升级兼容要求。

OpenHarmony 当前公开策略组件包含：

- `sepolicy/base`
- `sepolicy/ohos_policy`
- `sepolicy/ohos_product`
- `sepolicy/min`
- `sepolicy/whitelist`
- `scripts/build_policy.py`
- `scripts/build_contexts.py`
- `scripts/selinux_check`

其编译流程使用 `checkpolicy`、`secilc` 和 `sefcontext_compile`，生成 `policy.31`、CIL 及 contexts 编译产物。([github.com](https://github.com/openharmony/security_selinux_adapter/blob/master/AGENTS.md?utm_source=openai))

---

# 二、与 SELinux 审核方案的对标关系

| 通用 SELinux 审核能力 | OpenHarmony/HarmonyOS 对标能力 |
|---|---|
| SELint | 自研 `ohos-policy-lint` |
| `checkpolicy` / `secilc` | OpenHarmony 原生策略编译流程 |
| `sesearch` / `seinfo` | `policy.31` 或 `all.cil` 语义查询 |
| `sediff` | 基于 CIL/编译策略的语义差异比较 |
| `neverallow` 检查 | 原生编译检查 + `selinux_check` |
| `file_contexts` 检查 | 文件标签映射审核 |
| systemd/service 审核 | SA、HDF、init service 标签审核 |
| Android app domain 审核 | HAP、APL、`sehap_contexts` 审核 |
| sysprop 审核 | `parameter_contexts` 和参数 set/get 权限审核 |
| `audit2why` | OpenHarmony AVC/hilog/dmesg 解释器 |
| 运行时标签验证 | `ps -eZ`、`ls -lZ`、`restorecon` 等 |
| Vendor policy compatibility | System/Public/Vendor 分层及版本兼容审核 |

OpenHarmony 策略目录本身具有边界语义：`system` 放系统侧策略，`vendor` 放芯片侧策略，跨二者使用的类型应位于 `public`；应用策略应优先针对 `normal_hap_attr`、`system_basic_hap_attr`、`system_core_hap_attr` 等属性，而不是随意写死具体应用类型。([github.com](https://github.com/openharmony/security_selinux_adapter/blob/master/AGENTS.md?utm_source=openai))

---

# 三、总体架构

```text
ohos-mac-policy-auditor
│
├── 1. Product Resolver
│   ├── 识别产品名、分支、版本
│   ├── 解析 GN/build 参数
│   ├── 解析额外产品/SoC/Vendor 策略目录
│   └── 生成“实际生效策略根目录清单”
│
├── 2. Source Policy Linter
│   ├── TE 规则检查
│   ├── contexts 检查
│   ├── System/Public/Vendor 分层检查
│   └── OpenHarmony 专项规则检查
│
├── 3. Native Build Validator
│   ├── build_policy
│   ├── build_contexts
│   ├── neverallow
│   └── selinux_check
│
├── 4. Semantic Policy Analyzer
│   ├── CIL 标准化
│   ├── attribute 展开
│   ├── allow/allowxperm 展开
│   ├── domain transition
│   └── 信息流分析
│
├── 5. Policy Diff Engine
│   ├── 新增权限
│   ├── 删除约束
│   ├── attribute 成员变化
│   ├── context 映射变化
│   └── System/Vendor 接口变化
│
├── 6. Runtime Evidence Analyzer
│   ├── AVC/hilog/dmesg
│   ├── 进程实际标签
│   ├── 文件实际标签
│   ├── SA/HDF/parameter 访问
│   └── 测试覆盖率
│
└── 7. Risk Report Generator
    ├── 确定越权
    ├── 高风险授权
    ├── 兼容性问题
    ├── 可维护性问题
    └── 验证命令和整改建议
```

---

# 四、必须覆盖的策略输入

## 1. TE 策略

```text
*.te
*.spt
*.cil
```

需要提取：

- `type`
- `attribute`
- `typeattribute`
- `allow`
- `allowxperm`
- `dontaudit`
- `neverallow`
- `type_transition`
- 宏调用及展开结果

## 2. 标签映射

至少支持：

```text
file_contexts
service_contexts
hdf_service_contexts
parameter_contexts
sehap_contexts
```

OpenHarmony 除文件和进程之外，还对参数、System Ability、HDF 服务和 HAP 应用标签进行控制；仓库中也提供参数和服务权限检查相关运行时组件。([github.com](https://github.com/openharmony/security_selinux_adapter/blob/master/AGENTS.md?utm_source=openai))

## 3. 产品配置

必须解析：

```text
selinux.gni
product config.json
BUILD.gn
selinux_adapter_build_path
selinux_adapter_components
selinux_adapter_vendor_policy_version
selinux_adapter_support_developer_mode
selinux_adapter_check_extend_list
```

不能只扫描：

```text
base/security/selinux_adapter/sepolicy
```

因为最终产品策略可能由以下内容共同聚合：

```text
base policy
+ ohos_policy
+ ohos_product
+ device/SoC policy
+ vendor policy
+ product extra policy
```

否则 Skill 可能对“源码局部策略”给出正确结论，但对“产品最终生效策略”给出错误结论。OpenHarmony 的构建参数明确支持额外策略路径、System/Vendor 组件选择和 Vendor policy version。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/blob/master/selinux.gni?utm_source=openai))

---

# 五、核心审核规则包

建议规则编号统一使用：

```text
OHMAC-xxx
```

## A. 通用最小权限规则

### OHMAC-001：通配符授权

阻止或告警：

```te
allow * *:* *;
allow domain *:file *;
allow foo bar:file *;
```

特别关注：

- `write`
- `execute`
- `execute_no_trans`
- `relabelfrom`
- `relabelto`
- `mount`
- `ptrace`
- `setattr`
- `entrypoint`
- `dyntransition`
- `setcurrent`

默认级别：

```text
Critical / Block
```

---

### OHMAC-002：权限集合过宽

例如：

```te
allow foo sensitive_data_file:file {
    create read write open append unlink rename setattr
};
```

Skill 不应只报告“权限很多”，而应拆分为：

```text
读取能力
修改能力
删除能力
标签修改能力
持久化能力
代码执行能力
```

并生成攻击场景，例如：

> `foo` 若被攻陷，可以修改或删除敏感数据，并可能通过可执行文件写入形成持久化。

---

### OHMAC-003：写入和执行组合

重点检测：

```text
同一 domain 对同一对象既有 write 又有 execute
同一 attribute 集合形成间接 W+X
可写目录中的文件可被高权限 domain 执行
```

OpenHarmony 当前策略自检要求对“具有写和执行能力的文件目录”使用 `neverallow` 保护。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

## B. OpenHarmony 分层规则

### OHMAC-010：策略目录放置错误

检查：

```text
system 策略是否错误放入 vendor
vendor 私有策略是否依赖 system 私有 type
跨 System/Vendor 使用的 type 是否位于 public
是否继续向不应扩展的 base 目录添加业务策略
```

示例：

```text
vendor/foo.te 引用了 system/private/bar_type
```

输出：

```text
Severity: High
Reason: Vendor policy depends on a System-private policy symbol.
Risk: Breaks independent System/Vendor evolution and upgrade compatibility.
Fix: Move the shared type definition to the corresponding public directory.
```

---

### OHMAC-011：Public API 扩张

重点检查：

- 新增 public type
- public attribute 成员扩大
- public 宏增加权限
- public `neverallow` 被放宽
- Vendor 可见接口发生变化

该检查类似 API ABI 审核。

一个 public attribute 新增成员可能产生大量隐式授权，因此不能只看新增的一行：

```te
typeattribute new_domain privileged_service_attr;
```

必须展开它带来的全部权限增量。

---

### OHMAC-012：Vendor 策略版本兼容

检查：

```text
selinux_adapter_vendor_policy_version
public policy 变化
vendor policy 对旧 public symbol 的依赖
删除或重命名 public type
```

输出兼容性结论：

```text
Compatible
Conditionally compatible
Breaking change
Unable to verify
```

---

## C. HAP 应用审核

### OHMAC-020：HAP 授权范围过宽

检查应用策略是否使用正确范围：

```text
normal_hap_attr
system_basic_hap_attr
system_core_hap_attr
hap_domain
```

例如：

```te
allow hap_domain camera_service:service_manager find;
```

Skill 应明确指出：

> 该规则可能覆盖所有 HAP，而不是单个系统应用。

审核时需要回答：

1. 是否真的允许所有普通应用？
2. 是否只应允许预装应用？
3. 是否只应允许 `system_basic`？
4. 是否只应允许 `system_core`？
5. 能否改为更窄的 application attribute？

OpenHarmony 官方仓库当前明确要求应用策略使用适当的 HAP 属性，并在新增 HAP 权限时确认授权范围。([github.com](https://github.com/openharmony/security_selinux_adapter/blob/master/AGENTS.md?utm_source=openai))

---

### OHMAC-021：MAC 与 AccessToken 权限不一致

这是 OpenHarmony Skill 应比普通 SELinux Skill 多做的一层。

检查链：

```text
HAP/Native 调用方
    ↓
SELinux 是否允许找到/调用 SA
    ↓
服务端是否校验 AccessToken
    ↓
调用方是否声明对应 permission
    ↓
APL 是否满足
    ↓
是否需要 ACL 或 user_grant
```

可能发现：

```text
SELinux 允许所有 HAP 查找某个 SA，
但服务接口未做 AccessToken 校验。
```

或者：

```text
AccessToken 授予权限，
但 SELinux 将资源暴露给比预期更大的 domain 范围。
```

AccessToken 中应用具有 `normal`、`system_basic` 和 `system_core` 等 APL，较高等级权限还可能需要 ACL 声明，因此 MAC 审核不能完全脱离上层权限模型。([gitee.com](https://gitee.com/openharmony/docs/blob/3b5665a92234a177016080174066e457dc9d30c6/en/application-dev/security/accesstoken-guidelines.md?utm_source=openai))

该检查第一版可以标记为：

```text
Cross-layer review required
```

后续再与源码静态分析联动。

---

## D. SA 和 HDF 服务审核

### OHMAC-030：SA 服务缺少独立标签

检查：

```text
新增 SA 是否有独立 service type
service_contexts 是否有映射
调用 domain 是否精确
是否错误使用 default_service
```

建议直接阻止：

```text
default_service
```

作为正式业务服务标签。

---

### OHMAC-031：敏感 SA 缺少 neverallow 看护

例如某个 SA 不应向普通 HAP 暴露，则除了精确 `allow`，还应考虑：

```te
neverallow normal_hap_attr sensitive_sa_service:service_manager find;
```

需要基于实际 class 和策略语义生成建议，不能机械复制上述示例。

OpenHarmony 当前策略合入自检明确要求：不允许应用访问的 SA 服务应使用 `neverallow` 看护。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

### OHMAC-032：HDF 服务默认标签

阻止使用：

```text
default_hdf_service
```

检查：

```text
HDF service 是否有独立 type
hdf_service_contexts 是否存在映射
访问方是否只获得所需 HDF 服务权限
System domain 是否访问了不应暴露的 Vendor HDF 服务
```

---

### OHMAC-033：SA/HDF 映射与策略不一致

发现以下问题：

```text
contexts 有标签但没有 type 定义
type 已定义但没有 contexts 映射
allow 指向永远不会被分配的标签
同一服务存在重复映射
通配映射覆盖精确映射
```

---

## E. 系统参数审核

### OHMAC-040：默认参数标签

阻止正式策略使用：

```text
default_param
```

新增参数必须检查：

```text
parameter type
parameter_contexts
读取权限
写入权限
监听权限
init/parameter service 配置
```

---

### OHMAC-041：三方应用设置系统参数

检测：

```te
allow normal_hap_attr xxx_parameter:parameter_service set;
allow hap_domain xxx_parameter:parameter_service set;
```

默认定级：

```text
High / Block
```

除非有明确的设计和安全评审依据。

OpenHarmony 当前策略自检要求系统参数禁止三方应用配置；启动参数机制同时存在 DAC 与 SELinux MAC 控制，不能通过放松其中一层来规避另一层。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

### OHMAC-042：参数标签缺失或范围重叠

检测：

```text
parameter_contexts 前缀冲突
宽泛前缀吞掉更精确参数
新增参数落入 default_param
只定义 type 但未配置 context
删除旧 parameter label 导致升级问题
```

---

## F. 文件和可执行程序审核

### OHMAC-050：可执行文件没有独立标签

重点检查：

```text
/system/bin/*
/vendor/bin/*
/chipset/bin/*
```

若新增 daemon 仍落在通用标签，应报告：

```text
Executable uses a shared/default file type.
No explicit domain transition can be established.
```

当前 OpenHarmony 策略自检要求二进制执行文件设置独立标签。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

### OHMAC-051：缺失或异常 domain transition

检查完整链路：

```text
init/service source domain
        ↓
executable file type
        ↓
entrypoint permission
        ↓
type_transition
        ↓
target process domain
```

避免只检查是否有：

```te
type foo, domain;
```

而忽略进程实际仍运行在 `init`、`shell` 或共享 domain 下。

---

### OHMAC-052：file_contexts 正则冲突

检测：

- 重复正则
- 永远无法匹配的规则
- 宽泛规则覆盖精确规则
- 相同路径映射到不同 type
- 路径与 System/Vendor 分区不一致
- 删除旧文件标签引起 OTA 后旧文件残留标签问题

OpenHarmony 当前自检特别强调：文件类型旧标签不应随意删除，因为可能产生升级兼容问题。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

## G. ioctl 审核

### OHMAC-060：只允许 ioctl，未限制命令字

发现：

```te
allow foo bar_device:chr_file ioctl;
```

但没有对应：

```te
allowxperm foo bar_device:chr_file ioctl {
    0x1234
};
```

则报告：

```text
High: ioctl access is not restricted to required command numbers.
```

Skill 需要从 AVC 中提取 ioctl command：

```text
ioctlcmd=0x....
```

并生成候选 `allowxperm`，但必须标记为：

```text
Candidate only — requires driver/API ownership verification.
```

OpenHarmony 当前策略自检明确要求新增 ioctl 权限时根据 AVC 中的命令字使用 `allowxperm` 收窄接口。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

## H. 调试与开发者模式

### OHMAC-070：调试权限未隔离

检查高风险权限是否放在：

```text
debug_only(...)
developer_only(...)
```

重点主体：

```text
sh
shell
hdcd
su
debugger
test process
```

重点权限：

```text
ptrace
sys_admin
sys_ptrace
读取日志
读取进程内存
访问 debugfs
修改 SELinux 状态
写系统参数
执行测试二进制
```

当前 OpenHarmony 策略要求 debug 功能和 developer mode 功能分别使用对应宏隔离。([gitee.com](https://gitee.com/openharmony/security_selinux_adapter/pulls/7024?utm_source=openai))

---

### OHMAC-071：生产构建泄漏调试权限

对比：

```text
release policy
developer-mode policy
debug policy
```

要求：

```text
debug/developer policy 可以比 release 多
release policy 不应出现反向增量
```

报告中单独输出：

```text
Permissions available only in developer mode
Permissions unexpectedly available in release mode
```

---

# 六、审核流程设计

## 阶段 1：确定产品实际策略集合

```text
读取产品名
读取 build profile
读取 selinux.gni
解析 selinux_adapter_build_path
解析 System/Vendor 组件
收集所有 .te/.spt/context 文件
记录文件来源及优先级
```

产物：

```json
{
  "product": "rk3568",
  "policy_roots": [
    {
      "path": "base/security/selinux_adapter/sepolicy/base",
      "layer": "base"
    },
    {
      "path": "base/security/selinux_adapter/sepolicy/ohos_policy",
      "layer": "platform"
    },
    {
      "path": "vendor/example/product/sepolicy",
      "layer": "vendor"
    }
  ]
}
```

如果无法确定完整产品策略根目录，Skill 必须停止给出确定性结论：

```text
Result: PARTIAL
Reason: Product-specific policy roots could not be resolved.
```

---

## 阶段 2：源码静态检查

执行：

```text
语法级 AST 解析
宏引用分析
目录边界检查
context 映射检查
OpenHarmony 专项规则包
```

这一阶段适合快速 PR 检查。

---

## 阶段 3：原生编译验证

优先使用项目自身构建：

```bash
hb build selinux_adapter -i
```

测试：

```bash
hb build selinux_adapter -t
```

并解析：

- 编译错误
- `neverallow` violation
- `selinux_check` 失败
- contexts 编译失败
- 单元测试失败

OpenHarmony 仓库给出的完成条件包括：构建成功、单元测试通过、无 `neverallow` 违规，以及设备启动后没有未解释的 AVC。([github.com](https://github.com/openharmony/security_selinux_adapter/blob/master/AGENTS.md?utm_source=openai))

---

## 阶段 4：生成标准化策略图

将 CIL 或编译策略转换成图：

```text
Node:
  Domain
  Type
  Attribute
  File
  SA
  HDF service
  Parameter
  HAP category

Edge:
  allow
  transition
  membership
  context mapping
  neverallow constraint
```

示例：

```text
normal_hap_attr
    └── find → camera_service
                  └── call → camera_sa
                               └── read → camera_device
```

这样 Skill 才能回答：

> 一条新增 `typeattribute` 到底间接增加了多少权限？

---

## 阶段 5：语义 diff

不要只做文本 diff。

输入：

```text
baseline policy
candidate policy
```

输出：

```text
新增 allow
删除 allow
新增 allowxperm
扩大 attribute
删除 neverallow
修改 context
新增 domain transition
新增 HAP 可达服务
新增 System→Vendor 通路
新增普通应用→敏感资源路径
```

建议输出如下：

```text
Direct additions: 3
Indirect additions through attributes: 148
New HAP-reachable services: 2
New writable executable types: 1
Removed neverallow constraints: 0
```

---

## 阶段 6：运行时证据关联

输入：

```text
dmesg
hilog
AVC 日志
ps -eZ
ls -lZ
服务清单
测试场景清单
```

AVC 归一化为：

```json
{
  "subject": "foo_service",
  "target": "bar_data_file",
  "class": "file",
  "permissions": ["open", "read"],
  "path": "/data/service/bar/db",
  "permissive": false,
  "count": 12
}
```

然后分类：

```text
A. 标签错误
B. 缺失 domain transition
C. 缺失 context 映射
D. 合理但缺失的最小权限
E. 设计越权，不应添加 allow
F. 调试构建专属需求
G. 测试环境噪声
```

特别规定：

> Skill 禁止将每条 AVC 自动转换成 allow。

---

# 七、Skill 目录结构

```text
ohos-mac-policy-auditor/
├── SKILL.md
├── README.md
├── references/
│   ├── openharmony-policy-model.md
│   ├── system-vendor-boundary.md
│   ├── hap-apl-model.md
│   ├── sa-hdf-model.md
│   ├── parameter-security.md
│   └── risk-classification.md
│
├── scripts/
│   ├── resolve_product.py
│   ├── collect_policy.py
│   ├── compile_policy.py
│   ├── normalize_cil.py
│   ├── semantic_diff.py
│   ├── parse_avc.py
│   ├── audit_contexts.py
│   └── generate_report.py
│
├── adapters/
│   ├── base_mac.py
│   ├── openharmony_selinux.py
│   └── hongmeng_kernel_mac.py
│
├── rules/
│   ├── generic.yaml
│   ├── openharmony.yaml
│   ├── hap.yaml
│   ├── sa_hdf.yaml
│   ├── parameter.yaml
│   ├── ioctl.yaml
│   └── debug_release.yaml
│
├── schemas/
│   ├── finding.schema.json
│   ├── policy_graph.schema.json
│   └── report.schema.json
│
└── tests/
    ├── fixtures/
    ├── positive/
    ├── negative/
    └── golden-reports/
```

---

# 八、`SKILL.md` 核心模板

```markdown
---
name: ohos-mac-policy-auditor
description: >
  Audit OpenHarmony/HarmonyOS MAC policy changes for least privilege,
  System/Vendor isolation, HAP scope, SA/HDF exposure, parameter security,
  ioctl restrictions, debug-mode leakage, and upgrade compatibility.
---

# OpenHarmony MAC Policy Auditor

## Scope

Audit source policy, compiled policy, context mappings, policy diffs,
and runtime AVC evidence.

Do not automatically convert AVC denials into allow rules.

## Required inputs

At least one of:

1. OpenHarmony source tree and product name
2. Baseline and candidate policy source trees
3. Compiled policy/CIL and context files
4. AVC logs plus actual runtime labels

## Mandatory workflow

1. Resolve the complete product policy roots.
2. Identify System/Public/Vendor ownership.
3. Run source-level lint.
4. Run the native policy build and neverallow checks.
5. Normalize compiled policy or CIL.
6. Compare semantic policy differences.
7. Evaluate OpenHarmony-specific rule packs.
8. Correlate findings with runtime evidence.
9. Perform an independent second-pass review.
10. Generate a structured report.

## Hard prohibitions

- Never recommend setenforce 0 as a production fix.
- Never generate allow rules solely from AVC logs.
- Never edit generated policy.31 or generated CIL.
- Never weaken neverallow without explicit security review.
- Never use default_param, default_service, or default_hdf_service
  as a normal business label.
- Never claim full-policy safety if product-specific policy roots
  were not resolved.

## Severity

Critical:
- Third-party HAP obtains privileged write/execute/control access
- neverallow protection is removed
- release builds expose debug privileges
- wildcard access to sensitive objects

High:
- HAP scope is broader than required
- SA/HDF service exposed to untrusted applications
- system parameter can be set by third-party applications
- ioctl permission is unrestricted
- writable executable path

Medium:
- Context conflict
- Wrong System/Public/Vendor policy location
- Missing dedicated executable label
- Upgrade compatibility concern

Low:
- Naming, comments, organization, or maintainability issue
```

---

# 九、报告格式

每个 Finding 必须包含：

```yaml
id: OHMAC-041
severity: high
confidence: high

title: Third-party HAP domains can set a system parameter

policy_source:
  file: sepolicy/ohos_policy/foo/system/foo.te
  line: 38

rule:
  allow normal_hap_attr foo_parameter:parameter_service set;

effective_subjects:
  - normal_hap
  - isolated_normal_hap
  - other-expanded-members

asset:
  type: system_parameter
  name: persist.foo.mode

impact:
  - Modify privileged service behavior
  - Persist configuration across reboot

evidence:
  source_policy: true
  compiled_policy: true
  runtime_observed: false

recommendation:
  - Remove set permission from normal_hap_attr
  - Introduce a narrowly scoped privileged domain
  - Enforce AccessToken validation in the receiving service
  - Add a neverallow preventing normal HAP domains from setting it

verification:
  - Rebuild policy
  - Run neverallow checks
  - Query compiled CIL
  - Test authorized and unauthorized callers
```

---

# 十、合入门禁设计

## 必须阻塞合入

```text
Critical finding
High-confidence High finding
neverallow violation
policy compilation failure
context compilation failure
release/debug 权限泄漏
普通 HAP 新增敏感写权限
System/Vendor 边界破坏
```

## 允许人工豁免

```text
Medium finding
未使用权限候选
业务合理但缺少说明的授权
旧版本兼容性风险
无法复现的运行时 AVC
```

豁免必须包含：

```yaml
owner: subsystem-security-owner
reason: business justification
scope: exact rule or finding
expiry: 2026-12-31
reviewer: security-reviewer
```

不建议使用永久性、无所有者的 whitelist。

---

# 十一、测试矩阵

至少准备这些反例：

| 测试 | 预期结果 |
|---|---|
| 普通 HAP 查找敏感 SA | High |
| HAP 设置系统参数 | High/Critical |
| `default_service` | High |
| `default_hdf_service` | High |
| `default_param` | High |
| ioctl 没有 `allowxperm` | High |
| Vendor 引用 System-private type | High |
| 删除 public type | High/Compatibility |
| 可写文件同时可执行 | Critical |
| debug 权限进入 release | Critical |
| `file_contexts` 重叠 | Medium/High |
| 新二进制共用通用标签 | Medium |
| 删除旧文件标签 | Upgrade warning |
| attribute 新成员产生权限膨胀 | 按展开结果定级 |
| AVC 由标签错误导致 | 建议修 context，不建议补 allow |
| 只提供局部目录 | 输出 PARTIAL，不给全局安全结论 |

---

# 十二、分阶段落地计划

## 第一阶段：MVP

先实现：

```text
产品策略目录收集
TE/context 源码 lint
OpenHarmony 专项规则
原生编译和 neverallow 检查
AVC 解析
Markdown/JSON 报告
```

推荐规则：

```text
OHMAC-001 wildcard
OHMAC-010 分层错误
OHMAC-020 HAP 范围
OHMAC-030 默认 SA 标签
OHMAC-032 默认 HDF 标签
OHMAC-040 默认参数标签
OHMAC-041 HAP 设置参数
OHMAC-050 执行文件标签
OHMAC-060 ioctl/allowxperm
OHMAC-070 debug/developer 隔离
```

## 第二阶段：语义审核

增加：

```text
CIL 解析
attribute 展开
有效权限查询
语义 diff
domain transition 图
context 冲突分析
System/Vendor API 兼容分析
```

## 第三阶段：跨层安全审核

增加：

```text
MAC + AccessToken
MAC + SA 接口鉴权
MAC + init service 配置
MAC + sandbox
MAC + seccomp
MAC + DAC
HAP/SA/HDF 端到端攻击路径
```

OpenHarmony 的 native service 安全通常不仅涉及 SELinux，还可能同时涉及 init 的 `uid/gid/caps/secon`、参数 DAC、sandbox 和 seccomp。因此第三阶段应做组合分析，而不是把 MAC 当作唯一安全边界。([gitee.com](https://gitee.com/openharmony/docs/blob/b5841fbaa6e23738c8a53e9a53744c8407aece3e/en/device-dev/subsystems/subsys-boot-init-sandbox.md?utm_source=openai))

---

# 十三、针对原生鸿蒙内核的适配层

如果目标确实不是 Linux SELinux，而是原生鸿蒙内核 MAC，那么保持上述审核模型，只替换后端：

```python
class MacPolicyAdapter:
    def discover_policy_roots(self, product):
        ...

    def compile_policy(self):
        ...

    def list_subjects(self):
        ...

    def list_objects(self):
        ...

    def list_rules(self):
        ...

    def expand_groups(self):
        ...

    def query_effective_access(self, subject, obj, operation):
        ...

    def list_constraints(self):
        ...

    def semantic_diff(self, baseline, candidate):
        ...

    def parse_runtime_denial(self, log):
        ...
```

鸿蒙内核适配器需要你们内部提供至少以下信息：

1. 策略语言或配置格式；
2. 主体、客体、权限和安全域模型；
3. 策略编译器；
4. 最终策略产物；
5. 查询有效权限的方法；
6. deny/audit 日志格式；
7. 系统服务、应用、驱动和参数的标签机制；
8. 策略版本及系统/芯片兼容机制；
9. 对应 `neverallow` 的强制约束；
10. debug/release 策略裁剪方式。

如果暂时拿不到“有效权限查询接口”，可以先编写源码级 Skill，但报告必须明确：

```text
Source-level finding only.
Effective runtime policy could not be verified.
```

---

# 结论

推荐最终采用：

```text
通用 MAC 审核核心
├── OpenHarmony SELinux Adapter
│   ├── build_policy / build_contexts
│   ├── selinux_check / neverallow
│   ├── CIL semantic analyzer
│   └── AVC runtime analyzer
│
├── OpenHarmony Rule Pack
│   ├── System/Public/Vendor
│   ├── HAP/APL
│   ├── SA/HDF
│   ├── parameter
│   ├── ioctl
│   └── debug/developer mode
│
└── HongMeng Kernel MAC Adapter
    └── 对接内部策略编译器、查询器和审计日志
```

**最关键的三个差异化能力**是：

1. 不只审 `.te`，必须解析完整产品的 System、Vendor、SoC 和 Product 策略；
2. 不只审文件权限，还要审 HAP、SA、HDF 和系统参数；
3. 不只做文本 diff，必须展开 attribute 后比较最终有效权限。