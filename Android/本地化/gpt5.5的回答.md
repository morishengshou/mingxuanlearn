下面按 **AOSP/Android Framework 系统开发视角** 来拆解这个需求：  
目标是把“系统语言/Locale 原来跟随 Android userId / 用户空间”改成“跟随自研账户 accountId 登录状态”。

---

# 1. 需求本质

Android 原生的系统语言配置，本质上是 **按 userId 隔离** 的。

也就是说，系统中很多 Locale 相关配置目前默认是：

```text
userId -> LocaleList / Configuration
```

例如：

- user 0 设置中文
- user 10 设置英文
- 切换 Android 用户空间后，系统加载对应 userId 的语言配置

而你现在要改成：

```text
accountId -> LocaleList / Configuration
```

并且：

```text
Android userId 不变
登录账户 A -> 中文
登录账户 B -> 英文
登录账户 C -> 日文
```

也就是：

> Android 用户空间不切换，但系统语言要随着业务账户登录/切换而切换。

---

# 2. 需要先明确的设计边界

这个需求不建议直接把 Android Framework 里的 `userId` 语义整体替换成 `accountId`。

更合理的设计是：

```text
Android userId 仍然是系统隔离维度
AccountId 是业务语言配置维度
```

即：

```text
userId + accountId -> LocaleList
```

原因是：

- Android Framework 仍然大量依赖 userId 做权限、存储、Settings、Package、AMS/WMS 隔离
- 账户系统是业务概念，不应侵入所有 Android 多用户模型
- 同一个 Android userId 下可以登录不同 account
- 不同 Android userId 下可能也能登录同一个 account，是否共享语言策略要单独定义

推荐的数据模型是：

```text
locale(accountId)
```

或者更严谨：

```text
locale(androidUserId, accountId)
```

如果你们的账户全局唯一且跨用户空间共享，可以用：

```text
accountId -> locale
```

如果需要避免不同 Android 用户空间之间数据串扰，建议用：

```text
userId + accountId -> locale
```

---

# 3. 当前 Android 语言设置链路概览

Android 系统语言通常涉及以下链路：

```text
Settings App
  -> LocalePicker / LocalePickerWithRegion
  -> LocaleManager / ActivityManager
  -> ActivityTaskManager / ActivityManagerService
  -> Configuration
  -> system Settings / user config
  -> Resources.updateConfiguration
  -> App 进程 ConfigurationChanged
  -> SystemUI / Launcher / Settings / Framework UI 刷新
```

典型调用路径可能包括：

```java
LocalePicker.updateLocales(LocaleList locales)
ActivityManager.getService().updatePersistentConfiguration(config)
ActivityTaskManager.getService().updateConfiguration(config)
```

底层会更新：

```java
Configuration.locales
```

最终影响：

```java
Resources
Context
AssetManager
SystemUI
Launcher
App label
WebView / ICU / DateFormat
InputMethod
```

---

# 4. 原生“随用户空间切换语言”的关键点

Android 多用户下，语言一般和当前 userId 的配置绑定。

常见持久化位置包括：

```text
Settings.System
Settings.Secure
Settings.Global
UserManager / user config
system settings provider per-user database
```

系统用户切换时，会触发类似：

```text
ACTION_USER_SWITCHED
ActivityManagerService.switchUser()
UserController
load user-specific settings/configuration
update Configuration
```

因此原来模型是：

```text
switch Android user
  -> load locale for target user
  -> apply locale to system configuration
```

现在要改成：

```text
switch login account
  -> load locale for target account
  -> apply locale to current Android user/system configuration
```

---

# 5. 需要适配的模块

## 5.1 自研账户模块

需要提供能力：

```java
String getCurrentAccountId();
void addAccountSwitchListener(AccountSwitchListener listener);
LocaleList getAccountLocales(String accountId);
void setAccountLocales(String accountId, LocaleList locales);
```

账户切换时需要发出系统内可信事件，例如：

```text
com.xxx.intent.action.ACCOUNT_SWITCHED
```

