在 Java 里，`Runnable` 和 `Thread` 的关系可以用一句话概括：**`Runnable` 表示“要执行的任务”，`Thread` 表示“执行任务的线程（载体/调度单位）”。** 两者是**组合（has-a）**关系为主，而不是同一层面的东西。

## 1) 类型关系：接口 vs 类
- `Runnable`：一个函数式接口，只有一个方法：
  ```java
  public interface Runnable {
      void run();
  }
  ```
  它只负责描述“运行逻辑”。

- `Thread`：一个具体类：
  - `Thread` **实现了** `Runnable`（`class Thread implements Runnable`）。
  - `Thread` 代表一个真实的线程对象，负责线程的创建、启动、调度相关操作（如 `start()`、`join()`、优先级、名字等）。

## 2) 常见用法：把 Runnable 交给 Thread 去跑（组合）
最典型的写法是把 `Runnable` 作为“任务”传给 `Thread` 构造器：

```java
Runnable task = () -> System.out.println("running in " + Thread.currentThread().getName());
Thread t = new Thread(task);
t.start(); // 真正创建并启动一个新线程，然后在线程里调用 task.run()
```

这里的关系是：
- `Runnable` 负责 **run 的内容**
- `Thread` 负责 **在新线程里执行该 run**

> 注意：直接调用 `task.run()` 不会启动新线程，只是当前线程普通方法调用。

## 3) Thread 自己也是 Runnable：两种“提供 run 逻辑”的方式
因为 `Thread` 实现了 `Runnable`，所以你可以：

### A. 继承 Thread 并重写 `run()`
```java
Thread t = new Thread() {
    @Override public void run() {
        System.out.println("thread subclass");
    }
};
t.start();
```

### B. 传入 Runnable（更常见、更推荐）
```java
Thread t = new Thread(() -> System.out.println("runnable task"));
t.start();
```

一般推荐 B：**任务与线程机制解耦**，更灵活（任务可复用、便于交给线程池执行等）。

## 4) 当同时“传 Runnable + 重写 run()”会怎样？
如果你写了类似：

```java
Thread t = new Thread(() -> System.out.println("from runnable")) {
    @Override public void run() {
        System.out.println("from thread override");
    }
};
t.start();
```

**实际执行的是重写后的 `Thread.run()`**（即 `"from thread override"`）。  
原因是：最终调用是该 `Thread` 实例的 `run()`，动态绑定到你覆盖的方法；你覆盖后就不再走默认的“转发到 target Runnable”的逻辑了。

（在 JDK 的实现里，`Thread` 内部会保存一个 `target` `Runnable`，默认 `run()` 会在 `target != null` 时调用 `target.run()`；但你重写了 `run()` 就改写了这条路径。）

## 5) 总结一句话
- **`Runnable`：任务（做什么）**
- **`Thread`：线程（在哪个独立执行流里做）**
- 通常是 **`new Thread(runnable).start()`**：线程去执行任务  
- `Thread` 也实现 `Runnable`，但概念上仍应把它当作“执行载体”，把业务逻辑放到 `Runnable`（或更现代的 `Callable`/线程池）里。

如果你愿意，我也可以顺便讲一下 `Runnable` vs `Callable`，以及为什么生产代码更常用 `ExecutorService` / 线程池而不是直接 new `Thread`。