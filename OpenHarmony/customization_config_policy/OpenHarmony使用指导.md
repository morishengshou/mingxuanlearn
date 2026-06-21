# customization_config_policy 在 OpenHarmony 上的使用指导

> 本文档面向**首次在 OpenHarmony 系统上集成 `config_policy`（配置策略）组件**的开发者，
> 说明该组件提供的能力、各接口的调用方式（ArkTS / Native C 两条路线）、Follow-X 运营商差异化机制，
> 以及调用时必须遵守的约束与常见问题。
>
> 适用版本：OpenHarmony 4.0 / 5.0（API 8 起，Follow-X 系列 API 11 起）。
> 组件仓库：`base/customization/config_policy`，部件名 `config_policy`，子系统 `customization`。

---

## 一、组件用途

`config_policy` 提供**按系统预定义的"配置层级"获取配置目录与配置文件路径**的能力。

OpenHarmony 设备的配置文件分布在多个**分区（层级）**上，不同层级有固定的优先级。
业务模块只需提供配置文件的**相对路径**（如 `etc/telephony/config.json`），
组件负责按优先级在各层级目录中查找，返回实际存在的文件路径。

典型场景：系统/厂商把一份基线配置放在 `/system`，OEM 厂商或运营商通过更高优先级的层级
（如 `/sys_prod`、`/chip_prod`）覆盖其中部分配置，业务代码无需感知具体分区。

```
业务代码只提供：  etc/telephony/config.json

组件自动查找（优先级从高到低）：
  /chip_prod/etc/telephony/config.json   ← 最高优先级，优先命中
  /sys_prod/etc/telephony/config.json
  /chipset/etc/telephony/config.json
  /system/etc/telephony/config.json      ← 最低优先级（基线）

getOneCfgFile → 返回命中的最高优先级路径
getCfgFiles   → 返回所有命中路径（低→高顺序），供逐层合并
```

### 默认配置层级

| 优先级 | 层级目录 | 典型用途 |
|--------|----------|----------|
| 低 | `/system` | 系统基线配置 |
| ↓ | `/chipset` | 芯片平台配置 |
| ↓ | `/sys_prod` | 系统厂商定制 |
| 高 | `/chip_prod` | 芯片厂商定制 |

实际生效的层级由系统参数 `const.cust.config_dir_layer` 决定，未设置时回落到上表默认值。

---

## 二、两种使用路线的选择

| 你的代码形态 | 推荐路线 | 接口入口 |
|--------------|----------|----------|
| ArkTS 应用 / ArkTS 系统服务（FA/Stage 模型） | **ArkTS 接口** | `import { configPolicy } from '@kit.BasicServicesKit'` |
| C/C++ 系统服务、SA、native 部件 | **Native C 接口（inner_api）** | `#include "config_policy_utils.h"` |

> ⚠️ **重要前提**：`config_policy` 的 ArkTS 接口**均为系统接口（System API）**，
> 普通三方应用（normal 应用）无法调用。需要应用具备系统应用签名，
> 且工程使用 **Full SDK**（Public SDK 不包含系统接口）。
> 详见第六节"权限与签名要求"。

---

## 三、ArkTS 接口使用

### 3.1 导入模块

