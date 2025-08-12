如果你的应用是系统/特权应用（priv-app，且用平台证书签名），并且能够获批系统级签名权限，那么在 Android 14（SDK 34）及以上可以直接通过 UserManager 的 @SystemApi 列举“所有用户”，再取出各自的 userId。

要点概览
- 需要权限（签名级，普通应用拿不到）：
  - android.permission.MANAGE_USERS（列举/管理用户）
  - 建议：android.permission.INTERACT_ACROSS_USERS 或 android.permission.INTERACT_ACROSS_USERS_FULL（若后续还要跨用户访问/操作）
- 需要编译时使用“system SDK”（android-34-extN），这样才能直接调用 @SystemApi（如 UserManager#getUsers）。若使用公开 SDK，请改用厂商提供的 hidden API 豁免或采用 AIDL 直连 IUserManager（见下文“方案 B”）。

清单权限（Manifest）
```xml
<manifest ...>
    <uses-permission android:name="android.permission.MANAGE_USERS"/>
    <!-- 如需跨用户操作或查询进程/应用状态，添加以下其一（签名权限） -->
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS"/>
    <!-- 或更强 -->
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS_FULL"/>
</manifest>
```

方案 A：使用 @SystemApi（推荐，需用 system SDK 编译）
```java
import android.content.Context;
import android.os.UserHandle;
import android.os.UserManager;
// @SystemApi:
import android.content.pm.UserInfo;

public final class UsersHelper {
    public static List<Integer> getAllUserIds(Context context) {
        UserManager um = context.getSystemService(UserManager.class);

        // 方式 1：最简单，返回所有已存在的用户（包含非运行、已初始化的用户）
        List<UserInfo> users = um.getUsers(); // 需要 MANAGE_USERS

        // 如需过滤“将被移除/未完全准备/预创建”的用户，部分平台还提供重载或对应方法：
        // List<UserInfo> users = um.getAliveUsers(); // 如果你的 system SDK 暴露了该 @SystemApi

        List<Integer> ids = new ArrayList<>(users.size());
        for (UserInfo ui : users) {
            ids.add(ui.id); // 直接是 int userId
            // 可选：根据需求查看用户属性
            // boolean admin = ui.isAdmin();
            // boolean guest = ui.isGuest();
            // boolean profile = ui.isProfile();
            // boolean ephemeral = ui.isEphemeral();
        }
        return ids;
    }

    // 如果你只想要 UserHandle：
    public static List<UserHandle> getAllUserHandles(Context context) {
        UserManager um = context.getSystemService(UserManager.class);
        // 部分平台的 @SystemApi 提供：
        // List<UserHandle> handles = um.getUserHandles(/* excludeDying */ true);
        // 如果没有该方法，就通过 users 转换：
        List<UserHandle> handles = new ArrayList<>();
        for (UserInfo ui : um.getUsers()) {
            handles.add(ui.getUserHandle());
        }
        return handles;
    }
}
```

补充：仅获取“正在运行”的用户（可选）
- 某些场景只需要当前运行的用户 ID，可用 ActivityManager 的 @SystemApi。
```java
import android.app.ActivityManager;

ActivityManager am = context.getSystemService(ActivityManager.class);
// @SystemApi，需要 INTERACT_ACROSS_USERS(_FULL)
int[] runningUserIds = am.getRunningUserIds();
```

方案 B：无法用 system SDK 时，直接调 IUserManager（AIDL，厂商设备常用）
- 前提：你有平台签名/特权，并在设备上对你的包做了 hidden API 豁免或不依赖 hidden API。
- 做法：把 AOSP 中的 AIDL 拷入工程（包名路径必须一致），通过 Binder 获取 “user” 服务并调用。
- 关键接口（示意）：
  - android.os.IUserManager.getUsers(boolean excludePartial, boolean excludeDying, boolean excludePreCreated)
- 代码示例（简化示意，需你将对应 AIDL 拷贝到相同 package）：
```java
import android.os.IBinder;
import android.os.RemoteException;
import android.os.ServiceManager;      // 注意：某些平台此类为 @SystemApi/hidden，需要豁免或替代方案
import android.os.IUserManager;       // 你从 AOSP 同步的 AIDL 生成的接口
import android.content.pm.UserInfo;

public static List<Integer> getAllUserIdsViaAidl() throws RemoteException {
    IBinder b = ServiceManager.getService("user"); // Context.USER_SERVICE 的底层服务名
    IUserManager im = IUserManager.Stub.asInterface(b);
    // 过滤“未就绪/即将移除/预创建”的用户
    List<UserInfo> users = im.getUsers(/*excludePartial*/ true,
                                       /*excludeDying*/ true,
                                       /*excludePreCreated*/ true);
    List<Integer> ids = new ArrayList<>(users.size());
    for (UserInfo ui : users) ids.add(ui.id);
    return ids;
}
```
注意：
- 直接用 ServiceManager 在部分平台属于隐藏 API；推荐优先走方案 A。
- AIDL 方案的可行性取决于厂商对隐藏 API 的策略与豁免配置。

常见坑与建议
- 必须为“特权应用”：APK 放在 /system/priv-app 且用平台证书签名，否则签名权限不会被授予，即使在 Manifest 里声明也无效。
- targetSdk 34 起对跨用户权限进一步收紧；仅列举用户用 MANAGE_USERS 足够，但跨用户做其他操作需 INTERACT_ACROSS_USERS(_FULL)。
- 对“预创建用户”、“访客（ephemeral）”、“待删除用户”要按业务需要过滤（见上面的 exclude* 参数或使用 getAliveUsers）。
- 如果只做与当前用户关联的 profile 相关操作，用公开 API（UserManager#getUserProfiles）即可，无需系统权限。

如果你能说明是要“所有存在的用户”、还是“仅运行中的用户”、要不要包含“预创建/访客”，我可以给出更精准的过滤代码模板。