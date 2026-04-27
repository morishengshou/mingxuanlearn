# Android 系统语言与用户空间解耦改造方案

## 一、需求理解与核心问题分析

### 原有机制
Android 原生的语言设置是**与 UserId（用户空间）强绑定**的：
- 配置存储在 `Settings.System` / `LocalePicker` 触发的 `IActivityManager.updateConfiguration()` 中
- 最终落到 `system/users/<userId>/settings_system.xml` 或 framework 内的 `mUserConfiguration`
- 切换 user 时，`ActivityManagerService.switchUser()` 会重新加载该 user 的 Configuration

### 新需求
**用户空间不变（同一个 userId），账户切换时语言跟随账户改变。**

这意味着语言不再是 user 级别的属性，而是 **account 级别**的属性，需要把 Configuration 的存取主键从 userId 改为 accountId（或建立 account → locale 的映射层）。

---

## 二、需要适配的核心模块

### 1. Framework 层 —— ActivityManagerService / ActivityTaskManagerService

这是最核心的改造点。原本的 Locale 切换流程：

```
LocalePicker.updateLocale() 
  → ActivityManager.getService().updateConfiguration(config)
  → ATMS.updateConfigurationLocked()
  → 写入 mTempConfig / mUserConfiguration
  → 通知所有进程 onConfigurationChanged
```

**需要修改的类：**
- `ActivityTaskManagerService.java`：`updateGlobalConfigurationLocked()`、`updateUserConfigurationLocked()` —— 增加 account 维度参数
- `UserController.java`：`switchUser()` 流程中，原来会加载 user 的 locale，需要改为加载"当前 user 当前 account"的 locale
- 新增类 `AccountConfigurationController.java`：负责 account → Configuration（locale）的映射管理

### 2. Settings Provider 改造

原存储位置：`/data/system/users/<userId>/settings_system.xml` 中的 `system_locales` 字段。

**改造方案（推荐方案 B）：**

| 方案 | 说明 | 优劣 |
|-----|------|-----|
| A | 在 user 目录下增加 account 子目录 | 改动小，但 SettingsProvider 模型需扩展 |
| B | 新建独立 `AccountSettingsProvider` 或扩展表 `account_settings` | 解耦清晰，推荐 |
| C | 用 SharedPreferences 自建账户配置存储 | 仅业务侧用，但 framework 拿不到 |

**需要修改的类：**
- `SettingsProvider.java`：增加 account 维度的 Key 解析
- `SettingsState.java` / `SettingsRegistry`：新增 `SETTINGS_TYPE_ACCOUNT`
- `Settings.java`（android.provider）：暴露 `Settings.Account.getString/putString` 接口

### 3. 系统设置 UI（Settings App）

`packages/apps/Settings` 下：
- `LocalePickerWithRegion` / `LanguageAndInputSettings`：保存语言时调用新接口（按账户写入）
- `LocaleListEditor.doTheUpdate()`：把 `LocalePicker.updateLocales()` 改为按账户路径写入
- 增加权限校验：未登录账户时不允许修改语言，或写入"游客默认 locale"

### 4. 账户系统对接（你自研的账户体系）

需要提供以下能力：
- `AccountManagerService`（自研）：暴露 `getCurrentAccountId(userId)` 给 framework
- 账户登录/登出广播：`ACTION_ACCOUNT_LOGIN` / `ACTION_ACCOUNT_LOGOUT`
- 账户切换时驱动 Configuration 重建

### 5. 启动流程与监听

**关键时机：**
1. 开机启动后，user unlock 完成 → 查询当前账户 → 应用账户语言
2. 账户登录成功 → 触发 locale 切换
3. 账户登出 → 回退到默认 locale 或保留最后状态
4. 账户切换（A→B）→ 切换 locale

**需要新增/修改：**
- `SystemServer.java`：在 `AccountManagerService` 启动后注册回调
- `AccountSwitchObserver`（新增）：监听账户事件，调用 `ATMS.updateConfigurationForAccount()`
- `LockSettingsService` 或自研账户服务：在解锁/登录完成时回调

---

## 三、业务逻辑变更清单

### 3.1 数据模型变更

```
原：UserConfiguration { userId, locales, ... }
新：AccountConfiguration { userId, accountId, locales, ... }
    + 默认 fallback：UserConfiguration（无账户登录时使用）
```

### 3.2 关键流程变更

**写入流程：**
```
LocalePicker → 检查当前是否有登录账户
  ├─ 有：写入 account_settings 表（key: accountId+locale）
  └─ 无：写入原有 user_settings（保持兼容/默认值）
→ 触发 Configuration 更新
```

**读取流程（开机/账户切换）：**
```
boot complete → user unlocked → query current account
  → load account locale → apply Configuration
  → 若无账户：使用 system default locale
```

