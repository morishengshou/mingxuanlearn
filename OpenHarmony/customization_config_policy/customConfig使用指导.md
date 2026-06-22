# customConfig（渠道定制）独立详解

> 本文档是 `config_policy` 组件中 **customConfig 子模块** 的专项说明，面向需要按"渠道号"做
> 应用差异化定制的 OpenHarmony 开发者。内容包含：模块定位、ArkTS 接口用法、内部解析逻辑、
> **C++ 接口（实现内幕 + native 服务等效调用）DEMO**、系统参数的预置方式、权限要求与常见问题。
>
> 组件仓库：`base/customization/config_policy`，NAPI 模块名 `customConfig`，
> SysCap：`SystemCapability.Customization.CustomConfig`，起始版本 API 12。

---

## 一、模块定位

`customConfig` 解决的问题是：**同一个应用包，在不同销售渠道 / OEM 批次上需要表现出不同的行为**
（如不同的默认书签、预置内容、运营活动配置）。

系统集成方为每个应用预置一个**渠道号**到系统参数 `const.channelid.<bundleName>`，
应用运行时调用 `customConfig.getChannelId()` 读取属于自己的渠道号，再据此加载不同配置。

```
系统预置参数:  const.channelid.com.example.app = "CH_0001"
                                  ↑ 当前应用的 bundleName

应用调用:      customConfig.getChannelId()  →  "CH_0001"
```

与 `configPolicy`（按层级查找文件路径）不同，`customConfig` **只返回一个字符串渠道号**，
它本身不查找文件——拿到渠道号后由应用自行决定如何使用。

> ⚠️ 该模块**仅有 1 个对外接口** `getChannelId()`，且**仅 ArkTS（NAPI）形态**，
> 未提供 native inner_api。C++ native 服务若需同等能力，按第五节"等效实现"自行读参数。

---

## 二、ArkTS 接口用法

### 2.1 导入

```ts
import { customConfig } from '@kit.BasicServicesKit';
```

### 2.2 getChannelId

```ts
getChannelId(): string
```

**功能**：同步返回当前应用的渠道号。

| 项 | 说明 |
|----|------|
| 入参 | 无（内部自动取当前应用 bundleName） |
| 返回 | 渠道号字符串；无渠道号、获取 bundleName 失败、或应用在预置列表中时返回 `""` |
| SysCap | `SystemCapability.Customization.CustomConfig` |
| 形态 | 同步（无 callback / promise） |

**示例**：

```ts
import { customConfig } from '@kit.BasicServicesKit';

function loadByChannel(): void {
  let channelId: string = customConfig.getChannelId();
  if (channelId.length === 0) {
    console.info('无渠道号，使用默认配置');
    return;
  }
  console.info('当前渠道号: ' + channelId);   // 例如 "CH_0001"
  // 根据 channelId 加载差异化资源 / 配置
}
```

---

## 三、内部解析逻辑（务必了解）

`getChannelId()` 内部流程如下（源码 `custom_config_napi.cpp`）：

```
1. 取当前应用 bundleName
   └─ AbilityRuntime::Context::GetApplicationContext()->GetBundleName()
   └─ 失败或为空  → 返回 ""

2. 判断是否在"预置应用列表"中
   └─ 读取系统参数 persist.custom.preload.list（可分段）
   └─ 命中  → 返回 ""（预置应用不下发渠道号）

3. 拼接 key = "const.channelid." + bundleName
   └─ 读取该系统参数
   └─ 不存在 / 为空  → 返回 ""
   └─ 存在  → 返回参数值
```

### 预置列表（preload list）格式

预置列表用于排除某些"系统预装应用"，使其不参与渠道定制。
存储在系统参数中，**支持分段**以突破单参数长度上限（`PARAM_CONST_VALUE_LEN_MAX = 4096`）：

| 参数名 | 内容格式 | 说明 |
|--------|----------|------|
| `persist.custom.preload.list` | `"N,bundleA,bundleB,..."` | 首字符是分段总数 N（单个数字 0~9），逗号后为包名列表 |
| `persist.custom.preload.list1` | `"N,bundleC,..."` | 第 2 段（首字符同样占位，被跳过） |
| ... | ... | 直到第 N-1 段 |

> 解析时：第一段首字符 `'0'~'9'` 表示总段数，随后必须是 `','`；后续每段都跳过首字符再拼接。
> 格式不符（首字符非数字、第二字符非逗号）则视为无预置列表，渠道号正常下发。

---

## 四、C++ 接口实现内幕

`customConfig` 的 C++ 代码（`custom_config_napi.cpp`）**是 NAPI 桥接层**，不是可被其他 C++ 模块链接调用的库。
理解它有助于维护与排障。关键实现片段：

