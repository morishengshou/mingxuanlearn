# `config_policy_utils.c` 代码检视报告

> 范围：`frameworks/config_policy/src/config_policy_utils.c`（含其调用约定层）
> 目标：识别移植后可能出现的内存安全、未定义行为、资源泄漏、输入校验缺失等高风险问题，并给出修改建议。
> 评级：🔴 高危（必须修） · 🟠 中危（建议修） · 🟡 低危/最佳实践

---

## 缺陷总览

| 编号 | 级别 | 类别 | 位置 | 摘要 |
|------|------|------|------|------|
| D-01 | 🔴 | 内存泄漏 | `GetCfgDirRealPolicyValue` L400-405 | 系统参数返回非 NULL 空串时旧指针被直接覆盖 |
| D-02 | 🔴 | 输入校验缺失 / 路径穿越 | `GetOneCfgFileEx` / `GetCfgFilesEx` | `pathSuffix` 未过滤 `../`、绝对路径、NUL，可逃出策略目录 |
| D-03 | 🔴 | 未定义行为 | `TrimInplace` L275/L278 | `isspace(char)` 未强转 `unsigned char`，含非 ASCII 字节时 UB |
| D-04 | 🟠 | 未定义行为 | `GetFollowXRule` L210 | `endItem` 可能为 NULL 时仍执行 `endItem + 1` 指针算术 |
| D-05 | 🟠 | 解析健壮性 | `GetFollowXRule` L221 | `atoi` 无错误反馈，非法字符串静默得 0 |
| D-06 | 🟠 | 整数溢出 | `SplitStr` L157 | `sizeof(char *) * segCount` 未做溢出检查 |
| D-07 | 🟠 | 边界越界风险 | `EnsureHolderSpace` L298-305 | 上限截断后可能 `allocSize < leastSize`；二次 calloc 又脱离上限 |
| D-08 | 🟠 | 隐式所有权转移 | `SplitStr` ↔ `FreeSplitedStr` | `orgStr` 静默接管，调用方很容易二次 free 或忘记调用专用释放器 |
| D-09 | 🟠 | TOCTOU & 符号链接 | `GetOneCfgFileEx` L455 / `GetCfgFilesEx` L503 | `access(F_OK)` 后返回路径；符号链接逃逸/竞态 |
| D-10 | 🟡 | NULL 入参未校验 | `SetMiniConfigPolicy` L59 | `policy` 为 NULL 时 `strcpy_s` 返回错误但无日志，难定位 |
| D-11 | 🟡 | 接口签名 | `GetCfgDirList()` L525 | 实现处缺 `void`，K&R 风格签名 |
| D-12 | 🟡 | size_t→int 转换 | `TrimInplace` L278 | `int i = strlen(src) - 1`，超长字符串时实现定义 |
| D-13 | 🟡 | 输入修改副作用 | `ExpandStr` L350 | 直接改写入参 `src`，未在文档中标注 |
| D-14 | 🟡 | 线程安全 | 全文 | 文档未声明，但 `errno`/`gConfigPolicy` 等存在共享状态隐患 |

---

## D-01 🔴 系统参数空串导致内存泄漏

`config_policy_utils.c:400-406`

```c
res->realPolicyValue = CustGetSystemParam(CUST_KEY_POLICY_LAYER);
if (res->realPolicyValue != NULL && res->realPolicyValue[0]) {
    return;
}
res->realPolicyValue = strdup(DEFAULT_LAYER);   // ← 直接覆盖
```

**问题**：`CustGetSystemParam` 内部 `calloc` 分配的缓冲区，当系统参数虽存在但内容为 `""` 时（`value[0] == '\0'`，注意 `CustGetSystemParam` 第 111 行的 `value[0]` 判定会过滤掉这种情况，但移植后若适配实现把 `len=1, value=""` 视为成功返回，就会触发），原来的指针未 `free` 即被覆盖，发生泄漏。同样问题：若 `realPolicyValue` 非 NULL 但为空，回退分支会泄漏前一次分配。

**修复**：

```c
if (res->realPolicyValue == NULL || res->realPolicyValue[0] == '\0') {
    FreeIf(res->realPolicyValue);            // ← 显式释放
    res->realPolicyValue = strdup(DEFAULT_LAYER);
}
```

---