**账户切换流程（新增）：**
```
AccountService.onAccountSwitched(oldAcc, newAcc)
  → AccountConfigurationController.loadLocaleForAccount(newAcc)
  → ATMS.updateConfigurationLocked(newConfig)
  → 系统广播 ACTION_LOCALE_CHANGED
  → 所有 Activity 重建（同原 locale 切换流程）
```

### 3.3 边界场景处理

需要明确产品策略，列出关键问题：

1. **未登录态**：使用上一次账户的语言，还是系统默认？（建议系统默认）
2. **首次登录账户**：账户无语言记录时，从哪里 inherit？（建议继承当前 user 默认）
3. **多账户并发**：是否允许？（Android 单 user 同一时间通常单账户）
4. **OTA 升级**：旧的 user 级 locale 数据需要做迁移策略
5. **应用进程**：Configuration 切换会导致 Activity 重建，需评估业务影响（同原生 locale 切换一致）

---

## 四、需要修改/新增的类清单

### Framework 层（frameworks/base）

| 类 | 类型 | 说明 |
|---|------|------|
| `ActivityTaskManagerService` | 修改 | 增加 account 维度的 Configuration 更新方法 |
| `UserController` | 修改 | switchUser 时考虑 account 维度 |
| `Configuration` | 可能修改 | 如需携带 accountId 信息 |
| `AccountConfigurationController` | **新增** | account ↔ locale 映射管理 |
| `LocaleManagerService` (Android 13+) | 修改 | 应用级 locale 同样按账户隔离 |
| `Settings.java` (provider) | 修改 | 新增 Account 命名空间 |
| `SettingsProvider` | 修改 | 支持 account 类型 |
| `SettingsState` | 修改 | 新增存储类型 |
| `LocalePicker` | 修改 | 写入接口切换 |

### 账户系统（自研）

| 类 | 类型 | 说明 |
|---|------|------|
| `AccountManagerService`（自研） | 修改 | 暴露当前账户、注册切换监听 |
| `AccountSwitchObserver` | **新增** | 桥接账户事件与 Configuration 更新 |
| `AccountLocaleStore` | **新增** | 账户语言持久化（DB 或 XML） |

### 应用层

| 类 | 类型 | 说明 |
|---|------|------|
| `LocaleListEditor` (Settings) | 修改 | 写入路径调整 |
| `LanguageAndInputSettings` | 修改 | 未登录态 UI 提示 |
| 各类 `LocaleHelper` | 修改 | 读取按账户读取 |

---

## 五、工作量评估

| 模块 | 工作量（人日） | 风险等级 |
|------|---------------|---------|
| Framework AMS/ATMS 改造 | 8 ~ 12 | 高（影响系统稳定性） |
| SettingsProvider 扩展 | 5 ~ 7 | 中 |
| 账户服务对接 + Observer | 4 ~ 6 | 中 |
| Settings App UI 适配 | 3 ~ 5 | 低 |
| LocaleManagerService（应用级 Locale） | 4 ~ 6 | 中 |
| OTA 数据迁移逻辑 | 2 ~ 3 | 中 |
| 边界场景处理 + 异常恢复 | 3 ~ 5 | 中 |
| 自测 + 联调 + Monkey | 8 ~ 10 | 高 |
| CTS / GTS 兼容性回归 | 5 ~ 7 | **高** |
| **合计** | **约 42 ~ 61 人日** | — |

按 1 名熟悉 framework 的中高级工程师独立推进估算，约 **2 ~ 3 个月**完成开发自测，再加 **2 ~ 4 周**稳定性回归。

### 主要风险点

1. **CTS 兼容性**：修改了 SettingsProvider 数据模型和 Configuration 流程，很可能挂 CTS，需要预留专门的 CTS 适配 patch
2. **Configuration 风暴**：账户频繁切换可能引起 Activity 频繁重建，需做防抖
3. **进程冷启动竞态**：账户尚未就绪时 launcher 已起来，会用错误 locale，需要 boot 流程同步
4. **WMS / IME / Resources**：Locale 链路涉及 WMS 重布局、IME 重切换、Resources 重加载，每条链路都要回归
5. **三方应用兼容**：部分 App 自己缓存 Locale，账户切换后未必跟随，可能需要补强广播

---

## 六、推荐的落地分期

**Phase 1（MVP，约 3 周）：**
单账户场景下的语言切换打通，登录/登出/切换三态正确，先不动 LocaleManagerService（应用级 locale 暂不隔离）。

**Phase 2（约 3 周）：**
应用级 locale 按账户隔离、OTA 迁移、异常恢复。

**Phase 3（约 2 周）：**
CTS 修复、性能优化（防抖、缓存）、文档与测试用例补全。

如果需要，我可以进一步给出 `AccountConfigurationController` 的详细类设计或具体某个文件的 patch 草稿。