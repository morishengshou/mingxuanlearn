# Android 12 SDK 编译 & 自定义接口开发新手教程

> 面向对象：Android 12（AOSP）开发新手，需要编译公司定制 SDK 并为其添加自定义接口。

---

## 一、先搞清楚几个概念（很重要）

新手最容易混淆的就是"SDK"到底指什么。在 AOSP（Android 开源项目）语境里：

| 名词 | 是什么 | 你关心的 |
|------|--------|----------|
| **AOSP 源码** | 整个安卓系统的源代码 | 编译 SDK 的前提 |
| **framework.jar** | 系统框架层，`android.*` 那些 API 的实现 | 你加接口就是改这里 |
| **android.jar (SDK)** | 给 App 开发者用的"接口壳子"，只有方法签名没实现，放在 Android Studio 里编译用 | 你最终要产出的东西 |
| **API 签名文件** | `current.txt` 等，记录所有公开 API 的清单 | 加接口必须同步更新它 |

**核心结论**：你公司定制 SDK，本质是：**在 AOSP 里改 framework → 编译出带你新接口的 `android.jar` → 交给 App 开发同事在 Android Studio 里用。**

---

## 二、准备编译环境

### 1. 操作系统
AOSP **必须在 Linux 上编译**（官方支持 Ubuntu）。Windows 编不了 AOSP。

如果你现在用的是 Windows，有三个选择：
- **推荐**：一台 Ubuntu 20.04 物理机 / 服务器（公司通常有编译服务器）
- WSL2（可以，但磁盘 IO 慢，大项目吃力）
- 虚拟机（不太推荐，慢）

### 2. 硬件门槛（别小看）
- 磁盘：**源码 + 编译产物 ≥ 400GB**，建议留 500GB 以上
- 内存：**16GB 起步，推荐 32GB+**
- CPU：核越多越好，全量编译几十分钟到几小时

### 3. 装依赖（Ubuntu）
```bash
sudo apt-get update
sudo apt-get install -y git-core gnupg flex bison build-essential zip curl \
  zlib1g-dev libc6-dev-i386 libncurses5 lib32ncurses5-dev x11proto-core-dev \
  libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils xsltproc unzip fontconfig \
  python3 openjdk-11-jdk
```
> Android 12 用 **JDK 11**（源码里自带 JDK，一般不用手动配，但装上不亏）。

---

## 三、下载 AOSP 源码

### 1. 配置 repo 工具
```bash
mkdir ~/bin
curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
chmod a+x ~/bin/repo
export PATH=~/bin:$PATH
```

### 2. 配 git 身份
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 3. 初始化并同步（选 Android 12 分支）
```bash
mkdir ~/aosp && cd ~/aosp

# android-12.0.0_r34 是一个 Android 12 的 release tag，可按需换
repo init -u https://android.googlesource.com/platform/manifest -b android-12.0.0_r34

# 开始下载，-c 只下当前分支，-j 是并发线程数
repo sync -c -j8
```

> ⚠️ **公司定制场景**：你们公司多半有**自己的 Git 服务器和 manifest**（在官方 AOSP 基础上打了定制补丁）。这时应该用公司给的地址：
> ```bash
> repo init -u <公司的manifest仓库地址> -b <公司分支>
> ```
> **一定要先问你的同事或组长要这个地址**，不要直接用官方的——否则你编出来的不是公司定制版。国内网络访问官方源很慢，公司内网源会快得多。

下载可能要几个小时（几十 GB），耐心等。

---

## 四、编译 SDK

### 1. 进入编译环境
每次开新终端都要先执行：
```bash
cd ~/aosp
source build/envsetup.sh
```
这一步会加载 `lunch`、`make`、`m` 等一堆编译命令。

### 2. 选择编译目标
```bash
lunch
```
会弹出一个菜单列表让你选（或直接 `lunch sdk-eng`）。

**编 SDK 用这个组合**：
```bash
lunch sdk-eng
```
- `sdk` = 目标产品是 SDK（不是某台真机）
- `eng` = 工程版（带调试、编译快）