OpenHarmony API 9 及以后推荐通过 Kit 方式导入：

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';
```

> 早期写法 `import configPolicy from '@ohos.customization.configPolicy';` 仍兼容，
> 新工程请使用 Kit 写法。

- **系统能力（SysCap）**：`SystemCapability.Customization.ConfigPolicy`
- **错误码**：参数错误统一抛出 `401`（强制参数缺失 / 类型错误 / 参数校验失败）。

### 3.2 接口总览

| 接口 | 形式 | 起始版本 | 返回 |
|------|------|----------|------|
| `getOneCfgFile` | callback / promise | API 8 | 优先级最高的单个配置文件路径 |
| `getCfgFiles` | callback / promise | API 8 | 所有层级配置文件路径数组（低→高） |
| `getCfgDirList` | callback / promise | API 8 | 配置层级目录数组（低→高） |
| `getOneCfgFile`（带 followMode/extra） | callback / promise | API 11 | 同上，支持 Follow-X |
| `getCfgFiles`（带 followMode/extra） | callback / promise | API 11 | 同上，支持 Follow-X |
| `getOneCfgFileSync` | 同步 | API 11 | 同步返回单个路径 |
| `getCfgFilesSync` | 同步 | API 11 | 同步返回路径数组 |
| `getCfgDirListSync` | 同步 | API 11 | 同步返回目录数组 |

> 找不到文件时：`getOneCfgFile` 返回**空字符串 `""`**（不是异常）；`getCfgFiles` 返回**空数组 `[]`**。
> 业务代码务必判空。

---

### 3.3 getOneCfgFile — 获取最高优先级配置文件路径

```ts
getOneCfgFile(relPath: string, callback: AsyncCallback<string>): void
getOneCfgFile(relPath: string): Promise<string>
```

**功能**：在所有配置层级中查找 `relPath`，返回优先级最高的那个层级中该文件的完整路径。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `relPath` | string | 是 | 配置文件相对路径，如 `"etc/config.xml"`，**不以 `/` 开头** |

**Callback 示例**：

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

let relPath: string = 'etc/config.xml';
configPolicy.getOneCfgFile(relPath, (err: BusinessError, data: string) => {
  if (err == null) {
    if (data.length === 0) {
      console.info('该配置文件在任何层级都不存在');
    } else {
      console.info('最高优先级配置文件: ' + data);
    }
  } else {
    console.error('getOneCfgFile failed: ' + err.code + ', ' + err.message);
  }
});
```

**Promise 示例**：

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

async function fetchConfigFile(): Promise<void> {
  try {
    let value: string = await configPolicy.getOneCfgFile('etc/config.xml');
    if (value.length === 0) {
      console.info('配置文件不存在');
      return;
    }
    console.info('value is ' + value);
    // 拿到路径后即可用 @ohos.file.fs 读取该文件
  } catch (error) {
    let e = error as BusinessError;
    console.error('error: ' + e.code + ', ' + e.message);
  }
}
```

---

### 3.4 getCfgFiles — 获取所有层级的配置文件路径

```ts
getCfgFiles(relPath: string, callback: AsyncCallback<Array<string>>): void
getCfgFiles(relPath: string): Promise<Array<string>>
```

**功能**：返回**所有层级中存在**的该配置文件路径，按优先级**从低到高**排列。
适用于需要逐层叠加 / 合并配置的场景（后面的高优先级层覆盖前面的低优先级层）。

**Promise 示例**：

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

async function mergeConfigs(): Promise<void> {
  try {
    let files: Array<string> = await configPolicy.getCfgFiles('etc/plugin/rules.xml');
    if (files.length === 0) {
      console.info('任何层级均无此配置');
      return;
    }
    // files[0] 优先级最低，files[last] 优先级最高
    for (let i = 0; i < files.length; i++) {
      console.info(`[${i}] ${files[i]}`);
      // 按低→高顺序加载，高优先级覆盖低优先级
    }
  } catch (error) {
    let e = error as BusinessError;
    console.error('error: ' + e.code + ', ' + e.message);
  }
}
```

---

### 3.5 getCfgDirList — 获取所有配置层级目录

```ts
getCfgDirList(callback: AsyncCallback<Array<string>>): void
getCfgDirList(): Promise<Array<string>>
```

**功能**：返回当前设备生效的所有配置层级目录（不针对具体文件），按优先级从低到高。
常用于诊断"当前到底有哪些层级生效"。

**Promise 示例**：

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

async function fetchCfgDirList(): Promise<void> {
  try {
    let dirs: Array<string> = await configPolicy.getCfgDirList();
    console.info('当前配置层级（低→高）: ' + JSON.stringify(dirs));
    // 例如: ["/system","/chipset","/sys_prod","/chip_prod"]
  } catch (error) {
    let e = error as BusinessError;
    console.error('error: ' + e.code + ', ' + e.message);
  }
}
```

---

### 3.6 Follow-X：运营商差异化配置（API 11+）

某些配置文件随**运营商（opkey）**不同而不同。Follow-X 机制在标准层级路径中插入运营商子目录：

```
标准路径:  /sys_prod/etc/config.xml
Follow-X:  /sys_prod/etc/carrier/46060/etc/config.xml
                         ↑ 运营商代码（opkey），由 SIM 卡参数决定