或者更建议使用系统服务 Binder 回调：

```java
IAccountManagerInternal
IAccountSwitchObserver
```

不要单纯依赖普通广播，因为系统语言切换是高权限操作，广播容易被第三方伪造或监听。

---

## 5.2 Settings 应用语言设置页

原来用户在 Settings 里设置语言时，大概率是写入当前 Android user 的语言配置。

需要改成：

```text
设置语言
  -> 获取当前登录 accountId
  -> 保存到 accountId 维度
  -> 同时应用到当前系统 Configuration
```

原来的逻辑可能是：

```java
LocalePicker.updateLocales(locales);
```

改造后应该变成：

```java
String accountId = AccountService.getCurrentAccountId();
AccountLocaleManager.setLocalesForAccount(accountId, locales);
AccountLocaleManager.applyLocalesForCurrentAccount();
```

也就是说，语言设置 UI 不再直接认为“当前用户空间 = 配置归属者”。

需要改造点：

- 设置页读取语言时，从 account locale 读取
- 设置页保存语言时，保存到 account locale
- 当前无登录账户时的 fallback 行为
- 账户切换后 Settings 页面刷新
- 多账户语言显示逻辑

---

## 5.3 Framework Locale 持久化逻辑

建议新增一个系统级服务或内部管理类：

```java
AccountLocaleManagerService
```

职责：

```text
1. 维护 accountId -> LocaleList 映射
2. 监听账户登录/登出/切换
3. 在账户切换时应用对应 LocaleList
4. 对 Settings App 或系统组件提供 Binder API
5. 处理 fallback/default locale
6. 控制权限
```

示例接口：

```aidl
interface IAccountLocaleManager {
    LocaleList getLocalesForAccount(String accountId);
    void setLocalesForAccount(String accountId, in LocaleList locales);
    LocaleList getCurrentAccountLocales();
    void applyLocalesForCurrentAccount();
}
```

权限建议：

```text
android.permission.CHANGE_CONFIGURATION
自定义签名权限：com.xxx.permission.MANAGE_ACCOUNT_LOCALE
```

---

## 5.4 SettingsProvider / 数据存储

原生 SettingsProvider 是 per-user 的，比如：

```text
/data/system/users/0/settings_secure.xml
/data/system/users/10/settings_secure.xml
```

如果直接继续使用 SettingsProvider，则仍然是 per-user 维度，不满足“随账户”。

可以有两种方案。

---

### 方案 A：继续使用 SettingsProvider，但 key 中带 accountId

例如：

```text
Settings.Secure.ACCOUNT_LOCALE_accountA = zh-CN
Settings.Secure.ACCOUNT_LOCALE_accountB = en-US
```

优点：

- 改动较小
- 利用已有 SettingsProvider
- 备份/权限/观察者机制相对现成

缺点：

- 本质仍然存储在当前 Android user 下
- accountId 如果包含敏感信息，需要脱敏/hash
- 多 Android user 下同一 account 是否共享不好处理

---

### 方案 B：新增账户配置存储

例如：

```text
/data/system/account_locale/account_locale.xml
```

或：

```text
/data/system/users/{userId}/account_locale.xml
```

推荐结构：

```xml
<account-locales>
    <account id_hash="xxx" locales="zh-CN,en-US"/>
    <account id_hash="yyy" locales="ja-JP"/>
</account-locales>
```

优点：

- 账户维度清晰
- 不强依赖 SettingsProvider per-user 模型
- 可以独立做加密、迁移、清除

缺点：

- 需要新增读写、锁、备份、迁移逻辑
- 需要考虑系统服务启动时机

---

## 5.5 AMS / ATMS / Configuration 更新

账户切换后，最终还是必须更新 Android 的全局 Configuration：

```java
Configuration config = new Configuration();
config.setLocales(accountLocales);
ActivityManager.getService().updatePersistentConfiguration(config);
```

或者 Framework 内部调用：

```java
ActivityTaskManagerService.updateConfigurationLocked(...)
ActivityManagerService.updatePersistentConfiguration(...)
```