> 如果你要编的是**整机系统镜像**（刷到设备上），那要选公司具体的产品名，比如 `lunch aosp_arm64-userdebug` 或公司自定义的 `lunch xxx_product-userdebug`。**编 SDK 和编整机是两回事，别搞混。**

### 3. 开始编译 SDK
```bash
make sdk -j8
```
- `-j8`：用 8 线程，改成你 CPU 核数（比如 `-j$(nproc)` 自动用满）
- 第一次全量编译很慢（可能几十分钟到 1 小时+）

### 4. 找编译产物
成功后，SDK 压缩包在：
```
out/host/linux-x86/sdk/sdk/android-sdk_eng.<用户名>_linux-x86.zip
```

而你最关心的 **`android.jar`** 在：
```
out/target/common/obj/PACKAGING/android_jar_intermediates/android.jar
```
这个 `android.jar` 就是给 App 开发者在 Android Studio 里替换使用的核心产物。

---

## 五、在 SDK 里添加自定义接口

这是核心需求。假设你要给系统加一个接口，让 App 能调用你公司的某个功能。这里给一个**最典型、最完整的例子：新增一个系统服务 + 对外接口**。

### 场景示例
我们要加一个 `CompanyManager`，提供一个方法 `getCompanyId()` 给 App 调用：
```java
CompanyManager mgr = (CompanyManager) getSystemService("company");
String id = mgr.getCompanyId();
```

### 方式对比：三种"加接口"的粒度

| 方式 | 难度 | 说明 |
|------|------|------|
| 只加公开 API 方法 | ⭐ | 在已有类里加 public 方法 |
| 加 SystemService + Manager | ⭐⭐⭐ | 完整的一套新功能（下面详讲）|
| 加 AIDL 跨进程接口 | ⭐⭐⭐⭐ | 涉及进程间通信 |

下面走**完整的 SystemService 流程**（最能说明问题）。

---

### 步骤 1：定义对外的 Manager 类

框架层代码在 `frameworks/base/core/java/android/` 下。新建：

`frameworks/base/core/java/android/app/CompanyManager.java`
```java
package android.app;

import android.content.Context;
import android.os.RemoteException;

/**
 * 公司定制服务的对外接口。App 通过 getSystemService 拿到它。
 */
public class CompanyManager {
    private final ICompanyService mService;

    /** @hide 内部构造，不对 App 暴露 */
    public CompanyManager(Context context, ICompanyService service) {
        mService = service;
    }

    /**
     * 获取公司 ID。
     */
    public String getCompanyId() {
        try {
            return mService.getCompanyId();
        } catch (RemoteException e) {
            throw e.rethrowFromSystemServer();
        }
    }
}
```

> 注意 Javadoc 里的 `@hide`：**带 `@hide` 的成员不会出现在给 App 的 SDK 里**（属于内部 API）。不带 `@hide` 的 public 方法才会进 SDK。

### 步骤 2：定义 AIDL 跨进程接口

系统服务运行在独立进程，App 通过 Binder 调用它，所以要用 AIDL 描述接口。

`frameworks/base/core/java/android/app/ICompanyService.aidl`
```java
package android.app;

/** @hide */
interface ICompanyService {
    String getCompanyId();
}
```

然后在 `frameworks/base/Android.bp` 里，把这个 `.aidl` 加到编译列表（找 `filegroup` 或 aidl 相关配置，把路径加进去）。新手可参考同目录已有 `.aidl` 是怎么被引用的，照葫芦画瓢。

### 步骤 3：实现系统服务

`frameworks/base/services/core/java/com/android/server/CompanyService.java`
```java
package com.android.server;

import android.app.ICompanyService;
import android.content.Context;

public class CompanyService extends ICompanyService.Stub {
    private final Context mContext;

    public CompanyService(Context context) {
        mContext = context;
    }

    @Override
    public String getCompanyId() {
        // 这里写你的真实实现
        return "COMPANY-12345";
    }
}
```

### 步骤 4：注册系统服务

在 `frameworks/base/services/java/com/android/server/SystemServer.java` 里，找到 `startOtherServices()` 方法，加上：
```java
// 注册公司定制服务
traceBeginAndSlog("StartCompanyService");
ServiceManager.addService("company",
        new CompanyService(context));
traceEnd();
```