## D-02 🔴 `pathSuffix` 未做合法性校验（路径穿越）

`config_policy_utils.c:434/445/479/495` 等所有对外接口

```c
snprintf_s(buf, bufLength, bufLength - 1, "%s/%s", dirs->paths[i - 1], pathSuffix);
```

`pathSuffix` 由调用方直接传入并拼接到策略目录后。若上层 NAPI / FFI 把不可信字符串透传下来，攻击者可用：

- `"../../../etc/shadow"` 逃出 `/system` 等基目录
- `"\0../passwd"` 截断（虽然 C 字符串本身阻断，但联动 JS/NAPI 时 V8 字符串可能含嵌入 NUL）
- 绝对路径 `"/etc/passwd"` 直接覆盖前缀拼接预期

由于 `GetCfgFiles` 的语义是**返回真实存在的文件路径供后续 `fopen` 等使用**，路径穿越后果即任意文件读取。

**修复（建议在 utils 层做兜底）**：

```c
static bool IsValidPathSuffix(const char *p)
{
    if (p == NULL || *p == '\0' || *p == '/') return false;
    if (strstr(p, "..") != NULL) return false;          // 简化版；更严谨需按段判定
    for (const char *q = p; *q; q++) {
        if ((unsigned char)*q < 0x20) return false;     // 控制字符
    }
    return strlen(p) < MAX_PATH_LEN;
}
```

并在每个 `Get*` 入口处先调用。`Follow-X` 的 `extra` 同样需要校验。

---

## D-03 🔴 `isspace` 未强转 `unsigned char`（UB）

`config_policy_utils.c:272-290`

```c
while (isspace(*src)) { src++; }
for (int i = strlen(src) - 1; i >= 0 && isspace(src[i]); i--) { ... }
```

C 标准规定 `isspace` 实参必须为 `EOF` 或 `unsigned char` 表达式的值。若 `char` 在目标平台是有符号且字符串含非 ASCII 字节（如 UTF-8 0x80~0xFF），传入会被符号扩展为负数，触发**未定义行为**（多数实现以数组越界形式访问 ctype 表）。

**修复**：

```c
while (isspace((unsigned char)*src)) { src++; }
...
if (isspace((unsigned char)src[i])) { src[i] = '\0'; }
```

同类问题：项目内其他位置如使用 `isalpha/isdigit/tolower` 等，全部需复查。

---

## D-04 🟠 `GetFollowXRule` 中 NULL 指针算术

`config_policy_utils.c:209-214`

```c
char *endItem = strchr(item, SEP_FOR_X_RULE);
char *nextItem = endItem + 1;              // ← endItem 可能是 NULL
while (endItem && *nextItem == '-') {
    endItem = strchr(nextItem, SEP_FOR_X_RULE);
    nextItem = endItem + 1;                // ← 同样问题
}
```

`endItem` 为 NULL 时，`endItem + 1` 已经先行求值。`NULL + 1` 是 C 标准未定义行为；多数平台得到 `0x1`，未解引用前看似无害，但触发 UBSan/CodeChecker 告警，且在抢占式优化器下可能被异常路径优化。

**修复**：

```c
while (endItem != NULL) {
    char *nextItem = endItem + 1;
    if (*nextItem != '-') break;
    endItem = strchr(nextItem, SEP_FOR_X_RULE);
}
```

---

## D-05 🟠 `atoi` 无错误反馈

`config_policy_utils.c:221`

```c
*mode = atoi(modeStr);
```

`atoi` 对非数字静默返回 0，等价于 `FOLLOWX_MODE_DEFAULT`，导致逻辑被无声劫持。

**修复**：用 `strtol` 并校验：

```c
char *endp = NULL;
errno = 0;
long v = strtol(modeStr, &endp, 10);
if (endp == modeStr || errno != 0 || v < INT_MIN || v > INT_MAX) {
    /* 拒绝该规则 */
} else {
    *mode = (int)v;
}
```

---

## D-06 🟠 `SplitStr` 整数溢出

`config_policy_utils.c:151-171`

```c
int segCount = 1;
for (char *p = str; *p != '\0'; p++) {
    (*p == delim) ? segCount++ : 0;
}
SplitedStr *result = (SplitedStr *)calloc(sizeof(SplitedStr) + sizeof(char *) * segCount, 1);
```