注意点：

- 是否 persistent
- 是否写回原生 per-user locale
- 是否触发 app relaunch / onConfigurationChanged
- 是否更新 SystemUI
- 是否更新 Launcher
- 是否影响未登录状态

这里是关键设计点：

## 不建议账户切换时调用原生 persistent user locale 写入

如果调用：

```java
updatePersistentConfiguration(config)
```

它可能会把语言重新写回当前 user 的持久化配置。

这会导致：

```text
用户空间 0 的语言也被改成 account B 的语言
```

当重启后、无账户登录时，可能读到最后一次账户语言。

更好的做法是区分：

```text
account locale application
```

和

```text
user persistent locale
```

也就是：

- 用户手动设置账户语言：写账户 locale
- 系统当前 Configuration：立即应用
- 是否写 Android user persistent locale：需要谨慎，最好不要作为真实来源

如果必须使用原生 `updatePersistentConfiguration()` 才能完整刷新系统，则需要在系统启动/账户登录后再次覆盖为账户语言。

---

## 5.6 SystemServer 启动流程

需要处理开机后的语言来源。

原来：

```text
开机
  -> 加载当前 user locale
  -> 应用系统语言
```

改造后：

```text
开机
  -> 加载 Android user 默认 locale
  -> 等待账户系统 ready
  -> 获取当前登录账户
  -> 加载 account locale
  -> 覆盖当前 Configuration
```

需要定义：

| 场景 | 行为 |
|---|---|
| 开机无账户登录 | 使用设备默认语言 / user locale |
| 开机自动登录账户 A | 应用账户 A 语言 |
| 账户服务晚于 SystemUI 启动 | 后续二次刷新语言 |
| 账户数据损坏 | fallback 到默认语言 |
| 账户登出 | 回到默认语言或保持最后语言 |

---

# 6. 需要关注的具体类/模块

不同 Android 版本类名略有变化，但大体涉及以下。

---

## 6.1 Settings App

可能涉及：

```text
packages/apps/Settings
```

常见类：

```text
LocalePicker
LocalePickerWithRegion
LocaleDragAndDropAdapter
LanguageAndInputSettings
SystemDashboardFragment
```

Framework 里的 locale UI 类可能在：

```text
frameworks/base/core/java/com/android/internal/app/LocalePicker.java
frameworks/base/core/java/com/android/internal/app/LocalePickerWithRegion.java
```

修改点：

- 读取当前语言来源
- 保存语言到 account
- 语言排序/删除/添加后更新账户配置
- 与账户切换事件联动刷新

---

## 6.2 Framework Locale 相关

可能涉及：

```text
frameworks/base/core/java/android/app/LocaleManager.java
frameworks/base/core/java/android/app/ILocaleManager.aidl
frameworks/base/services/core/java/com/android/server/locales/LocaleManagerService.java
frameworks/base/core/java/android/content/res/Configuration.java
frameworks/base/core/java/android/os/LocaleList.java
```

如果 Android 版本较新，`LocaleManagerService` 主要也承担 app-specific locale 管理，需要注意不要混淆：

```text
system locale
app locale
```

你的需求是 **system locale 随账户切换**，不是单个 app 的 locale。

---

## 6.3 ActivityManager / ActivityTaskManager

可能涉及：

```text
frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java
frameworks/base/services/core/java/com/android/server/wm/WindowProcessController.java
frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java
```

关注点：

- `updateConfiguration`
- `updatePersistentConfiguration`
- `sendConfigurationChanged`
- app 进程收到 configuration 变化
- 多 display / multi-window 下配置传播

通常不建议大改 AMS/ATMS，只是在新增服务里调用现有 Configuration 更新接口。

---

## 6.4 UserController / 用户切换逻辑

可能涉及：

```text
frameworks/base/services/core/java/com/android/server/am/UserController.java
frameworks/base/services/core/java/com/android/server/pm/UserManagerService.java
```

原来 user switch 时可能会刷新 locale。