```cpp
// 1) 注册为 NAPI 模块 "customConfig"，构造期自动注册
static napi_module g_customConfigModule = {
    .nm_version = 1,
    .nm_register_func = CustomConfigInit,
    .nm_modname = "customConfig",
    ...
};
extern "C" __attribute__((constructor)) void CustomConfigRegister()
{
    napi_module_register(&g_customConfigModule);
}

// 2) 导出唯一方法 getChannelId
napi_value CustomConfigNapi::Init(napi_env env, napi_value exports)
{
    napi_property_descriptor property[] = {
        DECLARE_NAPI_FUNCTION("getChannelId", CustomConfigNapi::NAPIGetChannelId),
    };
    NAPI_CALL(env, napi_define_properties(env, exports,
              sizeof(property) / sizeof(property[0]), property));
    return exports;
}

// 3) 核心：取 bundleName → 排除预置应用 → 读 const.channelid.<bundleName>
napi_value CustomConfigNapi::NAPIGetChannelId(napi_env env, napi_callback_info info)
{
    std::string bundleName;
    if (GetBundleName(bundleName) != 0 || bundleName.empty() || IsInPreloadList(bundleName)) {
        return CreateNapiStringValue(env, "");
    }
    std::string channelKey = "const.channelid." + bundleName;
    return NativeGetChannelId(env, channelKey);   // 内部用 SystemGetParameter 读取
}
```

读取系统参数使用 `init` 子系统的 `SystemGetParameter`（与 `config_policy_utils.c` 中
`CustGetSystemParam` 完全一致的两段式调用：先取长度，再取值，并校验上限 4096）。

---

## 五、C++ native 服务等效调用 DEMO

由于 customConfig **没有 native inner_api**，C/C++ 服务想拿到渠道号，需要**自己读取同一个系统参数**。
下面给出两种等效实现，二选一即可。

### 5.1 BUILD.gn 依赖

```gn
import("//build/ohos.gni")

ohos_shared_library("your_native_service") {
  sources = [ "src/channel_helper.cpp" ]

  external_deps = [
    "c_utils:utils",            # 方式 A：OHOS::system::GetParameter
    "init:libbegetutil",        # 方式 B：SystemGetParameter（与组件实现同源）
    "ability_runtime:app_context",  # 取 bundleName（仅应用进程内可用）
    "hilog:libhilog",
  ]

  subsystem_name = "your_subsystem"
  part_name = "your_part"
}
```

### 5.2 方式 A：使用 c_utils 的 `OHOS::system::GetParameter`（最简洁，推荐）

```cpp
#include <string>
#include "parameters.h"                    // OHOS::system::GetParameter
#include "application_context.h"            // AbilityRuntime::Context
#include "hilog/log.h"

namespace {
constexpr const char *CHANNEL_ID_PREFIX = "const.channelid.";
}

// 取当前应用 bundleName（仅在应用进程 / 有 AbilityRuntime 上下文时可用）
static bool GetBundleName(std::string &bundleName)
{
    auto appContext = OHOS::AbilityRuntime::Context::GetApplicationContext();
    if (appContext == nullptr) {
        return false;
    }
    bundleName = appContext->GetBundleName();
    return !bundleName.empty();
}

// 等效 getChannelId：返回渠道号，无则返回 ""
std::string GetChannelId()
{
    std::string bundleName;
    if (!GetBundleName(bundleName)) {
        return "";
    }
    // 注意：完整等效还应判断预置列表（见 5.4），此处省略
    std::string key = std::string(CHANNEL_ID_PREFIX) + bundleName;
    // 第二个参数为缺省值，参数不存在时返回它
    return OHOS::system::GetParameter(key, "");
}
```

### 5.3 方式 B：使用 init 的 `SystemGetParameter`（与组件实现完全同源）

```cpp
#include <cstdlib>
#include <cstring>
#include <string>
#include "init_param.h"      // SystemGetParameter / PARAM_CONST_VALUE_LEN_MAX

// 复刻 config_policy 内部 CustGetSystemParam 的两段式读取
static char *CustGetSystemParam(const char *name)
{
    unsigned int len = 0;
    if (SystemGetParameter(name, nullptr, &len) != 0 ||
        len == 0 || len > PARAM_CONST_VALUE_LEN_MAX) {
        return nullptr;
    }
    char *value = static_cast<char *>(calloc(len, sizeof(char)));
    if (value != nullptr && SystemGetParameter(name, value, &len) == 0 && value[0] != '\0') {
        return value;     // 调用方负责 free
    }
    if (value != nullptr) {
        free(value);
    }
    return nullptr;
}

std::string GetChannelIdById(const std::string &bundleName)
{
    if (bundleName.empty()) {
        return "";
    }
    std::string key = "const.channelid." + bundleName;
    char *raw = CustGetSystemParam(key.c_str());
    if (raw == nullptr) {
        return "";
    }
    std::string result(raw);
    free(raw);            // ← CustGetSystemParam 分配的内存必须释放
    return result;
}
```

> 内存红线：`CustGetSystemParam` 用 `calloc` 分配，**调用方必须 `free`**，否则泄漏；
> 失败分支内部已释放并返回 `nullptr`。

