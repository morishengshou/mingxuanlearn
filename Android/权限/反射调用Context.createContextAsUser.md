前提已满足（priv-app、平台签名、权限已授予），那么你可以用反射安全地调用 createContextAsUser，并在旧平台上回退到已废弃的 createPackageContextAsUser。下面给出可直接复用的实现。

Kotlin 实现
```kotlin
@Suppress("DiscouragedPrivateApi")
fun createContextAsUserReflective(
    base: Context,
    user: UserHandle,
    flags: Int = 0
): Context {
    try {
        // 优先使用 public API（有的 ROM/编译环境可能因 stubs 问题不可见）
        val m = Context::class.java.getMethod(
            "createContextAsUser",
            UserHandle::class.java,
            Int::class.javaPrimitiveType
        )
        return m.invoke(base, user, flags) as Context
    } catch (e: NoSuchMethodException) {
        // 旧版本回退：createPackageContextAsUser(String, int, UserHandle)
        try {
            val m2 = Context::class.java.getMethod(
                "createPackageContextAsUser",
                String::class.java,
                Int::class.javaPrimitiveType,
                UserHandle::class.java
            )
            return m2.invoke(base, base.packageName, 0, user) as Context
        } catch (inner: Exception) {
            throw RuntimeException("No cross-user context creation API available", inner)
        }
    } catch (e: InvocationTargetException) {
        val cause = e.cause ?: e
        if (cause is SecurityException) throw cause
        throw RuntimeException("createContextAsUser invocation failed", cause)
    }
}
```

Java 实现
```java
public static Context createContextAsUserReflective(Context base, UserHandle user, int flags) throws Exception {
    try {
        java.lang.reflect.Method m = Context.class.getMethod(
                "createContextAsUser", UserHandle.class, int.class);
        return (Context) m.invoke(base, user, flags);
    } catch (NoSuchMethodException e) {
        // Fallback for older platforms
        try {
            java.lang.reflect.Method m2 = Context.class.getMethod(
                    "createPackageContextAsUser", String.class, int.class, UserHandle.class);
            return (Context) m2.invoke(base, base.getPackageName(), 0, user);
        } catch (Exception inner) {
            throw new RuntimeException("No cross-user context creation API available", inner);
        }
    } catch (java.lang.reflect.InvocationTargetException ite) {
        Throwable cause = ite.getCause();
        if (cause instanceof SecurityException) throw (SecurityException) cause;
        throw new RuntimeException("createContextAsUser invocation failed", cause != null ? cause : ite);
    }
}
```

获取 UserHandle（兼容方式）
```kotlin
fun userHandleOf(userId: Int): UserHandle {
    return try {
        val of = UserHandle::class.java.getMethod("of", Int::class.javaPrimitiveType)
        of.invoke(null, userId) as UserHandle
    } catch (_: NoSuchMethodException) {
        val ctor = UserHandle::class.java.getDeclaredConstructor(Int::class.javaPrimitiveType)
        ctor.isAccessible = true
        ctor.newInstance(userId)
    }
}
```

用法示例
```kotlin
val targetUser = userHandleOf(10) // 目标 userId
val otherCtx = createContextAsUserReflective(appContext, targetUser, 0)
val pm = otherCtx.packageManager
```

注意
- 即便反射成功，仍会执行同样的权限校验；你已在 priv-app 并具备相应权限即可通过。
- 在 Android 10+ 仍受包可见性影响；必要时在 manifest 声明 QUERY_ALL_PACKAGES 或添加 queries。