你需要确认：

```text
ACTION_USER_SWITCHED / switchUser
```

之后是否会覆盖账户语言。

如果 Android 用户空间切换仍然存在，则流程应变成：

```text
Android user switch
  -> 切到 user 默认配置
  -> 查询该 user 下当前登录 account
  -> 如果有 account locale，覆盖
```

否则用户空间切换可能把 account locale 冲掉。

---

## 6.5 SettingsProvider

可能涉及：

```text
frameworks/base/packages/SettingsProvider
```

关注点：

- 原 locale 配置在哪里保存
- 是否需要迁移原 per-user 语言到首个 account
- 是否增加 account locale key
- 是否需要监听变化

---

## 6.6 SystemUI / Launcher

可能涉及：

```text
frameworks/base/packages/SystemUI
packages/apps/Launcher3
```

理论上系统 Configuration 更新后它们会刷新，但要验证：

- 状态栏日期/时间语言是否刷新
- 锁屏日期格式是否刷新
- QS Tile 文案是否刷新
- Launcher app label 是否刷新
- 最近任务界面是否刷新
- 通知中已有文本是否刷新

很多组件可能不会完整重建，需要手动监听：

```text
onConfigurationChanged()
```

或主动重启相关进程。

---

## 6.7 输入法与语音

语言切换不只是界面文案，还可能影响：

```text
InputMethodManagerService
SpellChecker
TextServicesManagerService
VoiceInteractionManagerService
TTS
```

需要确认产品预期：

| 项目 | 是否随账户语言切换 |
|---|---|
| UI 显示语言 | 是 |
| 默认输入法语言 | 可能 |
| 键盘布局 | 可能 |
| 拼写检查语言 | 可能 |
| TTS 语言 | 可能 |
| 语音助手语言 | 可能 |

如果只要求“系统显示语言”，不要把输入法语言也强绑，否则范围会扩大很多。

---

## 6.8 日期、时间、数字格式

Locale 切换会影响：

```text
DateFormat
NumberFormat
Calendar
ICU
TimeZoneNames
```

需要验证：

- 12/24 小时制是否保持原设置
- 日期格式是否随语言变
- 星期/月名称是否刷新
- 数字、货币格式是否刷新

---

## 6.9 App 侧影响

系统语言切换后，三方 app 会收到 Configuration 变化：

```java
onConfigurationChanged(Configuration newConfig)
```

或 Activity 重建。

风险：

- 当前前台 app 被重建
- 表单状态丢失
- app 未适配 configChanges
- WebView 页面语言不刷新
- 部分 app 缓存 Locale

如果账户切换发生在运行中，需要产品接受“切换账户可能导致界面刷新/Activity 重建”。

---

# 7. 核心业务逻辑需要怎么改

可以抽象为以下流程。

---

## 7.1 设置语言流程

原流程：

```text
用户进入设置
  -> 选择语言
  -> 写当前 user locale
  -> update system configuration
```

新流程：

```text
用户进入设置
  -> 获取当前 accountId
  -> 选择语言
  -> 写 account locale
  -> apply account locale to current Configuration
  -> 通知系统 UI/app 刷新
```

伪代码：

```java
public void onUserSelectLocales(LocaleList locales) {
    int userId = UserHandle.myUserId();
    String accountId = mAccountService.getCurrentAccountId(userId);

    if (TextUtils.isEmpty(accountId)) {
        // fallback: 写设备默认语言或禁止修改
        mDefaultLocaleStore.setLocales(userId, locales);
    } else {
        mAccountLocaleStore.setLocales(userId, accountId, locales);
    }

    mAccountLocaleManager.applyLocales(userId, accountId, locales);
}
```

---

## 7.2 账户切换流程

```text
账户 A -> 账户 B
  -> AccountService 发出账户切换事件
  -> AccountLocaleManager 收到事件
  -> 查询 B 的 locale
  -> 如果 B 没有 locale，则使用默认 locale 或初始化
  -> 更新系统 Configuration
  -> 通知 Settings/SystemUI/Launcher
```