### 5.4 完整等效：带预置列表排除

若要 100% 复刻 ArkTS 行为（预置应用不返回渠道号），补充预置列表判断：

```cpp
#include <string>
#include "parameters.h"

static bool IsInPreloadList(const std::string &bundleName)
{
    std::string first = OHOS::system::GetParameter("persist.custom.preload.list", "");
    // 格式校验：首字符为段数(0~9)，第二字符为逗号
    if (first.size() < 2 || first[0] < '0' || first[0] > '9' || first[1] != ',') {
        return false;
    }
    int segCount = first[0] - '0';
    std::string merged = first.substr(1);          // 跳过段数占位符
    for (int i = 1; i < segCount; i++) {
        std::string seg = OHOS::system::GetParameter(
            "persist.custom.preload.list" + std::to_string(i), "");
        if (seg.empty()) {
            return false;
        }
        merged.append(seg.substr(1));              // 每段同样跳过首字符
    }
    merged.append(",");
    return merged.find("," + bundleName + ",") != std::string::npos;
}

std::string GetChannelIdFull()
{
    std::string bundleName;
    auto ctx = OHOS::AbilityRuntime::Context::GetApplicationContext();
    if (ctx == nullptr) {
        return "";
    }
    bundleName = ctx->GetBundleName();
    if (bundleName.empty() || IsInPreloadList(bundleName)) {
        return "";
    }
    return OHOS::system::GetParameter("const.channelid." + bundleName, "");
}
```

---

## 六、渠道号的预置（系统集成方）

渠道号是**只读系统参数**（`const.` 前缀），由系统集成方在镜像中预置，应用不可写。

```bash
# 调试期临时设置（重启后失效）
hdc shell param set const.channelid.com.example.app CH_0001

# 读取确认
hdc shell param get const.channelid.com.example.app

# 预置列表（排除某些应用）
hdc shell param set persist.custom.preload.list "1,com.example.preset"
```

生产环境通常通过 `*.para` 参数文件随镜像下发（如 `/system/etc/param/*.para`）：

```ini
const.channelid.com.example.app=CH_0001
```

> `const.` 参数在 `init` 启动阶段加载且不可修改，符合"出厂定制、运行只读"的安全模型。

---

## 七、权限与签名要求

| 项 | 要求 |
|----|------|
| 接口类型 | 系统接口（System API） |
| SDK | 必须使用 **Full SDK**（Public SDK 不含此接口，编译报找不到 `customConfig`） |
| 签名 | 应用需以**系统应用证书**签名 |
| 额外权限 | 无需 `ohos.permission.*`，门槛在"系统应用"身份 |
| SysCap | `SystemCapability.Customization.CustomConfig` |

---

## 八、常见问题

### Q1：`getChannelId()` 始终返回 `""`
逐项排查：
1. 系统参数 `const.channelid.<你的包名>` 是否已预置（`hdc shell param get`）；
2. 当前应用是否在 `persist.custom.preload.list` 中（预置应用不下发渠道号）；
3. 是否用 Full SDK + 系统应用签名（否则接口不可用）。

### Q2：C++ 服务里取不到 bundleName
`AbilityRuntime::Context::GetApplicationContext()` 仅在**应用进程**内有上下文。
纯 SA / 守护进程没有 application context，应改为**显式传入目标 bundleName**
（如 5.3 的 `GetChannelIdById`），或由调用方提供。

### Q3：C++ 读到的渠道号和 ArkTS 不一致
确认 key 拼接为 `const.channelid.` + **完整 bundleName**，且是否需要做预置列表排除（5.4）。
ArkTS 实现包含预置列表判断，简化版 C++（5.2/5.3）不含。

### Q4：`SystemGetParameter` 返回非 0
`len` 超过 `PARAM_CONST_VALUE_LEN_MAX(4096)` 或参数不存在都会失败，按"无渠道号"处理返回 `""`。

---

## 九、接口速查

| 接口 | 形态 | 入参 | 返回 | 无结果 |
|------|------|------|------|--------|
| `customConfig.getChannelId()` (ArkTS) | 同步 | 无 | `string` 渠道号 | `""` |
| `OHOS::system::GetParameter(key, "")` (C++ 等效) | 同步 | 参数名 | `std::string` | 缺省值 `""` |
| `SystemGetParameter(name, buf, &len)` (C 等效) | 同步 | 参数名/缓冲 | 状态码 `int` | 非 0 |

---

## 参考资料

- 源码：`interfaces/kits/js/src/custom_config_napi.cpp`、`interfaces/kits/js/include/custom_config_napi.h`
- 构建：`interfaces/kits/js/BUILD.gn`（`ohos_shared_library("customconfig")`）
- 系统参数能力：`init` 子系统 `init_param.h`（`SystemGetParameter`）、`c_utils` `parameters.h`（`OHOS::system::GetParameter`）
- 配套文档：`OpenHarmony使用指导.md`（configPolicy 配置层级查找）
