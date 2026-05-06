*Thinking...*

> **Considering Android development response**
> 
> I need to provide an answer in Chinese while discussing Android system development, which is technical and changes quite a bit. I’m wondering if I have to use the web since the user didn’t ask for the latest version, but details about the Android framework might require primary sources.
> 
> Since things can depend on the version, I can provide a general answer while mentioning that specifics may vary. I should definitely look up AOSP official sources for accuracy and include citations if I do that.
> 
> **Exploring Android language settings**
> 
> I’m looking into language settings for pre-Android devices and how locales are stored in Settings.System.SYSTEM_LOCALES. This setting might be user-specific, and I’m curious about how it interacts with the app's locale picker and underlying framework.
> 
> I need to check out the interaction between different tables and how current user settings affect locale storage. There seems to be a lot to uncover, like how ActivityManager handles these configurations. I should search through AOSP for more precise information on LocaleManagerService and how everything connects.
> 
> **Gathering specifics on settings**
> 
> I need to collect more official information regarding specifics, particularly about the SettingsProvider and how it relates to user storage. I'll search for authoritative sources to clarify these details better. This feels important to ensure I provide accurate and helpful responses. Let’s dig into it! Getting the right information is key here, and I'm curious to see what I can find about the settings and storage options available.
> 
> **Investigating tool issues**
> 
> I'm looking into issues with a large Settings.java file. I think I can use search results to help, and it's fine to cite those. I may need just enough from the search results, while still ensuring I get proper citations. It seems like there's useful information about how `getConfigurationForUser` interacts with `SYSTEM_LOCALES` and the user handle. I'll also check the current path for switching users in Android. Time to search!
> 
> **Investigating locale changes**
> 
> I need to figure out how the current system locale affects the flow. I'm thinking the Settings UI controllers call LocalePicker.updateLocales, and it might be helpful to look at the Settings app class. I’ll go ahead and do a search to gain a clearer understanding of how everything connects. It will help ensure any changes I make align properly with the expected behavior! Let’s explore this!
> 
> **Considering language configuration**
> 
> I need to think about the property persist.sys.locale as a global setting. The user wants to decouple account login changes from the system language. It’s important to remember that Android's system language applies globally to the device, not per process. For triggering account changes, we would need a custom observer or manager. If we don’t want to store per user records anymore, one option could be to keep AOSP user storage unchanged while introducing an account-language repository instead.
> 
> **Evaluating account language settings**
> 
> I’m realizing that the account store is essential, while SettingsProvider acts as a cache. When users select a language, I should write to the account store first and then apply the configuration. There’s an option to update Settings.System to maintain compatibility with AOSP. If a user switches accounts, I need to decide whether to apply the logged-in account’s language for that same context, while considering the potential need for deeper framework changes to accommodate account-specific settings.
> 
> **Mapping account services**
> 
> I think I need to provide a mapping for several components here. First, I could develop a custom AccountManagerService or Auth component that includes broadcast hooks for account switches. Next, should I create a new AccountLocaleManagerService or extend the existing LocaleManagerService? The current LocaleManagerService handles app-specific locales, but I might need to store account locales separately. I’ll have to consider account privacy and the storage method too, especially regarding encrypted data. It sounds like modifying `Settings.java` to use accountId rather than userId might be necessary, although it presents challenges with communicating between components.
> 
> **Modifying locale handling**
> 
> I think it’s best not to modify the public API of Settings.java but to adjust the call sites to route locales properly. At startup, the `Settings.System.getConfiguration()` is called from AMS, which reads the current user’s settings. I might need the AccountLocaleManager to apply the account settings during boot. I could also consider updating the persistent configuration to use the account store when the locale changes, while keeping per-user settings for things like font scale. It sounds like implementing a custom method to handle account-specific configurations could be a good solution.
> 
> **Integrating locale adjustments**
> 
> I need to remember that the system UI and backup expect certain settings. The `LocalePicker` and related components like `LocaleDragAndDropAdapter` may need adjustments during setup. I’m considering whether to introduce a new table in `SettingsProvider` for account-scoped data rather than modifying existing structures. It could make sense to create an `AccountSettingsProvider` instead. Regarding user configuration, I might need to ensure that switching users doesn't switch locales by default if accounts are decoupled. For backups and restoration, adapting the process to prevent overwriting account settings is also crucial.
> 
> **Choosing default language settings**
> 
> I need to decide on a temporary default language for the device until the user logs into their account. If it’s their first-time login and no account locale is set, I’ll use the current setup language as the initial locale. For surfaces like the lock screen and launcher, I should display either the system default or the last account used, with careful consideration to avoid showing previous users’ languages for privacy. I also need to adapt input methods based on account languages and explore regional preferences for text-to-speech and formatting settings in Android 14+.
> 
> **Exploring regional preferences**
> 
> I’m thinking about how Android settings include elements like Terms of Address and RegionAndNumberingSystem. I need to look into whether Android 14's "Regional Preferences" are stored and if I should include any classes related to this, such as `RegionalPreferences`. It seems like I've repeated myself here, but the focus is clear: understanding how these settings integrate into the system is essential. I'll need to search to see if there are any relevant classes or methods that can help me clarify this.
> 
> **Analyzing configuration changes**
> 
> I'm thinking about how `broadcastGlobalConfigurationChanged` sends `ACTION_CONFIGURATION_CHANGED`. Maybe Android sends `ACTION_LOCALE_CHANGED`? I could check ActivityManagerInternal.broadcastGlobalConfigurationChanged, but perhaps it's not necessary since a config update will restart the activity anyway.
> 
> I should mention that the framework broadcasts configuration or locale changes. 
> 
> On account logout, I have to choose between keeping the last locale or reverting to the default. When switching users, I might need to apply the current account language without restoring system locales unnecessarily.
> 
> **Planning migration strategy**
> 
> For the migration, I need to ensure that for existing devices, each account initializes its language from the previous Android `Settings.System.SYSTEM_LOCALES` during the first login, and then stop using the user record as the source.
> 
> I should handle backup and restore functionality too. 
> 
> In the code, I might want to update several classes, like adding account-aware methods in LocalePicker and possibly intercepting calls to the repository in the Settings app. Additionally, I need to make changes in ActivityManagerService and ActivityTaskManagerService to ensure the correct account configurations are updated and persisted.
> 
> **Refining the implementation**
> 
> I think it's better to use our own provider for the account locale management. I want to set up new services like CustomAccountManagerService and AccountLocaleManagerService, plus related interfaces and stores.
> 
> It seems that if global configurations are effective, the SystemUI, Keyguard, and Launcher might not require code changes—but I need to test that.
> 
> When it comes to the SetupWizard or OOBE, I should set the language before account provisioning. Plus, I’ll need to address the adaptation list, focusing on how application runtime config changes impact processes and considering persistent processes that must handle resources accordingly.
> 
> **Assessing dependencies and workload**
> 
> I need to consider dependencies like device policy and user restrictions, specifically `DISALLOW_CONFIG_LOCALE`. There are also permissions that system apps must have, like `CHANGE_CONFIGURATION` or `WRITE_SETTINGS`. 
> 
> I'll plan for backup/restore needs, keeping in mind race conditions during account switches.
> 
> For estimating the workload, a minimal solution could take around 2-4 person-days, possibly 1.5 to 2.5 weeks for development and testing. For a more complex implementation, I'll need around 3-5 weeks, with detailed planning for account persistence and features like setup wizards and backups.
> 
> **Considering citation strategy**
> 
> I don’t need to cite every statement, but it’s important to ensure that all internet-supported statements have corresponding citations. I'll focus on including citations for the main AOSP classes, as they're key. The rest can be more about design inference.
> 
> I’ll write citations paragraph by paragraph, sourcing where needed without raw URLs, just using citation markers. It’s also essential to ensure the citations are in Chinese but not overdo it.
> 
> As for the Android source flow, LocalePicker updates locales before calling other methods that set and persist configurations for users. I'll note that `updatePersistentConfigurationWithAttribution` uses the calling user ID as a nuance.
> 
> **Reviewing vendor account process**
> 
> I'm considering how the vendor account process is handled with the system user. If it calls incorrectly, it could persist data to user 0. To prevent this, I should use `Context#createContextAsUser(UserHandle.of(currentAndroidUser))` or ensure the service calls from the current user.
> 
> In Android 14/15, the signature for `updatePersistentConfiguration` doesn't include a user parameter; instead, `updatePersistentConfigurationWithAttribution` derives it from the calling UID. If the custom account daemon operates as the system user, it may write to USER_SYSTEM, so I'll need to manage that correctly. 
> 
> Creating a system API like `applyAccountLocales(String accountId, LocaleList locales)` could help avoid ambiguity in binder user IDs and maintain clarity around user space translations. The key idea is to switch the global configuration to the current account's language during login, as the account storage will serve as the source of truth.
> 
> **Considering data migration strategy**
> 
> For "数据迁移," I need to establish a process for the first account login when the account locale is empty. I should use the current `Configuration.getLocales()` or `Settings.System.SYSTEM_LOCALES` as a seed and save `accountId -> languageTags`.
> 
> When updating the language setting for the current account, I’ll save it first and then apply the updated configuration. For logging in another account, I should apply its stored tags, seeding from the system default if it's empty but avoiding seeding from the previous account, as that would cause data inheritance.
> 
> A business decision here is critical: the first account should seed from the current user locale, while new accounts should use the server profile or, if unavailable, device defaults, to prevent cross-account issues. If there's a custom account store that's cloud-backed, the account language can sync; otherwise, it will be local. I also need to track the source to avoid overwriting saved settings during the apply process.
> 
> **Thinking through configuration application**
> 
> When applying configuration, I need to ensure that the persistence callback is triggered for the account without duplicating saves. For instance, my pseudo-code for switching accounts will involve getting the target locales and applying them accordingly. I'll use `new Configuration()` instead of `getConfiguration()` to avoid persisting other fields, which the LocalePicker master already does.
> 
> I should also consider avoiding manual calls to `LocaleList.setDefault` unless necessary for UI responsiveness. 
> 
> Now, answering the question about what business logic needs to change involves identifying classes that need modification and estimating the adaptation workload. Key areas to consider include data storage (from SettingsProvider to the account store), triggers for account login and logout, system config application, settings UI, boot/init processes, multi-user fallbacks, and tests. I might want to differentiate between "minimum modifications" and "full decoupling," since users may expect specific classes to change in Android.
> 
> **Developing the recommended plan**
> 
> I should consider not modifying the SettingsProvider to include an account ID since all Settings.System APIs are user-keyed. Changing it to account-keyed could introduce significant risks regarding content resolver user IDs, permissions, and backup/restore functionalities. 
> 
> Instead, adding an account locale service seems more prudent. I also need to clarify that if acceptance criteria require avoiding user ID-based language storage in the database, I suggest skipping the persistent saving of SYSTEM_LOCALES initially. Many areas in AOSP still depend on SYSTEM_LOCALES as a configuration cache or backup trigger.
> 
> Noting a high-risk point, the global property `persist.sys.locale` means rebooting before account login will use the last account's locale. Strict decoupling requires setting a neutral locale upon logout or at the login screen. Otherwise, this could lead to bugs. 
> 
> It's crucial to remember that configuration is global rather than per Android user, but we can create a per-user persistent store. Switching accounts under the same Android user would mean applying configuration triggers a full system config change and app relaunch. We can't have two accounts showing different languages simultaneously unless using separate user profiles or per-app contexts.
> 
> **Ensuring device policy compliance**
> 
> I need to ensure that the DevicePolicyManager restriction DISALLOW_CONFIG_LOCALE is respected. The Settings app's LocaleListEditor extends RestrictedSettingsFragment, which incorporates this restriction. If an account switch is automatic, perhaps it should bypass this restriction, but we should honor it if the change is manual. 
> 
> I also have to consider font scaling; it shouldn’t change—just locale should be account-scoped. I need to be cautious with `putConfigurationForUser` since it writes fontScale as well. If I use `putLocaleForAccount`, I should avoid changing the fontScale.
> 
> Additionally, the system locale should consist of a LocaleList to support a list of language priorities rather than just one language. Also, class names might have changed across Android versions—like `ActivityManagerService.updateUserConfigurationLocked` in older versions versus the later `ActivityTaskManagerService` and `UserController`.
> 
> **Planning citation strategy**
> 
> I need to confirm that AOSP sources verify `Settings.System` maintains per-user settings, stored in separate XML files based on type. I'll be citing snippets from `SettingsProvider` to support this.
> 
> For my citation plan, I’ll break it down into several sections:
> 
> 1. In the "AOSP flow currently" paragraph, I’ll cite LocalePicker's updateLocales, ATM persist, and per-user Settings System and SettingsProvider.
> 2. For "app-specific locales are separate," I’ll reference LocaleManagerService.
> 3. The "Settings app call" will include citations from LocaleDragAndDropAdapter and the older LocalePicker.
> 4. I'll mention user switch propagation with a citation for the commit.
> 5. Permissions will be cited from the ActivityManagerService search.
> 
> To avoid citation overload in a table, I’ll include citations in the table's introduction and ensure no HTML in the final output.
> 
> In this final outlining step, I’ll make sure to emphasize that rather than switching Android users, we should create an "account language service" to ensure account language serves as the source of truth and actively update the global Configuration upon each account login or switch.
> 
> I’ll retain `Settings.System.SYSTEM_LOCALES` as the current Android user cache while using the account database for the actual data, with a strict decouple for framework persistence changes. The existing flow from the Settings UI to LocalePicker and through to the ActivityManager will need clear citations after each section.