伪代码：

```java
public void onAccountSwitched(String oldAccountId, String newAccountId, int userId) {
    LocaleList locales = mStore.getLocales(userId, newAccountId);

    if (locales == null || locales.isEmpty()) {
        locales = getFallbackLocales(userId);
        mStore.setLocales(userId, newAccountId, locales);
    }

    applyLocalesToSystem(locales);
}
```

---

## 7.3 登出流程

要定义登出后语言行为：

### 方案 1：回到设备默认语言

```text
账户登出 -> locale = device default
```

优点：语义清晰。

缺点：退出瞬间系统语言变化，用户可能困惑。

### 方案 2：保持最后一个账户语言

```text
账户登出 -> 保持当前语言
```

优点：体验平滑。

缺点：登录页可能显示上个账户语言。

### 方案 3：登录页使用系统默认语言，登录后账户语言

推荐：

```text
未登录态使用 device/user default locale
已登录态使用 account locale
```

---

## 7.4 新账户首次登录

需要定义初始化规则：

```text
新 account 第一次登录
  -> 如果服务端有账户语言，使用服务端语言
  -> 否则使用当前系统语言作为初始账户语言
  -> 或使用设备默认语言
```

推荐：

```text
首次登录 account locale = 当前系统 locale
```

这样不会突然切语言。

---

## 7.5 账户语言同步

如果账户系统有云同步能力，需要决定：

```text
account locale 是否跟随账户跨设备同步？
```

如果同步，逻辑是：

```text
登录账户
  -> 先用本地 cached locale
  -> 拉取云端 locale
  -> 如果云端不同，是否立即切换？
```

建议：

- 登录瞬间先用本地
- 云端返回后如不同，弹提示或静默切换，视产品定义
- 避免短时间连续切换语言

---

# 8. 推荐架构

建议新增一个中间层：

```text
AccountLocaleManagerService
```

而不是把 account 逻辑散落到 Settings、AMS、UserController。

架构：

```text
AccountService
      |
      | account switch callback
      v
AccountLocaleManagerService
      |
      | read/write
      v
AccountLocaleStore
      |
      | apply
      v
ActivityManager / ActivityTaskManager Configuration
      |
      v
SystemUI / Launcher / Apps
```

---

# 9. 需要修改或新增的类示例

下面给出一个典型清单。

---

## 9.1 新增

```text
frameworks/base/core/java/android/app/IAccountLocaleManager.aidl
frameworks/base/core/java/android/app/AccountLocaleManager.java
frameworks/base/services/core/java/com/android/server/locales/AccountLocaleManagerService.java
frameworks/base/services/core/java/com/android/server/locales/AccountLocaleStore.java
```

如果账户系统在 framework：

```text
frameworks/base/core/java/android/accounts/xxx/IInternalAccountService.aidl
frameworks/base/services/core/java/com/android/server/accounts/xxx/AccountService.java
```

权限：

```text
frameworks/base/core/res/AndroidManifest.xml
```

新增：

```xml
<permission
    android:name="com.xxx.permission.MANAGE_ACCOUNT_LOCALE"
    android:protectionLevel="signature|privileged" />
```

SystemServer 注册：

```text
frameworks/base/services/java/com/android/server/SystemServer.java
```

---

## 9.2 修改

### Settings

```text
packages/apps/Settings/src/com/android/settings/localepicker/...
packages/apps/Settings/src/com/android/settings/language/...
```

或：

```text
frameworks/base/core/java/com/android/internal/app/LocalePicker.java
frameworks/base/core/java/com/android/internal/app/LocalePickerWithRegion.java
```

修改：

- 读取 account locale
- 保存 account locale
- 调用 AccountLocaleManager

---

### Framework API

```text
frameworks/base/core/java/android/app/LocaleManager.java
frameworks/base/core/java/android/app/ActivityManager.java
```

不一定要改公开 API，可以使用 internal API。

---

### Services

```text
frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java
frameworks/base/services/core/java/com/android/server/am/UserController.java
```