```

#### FollowXMode 枚举

| 枚举 | 值 | 说明 |
|------|----|------|
| `configPolicy.FollowXMode.DEFAULT` | 0 | 默认。读取各层级下 `followx_file_list.cfg` 中配置的跟随规则 |
| `configPolicy.FollowXMode.NO_RULE_FOLLOWED` | 1 | 不跟随。即使存在 `followx_file_list.cfg` 也忽略，直接按层级查找 |
| `configPolicy.FollowXMode.SIM_DEFAULT` | 10 | 跟随默认卡，按默认卡 opkey 在 `etc/carrier/${opkey}` 下查找 |
| `configPolicy.FollowXMode.SIM_1` | 11 | 跟随卡 1 的 opkey（`telephony.sim.opkey0`） |
| `configPolicy.FollowXMode.SIM_2` | 12 | 跟随卡 2 的 opkey（`telephony.sim.opkey1`） |
| `configPolicy.FollowXMode.USER_DEFINED` | 100 | 用户自定义。由入参 `extra` 提供跟随规则，忽略 `followx_file_list.cfg` |

**带跟随模式的签名**：

```ts
// callback 形式
getOneCfgFile(relPath: string, followMode: FollowXMode, callback: AsyncCallback<string>): void
getOneCfgFile(relPath: string, followMode: FollowXMode, extra: string, callback: AsyncCallback<string>): void
// promise 形式（extra 可选）
getOneCfgFile(relPath: string, followMode: FollowXMode, extra?: string): Promise<string>
getCfgFiles(relPath: string, followMode: FollowXMode, extra?: string): Promise<Array<string>>
```

> ⚠️ 当 `followMode` 为 `USER_DEFINED` 时，`extra` **必填**，否则抛 `401`。其他模式下 `extra` 无意义。

**示例 1：跟随默认 SIM 卡运营商**

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

configPolicy.getOneCfgFile('etc/config.xml', configPolicy.FollowXMode.SIM_DEFAULT,
  (err: BusinessError, data: string) => {
    if (err == null) {
      console.info('运营商专属配置: ' + data);   // 命中如 /sys_prod/etc/carrier/46060/etc/config.xml
    } else {
      console.error('err: ' + err.code + ', ' + err.message);
    }
  });
```

**示例 2：用户自定义跟随规则（extra 中可带参数变量）**

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

async function fetchUserDefined(): Promise<void> {
  try {
    let extra: string = 'etc/carrier/${telephony.sim.opkey0}';   // ${} 内为系统参数名，会被解析替换
    let value: string = await configPolicy.getOneCfgFile(
      'etc/config.xml', configPolicy.FollowXMode.USER_DEFINED, extra);
    console.info('value is ' + value);
  } catch (error) {
    let e = error as BusinessError;
    console.error('error: ' + e.code + ', ' + e.message);
  }
}
```

---

### 3.7 同步接口（Sync，API 11+）

同步接口直接返回结果，无 callback/promise。适合在已知耗时可接受、非 UI 阻塞的场景使用。
找不到时分别返回 `""` 或 `[]`，参数非法抛 `401`。

```ts
import { configPolicy, BusinessError } from '@kit.BasicServicesKit';

try {
  // 1. 单文件（followMode、extra 均可省略）
  let one: string = configPolicy.getOneCfgFileSync('etc/config.xml');

  // 2. 单文件 + 用户自定义跟随
  let extra: string = 'etc/carrier/${telephony.sim.opkey0}';
  let one2: string = configPolicy.getOneCfgFileSync(
    'etc/config.xml', configPolicy.FollowXMode.USER_DEFINED, extra);

  // 3. 所有层级文件列表
  let files: Array<string> = configPolicy.getCfgFilesSync('etc/config.xml');

  // 4. 配置层级目录
  let dirs: Array<string> = configPolicy.getCfgDirListSync();

  console.info(`one=${one}, files=${files.length}, dirs=${dirs.length}`);
} catch (error) {
  let e = error as BusinessError;
  console.error('error: ' + e.code + ', ' + e.message);
}
```

---

## 四、Native C 接口使用（inner_api）

C/C++ 系统服务可直接调用底层接口，避免 ArkTS 跨语言开销。

### 4.1 BUILD.gn 依赖

```gn
import("//build/ohos.gni")