### 步骤 5：让 getSystemService("company") 能拿到 Manager

在 `frameworks/base/core/java/android/app/SystemServiceRegistry.java` 里，找到那一堆 `registerService(...)` 的地方，加一段：
```java
registerService(Context.COMPANY_SERVICE, CompanyManager.class,
        new CachedServiceFetcher<CompanyManager>() {
    @Override
    public CompanyManager createService(ContextImpl ctx) {
        IBinder b = ServiceManager.getService(Context.COMPANY_SERVICE);
        ICompanyService service = ICompanyService.Stub.asInterface(b);
        return new CompanyManager(ctx.getOuterContext(), service);
    }
});
```

再在 `frameworks/base/core/java/android/content/Context.java` 里加常量：
```java
public static final String COMPANY_SERVICE = "company";
```

### 步骤 6：更新 API 签名文件（⭐关键，新手必踩的坑）

AOSP 有个机制：**所有对外公开的 API 都必须登记在案**，否则编译直接报错，防止有人偷偷改公开接口。

你新增了 `getCompanyId()` 和 `COMPANY_SERVICE` 这些 public API，就必须更新签名文件。**不用手写**，运行：
```bash
make update-api -j8
```
它会自动把你的新 API 写进 `frameworks/base/api/current.txt` 等文件。

> 如果不做这一步，编译会报类似 `api-stubs` 不一致的错误，很多新手卡在这里。

### 步骤 7：重新编译 SDK
```bash
make sdk -j8
# 或者只想快速验证框架：make framework -j8
```

编完后新的 `android.jar` 里就带上了 `CompanyManager` 和 `getCompanyId()`。

---

## 六、把新 SDK 给 App 开发者用

App 开发同事拿到你编出的 `android.jar` 后，有两种常见用法：

1. **替换 Android Studio 的 platform android.jar**（简单粗暴）
   路径类似：`<Android SDK>/platforms/android-31/android.jar`（Android 12 = API 31），备份原文件后替换。

2. **正规做法**：把定制 SDK 打成 `.zip`（第四步产出的那个），通过 Android Studio 的 SDK Manager 以自定义 SDK 形式安装。

这样 App 里写 `getSystemService("company")` 才能在编译期识别到你的新接口。

> ⚠️ 提醒：App 编译能过 ≠ 运行能成功。**只有刷了你带 CompanyService 的定制系统的设备**，运行时才真正有这个服务。普通手机没有你的定制框架，运行会拿到 null。

---

## 七、新手常见坑速查

| 现象 | 原因 / 解决 |
|------|-------------|
| `repo sync` 巨慢/失败 | 用公司内网源；加 `-j` 别太大；断了重跑 `repo sync` 会续传 |
| 编译报磁盘/内存不足 | 清 `out/` 目录；加大内存或 swap |
| 加了 API 编译报 api 不一致 | 忘了 `make update-api` |
| 改了代码不生效 | 确认改的是**公司分支**的源码；`make` 有缓存，必要时 `make clean`（慎用，会全量重编）|
| 想加快调试 | 别每次 `make sdk`，先 `make framework` 验证逻辑，最后再打完整 SDK |
| `@hide` 的方法 App 用不了 | 对，那是内部 API；要给 App 用就别加 `@hide` 并跑 update-api |

---

## 八、建议的学习路径

1. 先**完整跑通一次** `lunch sdk-eng` → `make sdk`，别急着改代码，先确认环境 OK。
2. 再做一个**最小改动**：在某个已有类（比如 `Build.java`）加一个 public static 常量 → `make update-api` → `make sdk`，验证它出现在新 `android.jar` 里。
3. 最后才做上面完整的 SystemService 流程。

由简到繁，每一步都验证，比一上来就整大工程稳得多。

---

## 附：进阶方向（需要时再深入）

- **公司定制场景**下 manifest / 分支怎么对接
- **AIDL 跨进程接口**的完整写法
- 用 **`m` / `mm` / `mmm`** 做增量编译加速调试
- **SystemApi / hide API** 权限控制（哪些接口只给系统 App、哪些给第三方 App）