建议只做少量 hook：

- 用户切换后重新 apply account locale
- 配置更新时避免账户 locale 被 user locale 覆盖
- 必要时新增内部 apply 方法

---

### SettingsProvider

```text
frameworks/base/packages/SettingsProvider/...
```

如果采用 SettingsProvider 存储，需要新增 key 或迁移逻辑。

---

### SystemUI / Launcher

```text
frameworks/base/packages/SystemUI/...
packages/apps/Launcher3/...
```

通常以测试修复为主：

- 检查 `onConfigurationChanged`
- 修复缓存字符串
- 刷新日期格式和 app label

---

# 10. 关键难点

## 10.1 “持久化配置”与“当前生效配置”的冲突

Android 原生假设：

```text
当前系统 locale = 当前 user 持久化 locale
```

现在你要改成：

```text
当前系统 locale = 当前 account locale
```

这会导致原生 persistent configuration 机制不再完全适用。

解决方案：

```text
账户语言作为 source of truth
系统 Configuration 只是运行时应用结果
```

并且在以下时机重新 apply：

- 开机账户 ready
- 账户登录
- 账户切换
- Android user 切换
- Settings 语言修改
- framework configuration 被其他路径修改后

---

## 10.2 其他路径修改系统语言

除了 Settings App，可能还有：

```text
adb shell settings put system system_locales ...
adb shell am update-config
DevicePolicyManager
SetupWizard
OEM 工具
恢复出厂设置流程
```

需要统一收口。

否则会出现：

```text
Settings 显示账户语言
实际系统语言被其他模块改掉
```

建议：

- 正式入口走 AccountLocaleManager
- 监控系统 locale 被外部修改
- 如果当前已登录账户，则同步回当前账户 locale
- 或禁止非账户路径修改

---

## 10.3 权限和安全

必须防止普通 app 切换系统语言。

建议：

```text
setAccountLocales()
```

要求：

```text
signature permission
MANAGE_ACCOUNT_LOCALE
CHANGE_CONFIGURATION
```

并限制调用方：

```text
Settings
SystemUI
AccountService
system_server
```

---

## 10.4 账户 ID 隐私

不要明文存储账户名、手机号、邮箱。

建议：

```text
accountKey = HMAC(accountId, deviceSecret)
```

存储：

```text
accountKey -> locales
```

---

## 10.5 恢复出厂设置和账户删除

需要处理：

```text
删除账户 -> 删除对应 locale 配置
恢复出厂 -> 清除所有 account locale
清除账户数据 -> 是否清除 locale
```

---

# 11. 测试用例

## 11.1 基础功能

| 用例 | 预期 |
|---|---|
| 登录账户 A，设置中文 | 系统中文，A 记录中文 |
| 切到账户 B，设置英文 | 系统英文，B 记录英文 |
| 切回账户 A | 系统恢复中文 |
| 重启后自动登录 A | 系统中文 |
| 登出 A | 按定义回默认语言或保持 |

---

## 11.2 多用户空间

| 用例 | 预期 |
|---|---|
| user 0 登录 A 设置中文 | user 0 + A 中文 |
| user 10 登录 A | 是否中文取决于设计 |
| user 0 切 user 10 | 语言不应被错误覆盖 |
| user 10 切回 user 0 | 恢复 user 0 当前账户语言 |

---

## 11.3 异常场景

| 场景 | 预期 |
|---|---|
| account locale 文件损坏 | fallback |
| accountId 为空 | fallback |
| Locale tag 非法 | 忽略或修正 |
| 账户切换过程中 Settings 正在改语言 | 加锁保证最终一致 |
| 连续快速切账户 | 最终语言等于最后账户 |
| SystemUI 未刷新 | 修复 onConfigurationChanged |

---

## 11.4 兼容测试

需要跑：

```text
CTS / GTS / VTS 相关 locale/configuration 测试
Settings 单测
SystemUI monkey
多语言切换稳定性
```

重点关注：