ohos_shared_library("your_service") {
  sources = [ "src/your_service.cpp" ]

  external_deps = [
    "config_policy:configpolicy_util",   # ← 依赖 inner_api
  ]

  subsystem_name = "your_subsystem"
  part_name = "your_part"
}
```

`bundle.json` 的 `deps.components` 中加入 `"config_policy"`。

头文件来自组件的 `inner_kits`：

```cpp
#include "config_policy_utils.h"
```

### 4.2 接口与内存模型

| 函数 | 返回内存 | 释放方式 |
|------|----------|----------|
| `GetCfgDirList()` | 堆分配 `CfgDir*` | `FreeCfgDirList()`，**禁止单独 free `paths[i]`** |
| `GetOneCfgFile()` / `GetOneCfgFileEx()` | 指向**调用方传入的 buf** | 不需要 free |
| `GetCfgFiles()` / `GetCfgFilesEx()` | 堆分配 `CfgFiles*` | `FreeCfgFiles()` |

> 关键差异：`CfgDir->paths[]` 各元素指向 `realPolicyValue` 内部（原地切割冒号分隔串），
> **不是独立分配**，单独 `free` 会导致堆损坏；而 `CfgFiles->paths[]` 每个都是独立 `strdup`。

### 4.3 示例

```cpp
#include <cstdio>
#include "config_policy_utils.h"

void Demo()
{
    // 1. 最高优先级单文件（buf 由调用方提供，建议 MAX_PATH_LEN）
    char buf[MAX_PATH_LEN] = {0};
    char *one = GetOneCfgFile("etc/config.xml", buf, MAX_PATH_LEN);
    if (one != nullptr) {
        printf("highest: %s\n", one);   // one == buf，无需 free
    }

    // 2. 带 Follow-X：默认卡运营商
    char buf2[MAX_PATH_LEN] = {0};
    char *carrier = GetOneCfgFileEx("etc/config.xml", buf2, MAX_PATH_LEN,
                                    FOLLOWX_MODE_SIM_DEFAULT, nullptr);
    (void)carrier;

    // 3. 所有层级文件列表
    CfgFiles *files = GetCfgFiles("etc/config.xml");
    if (files != nullptr) {
        for (size_t i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
            if (files->paths[i] != nullptr) {
                printf("file[%zu]: %s\n", i, files->paths[i]);
            }
        }
        FreeCfgFiles(files);   // ← 必须
    }

    // 4. 配置层级目录
    CfgDir *dirs = GetCfgDirList();
    if (dirs != nullptr) {
        for (size_t i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
            if (dirs->paths[i] != nullptr) {
                printf("dir[%zu]: %s\n", i, dirs->paths[i]);
            }
        }
        FreeCfgDirList(dirs);   // ← 必须，且禁止单独 free paths[i]
    }
}
```

> C 接口的 `followMode` 取值常量定义在 `config_policy_utils.h`：
> `FOLLOWX_MODE_DEFAULT(0)` / `FOLLOWX_MODE_NO_RULE_FOLLOWED(1)` /
> `FOLLOWX_MODE_SIM_DEFAULT(10)` / `FOLLOWX_MODE_SIM_1(11)` / `FOLLOWX_MODE_SIM_2(12)` /
> `FOLLOWX_MODE_USER_DEFINED(100)`。

---

## 五、customConfig：获取渠道号 getChannelId

组件还提供一个面向应用渠道定制的轻量接口 `customConfig.getChannelId()`，
读取系统参数 `const.channelid.<bundleName>`，返回当前应用的渠道号。

```ts
import { customConfig } from '@kit.BasicServicesKit';