- `segCount` 为 `int`，理论上 `str` 极长时可达 `INT_MAX`，自增溢出 UB。
- `sizeof(char *) * segCount` 在 32 位地址平台可乘积溢出。
- `calloc` 第一参数表示项数，若把整体 size 塞进项数也丧失了 calloc 自带的溢出检测。

**修复**：

```c
if (str == NULL) return NULL;
size_t segCount = 1;
for (const char *p = str; *p != '\0'; p++) {
    if (*p == delim && segCount < SIZE_MAX) segCount++;
}
if (segCount > MAX_REASONABLE_SEGS /* e.g. PARAM_CONST_VALUE_LEN_MAX */) return NULL;
SplitedStr *result = (SplitedStr *)calloc(1, sizeof(SplitedStr) + sizeof(char *) * segCount);
```

并把结构体里的 `segCount` 改成 `size_t`，对外保持兼容。

---

## D-07 🟠 `EnsureHolderSpace` 上限与重试逻辑漏洞

`config_policy_utils.c:292-316`

```c
size_t allocSize = Min(Max(leastSize * 2, MIN_APPEND_LEN), PARAM_CONST_VALUE_LEN_MAX);
char *newPtr = (char *)calloc(allocSize, sizeof(char));
if (newPtr == NULL) {
    allocSize = leastSize;                       // ← 退化时跳过上限
    newPtr = (char *)calloc(allocSize, sizeof(char));
    ...
}
if (holder->p != NULL && memcpy_s(newPtr, allocSize, holder->p, holder->strLen) != EOK) {
```

两个问题：
1. 当 `leastSize > PARAM_CONST_VALUE_LEN_MAX` 时，上限分支返回的 `allocSize` 小于 `leastSize`，外层 `AppendStr` 误以为容量足够，但实际后续 `strcat_s` 会失败（侥幸 securec 兜住，但流程上是缺陷）。
2. 第二次重试 `allocSize = leastSize`，不再受 `PARAM_CONST_VALUE_LEN_MAX` 限制，相当于失败重试反而申请更大空间，与策略冲突。
3. `leastSize * 2` 自身无溢出检查。

**修复**：

```c
if (leastSize > PARAM_CONST_VALUE_LEN_MAX) return false;     // 显式拒绝
size_t want = leastSize > SIZE_MAX / 2 ? leastSize : leastSize * 2;
size_t allocSize = Min(Max(want, MIN_APPEND_LEN), PARAM_CONST_VALUE_LEN_MAX);
/* 不要在失败时绕过上限；要么返回 false，要么仍受限重试 */
```

---

## D-08 🟠 `SplitStr` 隐式接管 `orgStr` 所有权

```c
result->orgStr = str;    // 接管
...
void FreeSplitedStr(SplitedStr *p) {
    FreeIf(p->orgStr);   // 释放
}
```

`SplitStr` 把外部传入的 `str` 指针**静默存进** `orgStr`，并由 `FreeSplitedStr` 负责释放。当前内部唯一调用点是 `GetFollowXPathByMode` 里 `ExpandStr` 的返回值，但任何后续维护者都很容易传入栈上数组或外部还需使用的指针，引发 use-after-free / double-free。

**修复**（任选）：
- 在 `SplitStr` 内 `strdup` 一份做内部拷贝；
- 或在头注释明确："`str` must be heap-allocated; ownership transferred"；
- 或拆成 `SplitStrTakeOwnership` / `SplitStrCopy` 两个版本。

---

## D-09 🟠 TOCTOU / 符号链接

`config_policy_utils.c:455 / 503`

```c
if (snprintf_s(buf, ...) > 0 && access(buf, F_OK) == 0) { ... }
```

`access` 与后续调用方 `open` 之间存在 TOCTOU；同时 `access` 默认跟随符号链接，攻击者若能在策略目录种植符号链接，可使返回路径指向任意位置。

**建议**：
- 在受信策略目录（`/system` 等）通常由系统镜像写保护，风险较低；但在 `/sys_prod`、`/chip_prod` 等可写分区下应使用 `lstat` 检查是否为符号链接并拒绝；
- 或返回打开后的 FD（更大改动）；
- 在文档中明确"调用方应使用 `O_NOFOLLOW` 打开"。

---

## D-10 🟡 `SetMiniConfigPolicy` 缺 NULL 校验与失败反馈