## 结论

建议把**账号语言**做成新的 source of truth：`accountId -> LocaleList`。  
Android 当前的 `Settings.System.SYSTEM_LOCALES` 可以第一期保留为“当前 Android user 的运行时镜像/缓存”，但**不能再作为业务真实语言配置**。账号登录/切换时，由你们自己的账号系统触发一次系统 `Configuration` 更新，从而让**用户空间不变、账号切换时系统语言跟着变**。

AOSP 现状大致是：Settings 语言界面最终调用 `LocalePicker.updateLocales()`；该方法构造 `Configuration`、设置 `userSetLocale = true`，再调用 ActivityManager 的持久化配置更新；ActivityTaskManager 更新全局配置时会设置 `persist.sys.locale`、`LocaleList.setDefault()`，并把配置写回 `Settings.System.putConfigurationForUser(..., userId)`；而 `Settings.System` 读写 `SYSTEM_LOCALES` 时带 `userHandle`，`SettingsProvider` 的 system/secure settings 也是按 user 加载和持久化的。所以默认实现天然是“随 Android user/user space 记录”。([android.googlesource.com](https://android.googlesource.com/platform/packages/apps/Settings/%2B/903d2610dd6479445633db86336bde3208e5b4da/src/com/android/settings/localepicker/LocaleDragAndDropAdapter.java?utm_source=openai))

---

## 1. 需要适配的核心链路

### 当前链路

```text
用户在 Settings 选择语言
  -> packages/apps/Settings localepicker
  -> com.android.internal.app.LocalePicker.updateLocales()
  -> IActivityManager.updatePersistentConfigurationWithAttribution()
  -> ActivityManagerService / ActivityTaskManagerService
  -> update global Configuration
  -> persist.sys.locale
  -> Settings.System.SYSTEM_LOCALES for current userId
  -> 广播/配置变化，应用重建或 onConfigurationChanged()
```

用户切换时，AOSP 也会把“下一个 Android user 的配置”读出来覆盖当前配置；Android N 以后 system locale 存在 `Settings.System`，用户切换时会通过 `adjustConfigurationForUser()` 读取目标 user 的 `SYSTEM_LOCALES`。这正是你们要解耦的点。([android.googlesource.com](https://android.googlesource.com/platform/frameworks/base/%2B/ea906b3%5E%21/?utm_source=openai))

---

## 2. 推荐架构

新增一个账号语言服务，不建议直接把 `SettingsProvider` 改成 account 维度。

```text
自研账号系统
  -> onAccountLogin / onAccountSwitch / onLogout
  -> AccountLocaleManagerService
      - 读取 accountId 对应 LocaleList
      - 若没有记录，按策略初始化
      - 调用系统 Configuration 更新
      - 写入/同步账号语言配置
  -> Android 全局 Configuration 变化
  -> 全系统 UI 语言变化
```

### 推荐数据模型

```text
AccountLocaleRecord {
    accountId: String
    localeTags: String      // 例如 "zh-Hans-CN,en-US"
    source: enum { USER_SET, SERVER_SYNC, MIGRATED, DEFAULT }
    updatedAt: long
}
```

注意：Android 系统语言是 `LocaleList`，不是单个 `Locale`，要支持语言优先级列表。

---

## 3. 业务逻辑需要怎么改

| 场景 | 原逻辑 | 改造后逻辑 |
|---|---|---|
| 用户手动修改系统语言 | 写入当前 Android user 的 `Settings.System.SYSTEM_LOCALES` | 写入当前登录账号的 `AccountLocaleStore`，然后 apply 到系统 |
| 账号 A 登录 | 不触发系统语言变化 | 读取账号 A 的 locale，更新全局 `Configuration` |
| A 切到 B | Android user 不变，系统语言不会自动变 | 账号切换回调中 apply 账号 B 的 locale |
| B 首次登录 | 可能继承当前 user/上个账号语言 | 按策略初始化：服务端配置、设备默认语言、SetupWizard 语言；避免无意继承上一个账号 |
| 退出账号 | 无对应逻辑 | 需要定义策略：保持最后语言、恢复设备默认、或切到登录页默认语言 |
| Android user 切换 | 默认读取目标 user 的 `SYSTEM_LOCALES` | 如果该 user 内有当前账号，则以账号 locale 为准；无账号时才 fallback 到 user locale |
| 备份/恢复 | SettingsProvider 备份 user 级设置 | 账号语言走你们账号系统/自定义备份，避免被 user 级 restore 覆盖 |

---

## 4. 需要新增/修改的主要类

### A. 新增，推荐必须做

| 模块 | 类/文件 | 作用 |
|---|---|---|
| SystemServer | `AccountLocaleManagerService` | 账号语言的系统服务，负责存取和 apply |
| Binder API | `IAccountLocaleManager.aidl` | 给 Settings、账号系统、系统组件调用 |
| 存储层 | `AccountLocaleStore` | `accountId -> localeTags` 持久化 |
| 账号系统 | `AccountSwitchObserver` / 你们已有账号回调 | 监听登录、切换、退出 |
| 权限 | `android.permission.MANAGE_ACCOUNT_LOCALE` 或 signature 权限 | 限制只有系统组件能改账号语言 |

### B. Framework 需要关注/可能修改

| 类 | 修改建议 |
|---|---|
| `frameworks/base/core/java/com/android/internal/app/LocalePicker.java` | 可以保留原逻辑，但 Settings 调用前后要接入账号存储；或者新增 account-aware 方法 |
| `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` | 账号切换 apply locale 时不要依赖调用方 userId；最好由 system_server 内部用当前 foreground userId apply |
| `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` | 如果要严格禁止 user 维度语言持久化，需要改 `putConfigurationForUser` 路径；否则第一期可继续把 `Settings.System` 当镜像 |
| `frameworks/base/core/java/android/provider/Settings.java` | 严格解耦时才改 `SYSTEM_LOCALES` 读写；推荐第一期不大改，避免影响其他配置 |
| `frameworks/base/packages/SettingsProvider/.../SettingsProvider.java` | 不建议直接改成 account 维度；除非验收要求 settings 数据库中也不能保存 user 级语言 |
| `frameworks/base/services/core/java/com/android/server/locales/LocaleManagerService.java` | 这是 Android 13+ 的“应用级语言”服务，不是系统语言主链路；除非你们也要让每个账号有不同 app-specific locale，否则不要把系统语言逻辑塞进去。AOSP 注释也说明它主要存储 app-specific UI locales 和 app 的 override `LocaleConfig`。([android.googlesource.com](https://android.googlesource.com/platform/frameworks/base/%2B/master/services/core/java/com/android/server/locales/LocaleManagerService.java?utm_source=openai)) |

### C. Settings App 需要改

按你们分支实际类名为准，常见包括：

| 类 | 修改点 |
|---|---|
| `LocaleDragAndDropAdapter.java` | 当前拖拽/删除/新增语言后会调用 `LocalePicker.updateLocales()`；要先保存到当前账号，再 apply |
| `LocaleListEditor.java` | 语言列表展示、删除确认、限制逻辑要改成账号语义 |
| `SystemLocalePickerFragment.java` | 选择系统语言后写账号语言 |
| `LocalePickerWithRegionActivity.java` | 地区选择结果写账号语言 |
| `SystemLocaleAllListPreferenceController.java` | 展示当前账号语言 |
| `SystemLocaleSuggestedListPreferenceController.java` | 建议语言列表可结合账号/服务端策略 |
| `LocaleHelperPreferenceController.java` | summary/标题要从账号语言源获取 |
| 老版本 `com.android.settings.LocalePicker` | 如果分支较老，老入口直接调用 `LocalePicker.updateLocale()`，也要改 |

AOSP Settings 里语言列表拖拽适配器已有直接调用 `LocalePicker.updateLocales(mLocalesToSetNext)` 的路径，这是 Settings 侧最关键的改点之一。([android.googlesource.com](https://android.googlesource.com/platform/packages/apps/Settings/%2B/903d2610dd6479445633db86336bde3208e5b4da/src/com/android/settings/localepicker/LocaleDragAndDropAdapter.java?utm_source=openai))

---

## 5. 关键实现建议

### 5.1 账号切换时 apply 系统语言

伪代码：

```java
public final class AccountLocaleManagerService extends SystemService {
    private final AccountLocaleStore mStore;
    private final ActivityTaskManagerInternal mAtmInternal;
    private final ActivityManagerInternal mAmInternal;

    public void onAccountSwitched(@Nullable String accountId) {
        LocaleList target = resolveLocaleForAccount(accountId);

        if (target == null || target.isEmpty()) {
            target = getDefaultLoginLocale();
        }

        applySystemLocales(target, "account_switch");
    }

    public void onUserChangedSystemLocales(String accountId, LocaleList locales) {
        mStore.putLocales(accountId, locales.toLanguageTags(), Source.USER_SET);
        applySystemLocales(locales, "settings_user_change");
    }

    private void applySystemLocales(LocaleList locales, String reason) {
        Configuration config = new Configuration();
        config.setLocales(locales);
        config.userSetLocale = true;

        int currentUserId = mAmInternal.getCurrentUserId();

        // 推荐走 system_server 内部路径，显式传 currentUserId，
        // 不要让调用方 Binder userId 决定写哪个 Android user。
        mAtmInternal.updatePersistentConfiguration(config, currentUserId);
    }
}
```

注意：实际 `ActivityTaskManagerInternal` 是否已有可直接调用的方法，取决于你们 Android 版本；没有就封一层 system_server 内部接口。

### 5.2 处理 Binder 调用方 userId 问题

`updatePersistentConfigurationWithAttribution()` 会做权限检查，并基于调用方 userId 走持久化路径；系统源码里还会检查 `CHANGE_CONFIGURATION` 和 `WRITE_SETTINGS`。如果你们的账号进程是 system user 或常驻进程，直接从外部进程调可能写到错误 user。建议账号语言 apply 放在 system_server 内部完成，显式使用当前 foreground Android userId。([android.googlesource.com](https://android.googlesource.com/platform/frameworks/base/%2B/refs/heads/android12-release/services/core/java/com/android/server/am/ActivityManagerService.java?utm_source=openai))

### 5.3 `persist.sys.locale` 只能是全局的

系统语言 apply 后会写 `persist.sys.locale`，这是设备级属性，不可能天然变成多账号多值。账号切换能做到的是：**登录哪个账号，就把当前全局语言切到哪个账号的语言**。如果设备重启后还没登录账号，系统会使用上一次持久化的 locale；如果你们有隐私或体验要求，需要在 logout/boot/login page 阶段定义“未登录默认语言”。AOSP 在全局配置更新时会设置 `persist.sys.locale`。([android.googlesource.com](https://android.googlesource.com/platform/frameworks/base/%2B/master/services/core/java/com/android/server/wm/ActivityTaskManagerService.java))

### 5.4 是否还写 `Settings.System.SYSTEM_LOCALES`

推荐分两阶段：

#### 第一阶段，低风险

- 账号语言存在你们自己的 `AccountLocaleStore`。
- 每次账号登录/切换都从账号库 apply。
- 允许系统继续把当前 locale 镜像写到 `Settings.System.SYSTEM_LOCALES`。
- 不再把 `Settings.System.SYSTEM_LOCALES` 当业务真实值。

优点：改动小，兼容 SettingsProvider、BackupManager、现有系统组件。  
缺点：`adb shell settings get system system_locales` 看到的是“当前镜像”，不是账号源数据。

#### 第二阶段，严格解耦

- 修改 `ActivityTaskManagerService` 或 `Settings.System.putConfigurationForUser()` 路径。
- locale 不再按 userId 持久化，或者只写 account-scoped provider。
- `Settings.System.SYSTEM_LOCALES` 只保留兼容读，或者改成返回当前账号语言。

优点：数据层完全符合“随账号记录”。  
缺点：风险大，容易影响用户切换、备份恢复、系统初始化、CTS/兼容性。

---

## 6. 还要适配的边界场景

1. **SetupWizard / 首次开机语言**  
   首次开机还没有账号，必须有临时语言。账号首次登录时，决定是继承 SetupWizard 语言，还是使用账号服务端语言。

2. **锁屏 / 登录页语言**  
   退出账号后是保持最后账号语言，还是切到设备默认语言，要明确产品策略。

3. **多 Android user 仍然存在时**  
   虽然需求说用户空间不变，但系统可能仍支持多 user。建议策略是：同一个 Android user 内按账号切语言；Android user 切换后，如果该 user 有活跃账号，仍以账号语言为准。

4. **应用重启和配置变化**  
   系统语言变化会触发 configuration change。系统 app、Launcher、SystemUI、Settings、输入法等要确认是否正确刷新。

5. **输入法、拼写检查、TTS、键盘布局**  
   如果业务口径是“语言体验随账号”，这些也可能需要 account-scoped；如果只要求系统显示语言，则可以暂不做。

6. **Android 13+ 应用级语言**  
   App-specific locale 和 system locale 是两套机制。账号切系统语言时，不一定要改 app-specific locale；但如果某账号给某些 app 设置了单独语言，需要额外适配 `LocaleManagerService` 相关数据。

7. **备份恢复 / 云同步**  
   账号语言最好跟随账号系统同步。避免系统 Settings restore 后覆盖账号语言。

8. **权限与安全**  
   修改系统语言需要 signature/system 权限。账号语言服务的写接口必须限制调用方，避免普通 app 伪造账号切换改系统语言。

9. **快速切换账号的竞态**  
   账号 A -> B -> C 快速切换时，apply 操作要串行化，只保留最后一次目标 locale。

---

## 7. 测试清单

| 测试项 | 预期 |
|---|---|
| 同一 Android user，账号 A 设置中文，账号 B 设置英文 | A/B 切换时系统语言跟随切换 |
| 切换账号后打开 Settings 语言页 | 显示当前账号语言 |
| 修改语言后重启 | 登录同一账号恢复该账号语言 |
| 退出账号后重启 | 按未登录语言策略显示 |
| 新账号首次登录 | 不错误继承上一个账号语言，除非产品明确要求 |
| 连续快速切账号 | 最终语言等于最后登录账号 |
| SystemUI、Launcher、Settings、输入法 | UI 文案刷新正常 |
| 后台 app / 前台 app | 正确收到配置变化或重建 |
| Android user 切换 | 不再错误以 user locale 覆盖账号 locale |
| 备份恢复 | 账号语言不被 user 级 settings 覆盖 |
| 权限测试 | 非系统 app 不能改账号语言 |

---

## 8. 工作量评估

按已有自研账号系统、Android 12+ Framework 分支估算：

| 方案 | 范围 | 开发工作量 | 测试工作量 | 风险 |
|---|---|---:|---:|---|
| 最小方案 | 账号切换时直接调用现有 `LocalePicker.updateLocales()` 或 AM 接口；Settings UI 少量适配 | 5～8 人日 | 3～5 人日 | 中 |
| 推荐方案 | 新增 `AccountLocaleManagerService`，账号库作为 source of truth，Settings 语言页改为账号维度，`Settings.System` 作为镜像 | 10～18 人日 | 5～10 人日 | 中 |
| 严格解耦方案 | 改 Framework 持久化路径，不再按 userId 保存 `SYSTEM_LOCALES`，适配 boot/user switch/backup | 20～35 人日 | 10～20 人日 | 中高 |
| 完整产品化 | 再加 SetupWizard、未登录态、云同步、app-specific locale、输入法/TTS/区域偏好 | 30～50+ 人日 | 20～30 人日 | 高 |

我的建议是：**先做推荐方案**。也就是“账号库为准，Settings.System 只做当前系统运行镜像”。这样能满足用户空间不变、账号切换语言变化的核心诉求，同时尽量少破坏 AOSP 原有配置更新链路。

---
Learn more:
1. [src/com/android/settings/localepicker/LocaleDragAndDropAdapter.java - platform/packages/apps/Settings - Git at Google](https://android.googlesource.com/platform/packages/apps/Settings/%2B/903d2610dd6479445633db86336bde3208e5b4da/src/com/android/settings/localepicker/LocaleDragAndDropAdapter.java?utm_source=openai)
2. [Diff - ea906b3^! - platform/frameworks/base - Git at Google](https://android.googlesource.com/platform/frameworks/base/%2B/ea906b3%5E%21/?utm_source=openai)
3. [services/core/java/com/android/server/locales/LocaleManagerService.java - platform/frameworks/base - Git at Google](https://android.googlesource.com/platform/frameworks/base/%2B/master/services/core/java/com/android/server/locales/LocaleManagerService.java?utm_source=openai)
4. [services/core/java/com/android/server/am/ActivityManagerService.java - platform/frameworks/base - Git at Google](https://android.googlesource.com/platform/frameworks/base/%2B/refs/heads/android12-release/services/core/java/com/android/server/am/ActivityManagerService.java?utm_source=openai)
5. [services/core/java/com/android/server/wm/ActivityTaskManagerService.java - platform/frameworks/base - Git at Google](https://android.googlesource.com/platform/frameworks/base/%2B/master/services/core/java/com/android/server/wm/ActivityTaskManagerService.java)