let channelId: string = customConfig.getChannelId();   // 同步，无渠道号或在预置列表中时返回 ""
console.info('channelId = ' + channelId);
```

> - SysCap：`SystemCapability.Customization.CustomConfig`。
> - 内部会基于当前应用的 bundleName 取参；若应用在 `persist.custom.preload.list` 预置列表中，返回空串。

---

## 六、权限与签名要求

1. **系统接口限制**：`configPolicy` / `customConfig` 的 ArkTS 接口均为 System API，
   仅系统应用可调用。需要：
   - 使用 **Full SDK**（在 DevEco Studio 中切换；Public SDK 编译会报 "Cannot find name 'configPolicy'"）。
   - 应用以**系统应用证书**签名（`app-feature` 为 `hos_system_app`）。
2. **配置文件的可访问性**：返回的路径指向系统分区，应用进程需对该路径有读权限。
   配置文件通常预置在系统镜像中，由系统集成方保证可读。
3. **无需申请额外 `ohos.permission.*`**：本组件接口本身不挂权限，门槛在"系统应用"身份。

---

## 七、运行环境前提

组件依赖 `init` 子系统的系统参数能力（`SystemGetParameter`）读取层级配置：

```bash
# 查看实际生效的配置层级
hdc shell param get const.cust.config_dir_layer

# 查看默认 Follow-X 规则
hdc shell param get const.cust.follow_x_rules

# Follow-X SIM 模式依赖运营商参数（由 telephony 子系统设置）
hdc shell param get telephony.sim.opkey0
hdc shell param get telephony.sim.opkey1
```

若 `const.cust.config_dir_layer` 未设置，组件回落到编译期默认层级
（`/system:/chipset:/sys_prod:/chip_prod`），接口不会崩溃，但层级可能与你的实际分区不符。

---

## 八、常见问题

### Q1：ArkTS 中 `configPolicy` 未定义 / 编译报错找不到模块

未使用 Full SDK，或应用非系统应用。切换 Full SDK 并使用系统应用签名。

### Q2：所有接口都返回空（`""` / `[]`）

- 查询的相对路径确实不存在于任何层级目录；
- 或层级参数未正确设置（用 `getCfgDirListSync()` / `GetCfgDirList()` 先确认当前层级）；
- 相对路径写法错误（**不能以 `/` 开头**）：

```ts
configPolicy.getOneCfgFileSync('etc/config.xml');   // ✓
configPolicy.getOneCfgFileSync('/etc/config.xml');  // ✗
```

### Q3：Follow-X SIM 模式取不到运营商配置

确认 `telephony.sim.opkey0/1` 已由 telephony 子系统写入，且配置文件实际存在于
`<层级>/etc/carrier/<opkey>/<relPath>`。可临时验证：

```bash
hdc shell param set telephony.sim.opkey0 46060
```

### Q4：`USER_DEFINED` 模式报 401

`followMode` 为 `USER_DEFINED` 时 `extra` 必填，且需符合跟随规则格式
（可含 `${参数名}` 或 `${参数名:-默认值}` 变量）。

### Q5：Native 侧偶发崩溃 / double-free

最常见原因是对 `GetCfgDirList()` 的 `paths[i]` 单独调用了 `free()`。
`CfgDir->paths[]` 指向 `realPolicyValue` 内部，**只能**用 `FreeCfgDirList()` 统一释放。

### Q6：`getOneCfgFile` 返回值（Native）在函数外失效

C 接口返回值指向传入的栈 `buf`，函数返回后失效。需持久保存时 `strdup` 一份并自行 `free`。

---

## 九、接口速查表（ArkTS）

| 接口 | 入参 | 返回 | 找不到时 |
|------|------|------|----------|
| `getOneCfgFile(relPath[, followMode[, extra]])` | 相对路径(+跟随模式) | `Promise<string>` / callback | `""` |
| `getOneCfgFileSync(relPath[, followMode[, extra]])` | 同上 | `string` | `""` |
| `getCfgFiles(relPath[, followMode[, extra]])` | 同上 | `Promise<Array<string>>` / callback | `[]` |
| `getCfgFilesSync(relPath[, followMode[, extra]])` | 同上 | `Array<string>` | `[]` |
| `getCfgDirList()` | 无 | `Promise<Array<string>>` / callback | `[]` |
| `getCfgDirListSync()` | 无 | `Array<string>` | `[]` |
| `customConfig.getChannelId()` | 无 | `string` | `""` |

---

## 参考资料

- OpenHarmony 官方文档：@ohos.configPolicy（配置策略，系统接口）— `zh-cn/application-dev/reference/apis-basic-services-kit/js-apis-configPolicy-sys.md`
- 组件源码：`base/customization/config_policy`（`config_policy_utils.c` / `config_policy_napi.cpp` / `custom_config_napi.cpp`）
- 头文件：`interfaces/inner_api/include/config_policy_utils.h`