`config_policy_utils.c:59-65`

```c
void SetMiniConfigPolicy(const char *policy)
{
    if (gConfigPolicy[0] != 0) return;
    (void)strcpy_s(gConfigPolicy, sizeof(gConfigPolicy), policy);
}
```

- `policy == NULL` 时 securec `strcpy_s` 返回错误并清空 dest，但调用方完全无感知。
- 截断（`strlen(policy) >= sizeof(gConfigPolicy)`）同样静默。

**修复**：增加 NULL 校验与日志（接入项目 DFX）：

```c
if (policy == NULL || policy[0] == '\0') return;
if (strcpy_s(gConfigPolicy, sizeof(gConfigPolicy), policy) != EOK) {
    CPLOGE("SetMiniConfigPolicy truncated, len=%zu", strlen(policy));
    gConfigPolicy[0] = '\0';
}
```

---

## D-11 🟡 `GetCfgDirList` 实现处签名不规范

```c
CfgDir *GetCfgDirList()              // ← 应为 (void)
```

C 中空参数列表 `()` 表示**未指明参数**，会绕过原型检查。头文件已写 `(void)`，实现保持一致：

```c
CfgDir *GetCfgDirList(void) { ... }
```

---

## D-12 🟡 `TrimInplace` size 转 int 的隐患

```c
for (int i = strlen(src) - 1; i >= 0 && isspace(src[i]); i--)
```

`strlen` 返回 `size_t`，赋给 `int` 在长度 > `INT_MAX` 时为实现定义行为。虽然实际配置串远小于 2GB，但属于编码红线项，应换成：

```c
for (size_t len = strlen(src); len > 0; len--) {
    if (!isspace((unsigned char)src[len - 1])) break;
    src[len - 1] = '\0';
}
```

---

## D-13 🟡 `ExpandStr` 修改入参且未文档化

`config_policy_utils.c:350` 通过 `*find = *varEnd = 0` 直接修改入参 `src`。当前唯一调用方 `GetFollowXPathByMode` 把 `followXPath`（`strdup` 出的临时缓冲）传入，且调用后立即 `FreeIf(followXPath)`，所以安全。但函数注释完全没有提示这一副作用，后续复用会踩坑。

**修复**：在 `ExpandStr` 头加一行注释 `/* NOTE: modifies src in place; caller must own it. */`，或在内部先 `strdup` 一份再处理。

---

## D-14 🟡 线程安全声明缺失

- `errno = EINVAL`（L363）依赖线程局部 errno，多数 libc 满足，但移植目标若使用全局 errno 会有竞争。
- `gConfigPolicy`（L58）静态全局，`SetMiniConfigPolicy` 无锁，多线程并发首次写入存在竞态。
- `SystemGetParameter` 的线程安全由适配层提供，应在 `port/config_policy_param_adapter.h` 中文档化要求。

**建议**：在头文件或 `开发文档.md` 中明确各 API 的线程安全等级。

---

## 修复优先级建议

1. **立刻修**：D-01、D-02、D-03（与外部输入直接相关，且 D-02 可导致任意文件读取）。
2. **本迭代修**：D-04、D-05、D-06、D-07、D-08（健壮性，影响稳定性与可维护性）。
3. **下一迭代或与文档化同步**：D-09 ~ D-14。

---

## 附：建议补充的单元测试用例

为防止回归，建议在 `test/unittest/config_policy_utils_test.cpp` 中新增：

| 用例 | 目的 |
|------|------|
| `PathTraversalRejected` | 传 `../../etc/passwd` 应返回 NULL |
| `NullAndEmptySuffix` | 传 `NULL`/`""` 应安全返回 NULL |
| `NonAsciiInTrim` | `realPolicyValue` 含 UTF-8 字节，验证 trim 不崩 |
| `MalformedFollowXRule` | `const.cust.follow_x_rules` 含非数字 mode |
| `EmptyPolicyParam` | 系统参数返回空串 → 应回落默认值且不泄漏 |
| `LongPathSuffix` | 接近 `MAX_PATH_LEN` 的后缀，验证截断与不越界 |
| `SymlinkInPolicyDir` | 策略目录中放符号链接，确认行为符合预期 |

可通过 Valgrind / AddressSanitizer 运行测试集以验证 D-01、D-06、D-07 的修复效果。
