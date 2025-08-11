在Android开发中，`onClickListener`（以及其他匿名内部类或非静态内部类）很容易导致**内存泄漏**。这是因为它会隐式持有外部类（如`Activity`或`Fragment`）的引用。如果外部类被销毁，但`onClickListener`还持有其引用，就会造成泄漏。

以下是**防止内存泄漏的主要方法**：

---

## 1. 避免匿名内部类直接持有Activity引用

**问题示例**：

```java
// 会造成泄漏
button.setOnClickListener(new View.OnClickListener() {
    @Override
    public void onClick(View v) {
        // 这里隐式持有外部Activity引用
        doSomething();
    }
});
```

---

## 2. 使用静态内部类 + 弱引用

**推荐方法**：

```java
static class MyClickListener implements View.OnClickListener {
    private WeakReference<Activity> activityRef;

    MyClickListener(Activity activity) {
        activityRef = new WeakReference<>(activity);
    }

    @Override
    public void onClick(View v) {
        Activity activity = activityRef.get();
        if (activity != null) {
            // 安全地操作activity
        }
    }
}

// 使用
button.setOnClickListener(new MyClickListener(this));
```

---

## 3. 在`onDestroy()`中及时解除监听器

```java
@Override
protected void onDestroy() {
    super.onDestroy();
    button.setOnClickListener(null);
}
```

---

## 4. 尽量使用lambda表达式（Java 8及以上）

lambda表达式在某些情况下不会生成额外的内部类，但依然会捕获外部引用。如果用在短生命周期的View上通常没问题，但长生命周期或跨线程要小心。

---

## 5. 使用全局或单例的Listener时，**不要持有Context/Activity引用**

例如：

```java
// 错误示范
public class MySingletonListener implements View.OnClickListener {
    private Context ctx;
    // ...
}
```
这种写法会导致全局泄漏。

---

## 总结

- **静态内部类+WeakReference** 是最安全的方式
- 不再需要监听时，及时解除监听器
- 避免Listener间接引用Activity或Context
- 注意lambda表达式也可能捕获外部引用

---

### 参考实例（常用写法）

```java
public class MainActivity extends AppCompatActivity {

    private Button button;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        button = findViewById(R.id.button);

        button.setOnClickListener(new SafeClickListener(this));
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        button.setOnClickListener(null); // 解除监听
    }

    private static class SafeClickListener implements View.OnClickListener {
        private final WeakReference<MainActivity> activityRef;

        SafeClickListener(MainActivity activity) {
            activityRef = new WeakReference<>(activity);
        }

        @Override
        public void onClick(View v) {
            MainActivity activity = activityRef.get();
            if (activity != null && !activity.isFinishing()) {
                // do something
            }
        }
    }
}
```

---

有任何具体场景可以继续追问！