- `Configuration` 变更广播
- app 资源刷新
- per-app language
- 多用户相关 CTS
- 设备所有者/企业策略

---

# 12. 工作量评估

按中等复杂度 Android 定制系统评估。

---

## 方案一：轻量方案

特点：

```text
SettingsProvider 中以 accountId key 保存 locale
账户切换时调用现有 updateConfiguration
不大改 Framework
```

工作内容：

- Settings 语言页改造
- 账户切换监听
- 新增 AccountLocaleManager 简单封装
- 存储 account locale
- 切账户 apply locale
- 基础测试

预估：

```text
开发：2 ~ 3 周
联调：1 ~ 2 周
测试修复：2 周
总计：5 ~ 7 周
```

风险：

- 启动时序问题
- 原生 user locale 覆盖 account locale
- 部分系统 UI 刷新不彻底

适合：

```text
产品只要求当前用户空间下账户切换语言
不严格要求多用户空间/云同步/复杂权限
```

---

## 方案二：标准方案，推荐

特点：

```text
新增 AccountLocaleManagerService
账户语言成为独立 source of truth
Framework 有明确 hook
Settings/SystemUI/UserSwitch 适配完整
```

工作内容：

- 新增系统服务
- 新增存储模块
- 新增权限
- Settings 接入
- 账户服务回调
- SystemServer 启动接入
- User switch 后重新 apply
- 外部修改语言路径收口
- SystemUI/Launcher 修复
- 完整测试

预估：

```text
开发：4 ~ 6 周
联调：2 ~ 3 周
测试修复：3 ~ 4 周
总计：9 ~ 13 周
```

风险中等，但架构清晰，后续可维护。

---

## 方案三：深度 Framework 改造

特点：

```text
将 Locale 在 Framework 内部从 userId 维度彻底抽象为 accountId 维度
```

会涉及：

- AMS/ATMS 配置持久化模型
- SettingsProvider 模型
- UserController
- LocaleManagerService
- Backup/Restore
- CTS 兼容
- 多用户多账户复杂组合

预估：

```text
开发：8 ~ 12 周
联调：4 ~ 6 周
测试修复：6 ~ 8 周
总计：18 ~ 26 周
```

风险高，不推荐，除非你们系统深度去 Google 化且账户体系已是系统主身份。

---

# 13. 推荐落地方案

我建议采用 **方案二：新增 AccountLocaleManagerService**。

核心原则：

```text
不要改 Android userId 语义
不要把 accountId 塞进所有 Framework 多用户逻辑
只把 system locale 的 source of truth 从 user locale 改为 account locale
```

推荐最终行为：

```text
未登录：
    使用设备默认语言或当前 Android user 默认语言

登录账户：
    使用账户语言

切换账户：
    立即应用新账户语言

修改语言：
    修改当前账户语言，不修改 Android user 语言作为主数据

Android user 切换：
    先切 user，再根据该 user 当前登录账户 apply account locale
```

---

# 14. 总结

这个需求需要适配的核心不是 `LocaleList` 本身，而是 **语言配置的归属维度**。

你要完成三件事：

1. **存储解耦**
   ```text
   从 userId -> locale
   改成 accountId 或 userId + accountId -> locale
   ```

2. **触发源解耦**
   ```text
   从 Android user switch 触发
   改成 account login/switch 触发
   ```

3. **系统生效链路复用**
   ```text
   仍然通过 Configuration.locales 更新系统资源
   让 SystemUI、Launcher、App 走原生配置刷新机制
   ```

涉及重点模块：

```text
AccountService
Settings App
LocalePicker
LocaleManager / 新 AccountLocaleManagerService
SettingsProvider 或新增 AccountLocaleStore
ActivityManagerService
ActivityTaskManagerService
UserController
SystemServer
SystemUI
Launcher
InputMethod / TextServices 可选
```

推荐工作量：

```text
标准可维护实现：约 9 ~ 13 周
轻量实现：约 5 ~ 7 周
深度 Framework 改造：约 18 ~ 26 周
```