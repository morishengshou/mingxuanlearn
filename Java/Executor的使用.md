# Java Executor 使用详解（含常见错误反例与避坑指南）

本文面向多线程初学者，系统讲解 Java Executor/线程池的使用方法、配置思路、异常与关闭策略，并附带一组“错误反例 + 正确写法”帮助你避开常见坑。

---

## 1. 为什么用 Executor/线程池

- 线程创建和销毁成本高；手动 `new Thread(...).start()` 不易统一管理、监控和关闭。
- Executor 把“任务提交”和“任务执行”解耦：你只关心提交的任务，池子负责复用线程、排队、限流、拒绝策略等。
- 能更容易做到：
  - 控制并发度（线程数、队列长度）
  - 负载背压（排队/拒绝）
  - 统一命名与日志
  - 优雅关闭
  - 定时与周期任务

---

## 2. 核心概念与接口

- Runnable vs Callable
  - Runnable 无返回值，不能直接抛受检异常。
  - Callable<V> 有返回值，`Future<V>` 可获取结果/异常。
- Executor / ExecutorService
  - `execute(Runnable)` 提交任务，无返回值。
  - `submit(Callable|Runnable)` 返回 `Future`，可 `get()` 结果/异常。
  - `invokeAll`/`invokeAny` 批量提交。
- ScheduledExecutorService
  - `schedule`、`scheduleAtFixedRate`、`scheduleWithFixedDelay` 执行定时/周期任务。
- Future
  - `get()` 阻塞等待；`get(timeout, unit)` 超时等待；
  - `cancel(boolean mayInterruptIfRunning)` 取消任务（尝试中断）。
- CompletionService
  - 提交多个任务，按“完成先后”消费结果，避免某个慢任务导致全体等待。

---

## 3. 最小可用例子（演示流程：提交、获取结果、关闭）

> 演示用 `Executors.newFixedThreadPool`，实际生产建议用 ThreadPoolExecutor 显式配置（见后文）。

```java
import java.util.*;
import java.util.concurrent.*;

public class SimpleExecutorDemo {
    public static void main(String[] args) throws InterruptedException {
        ExecutorService pool = Executors.newFixedThreadPool(4); // 演示用

        try {
            List<Callable<Integer>> tasks = new ArrayList<>();
            for (int i = 0; i < 10; i++) {
                int n = i;
                tasks.add(() -> {
                    // 模拟计算
                    TimeUnit.MILLISECONDS.sleep(200);
                    if (n == 5) throw new RuntimeException("模拟异常: n=5");
                    return n * n;
                });
            }

            List<Future<Integer>> futures = new ArrayList<>();
            for (Callable<Integer> task : tasks) futures.add(pool.submit(task));

            for (Future<Integer> f : futures) {
                try {
                    // 建议带超时，避免永久阻塞
                    Integer val = f.get(1, TimeUnit.SECONDS);
                    System.out.println("result: " + val);
                } catch (ExecutionException e) {
                    System.err.println("任务异常: " + e.getCause());
                } catch (TimeoutException e) {
                    System.err.println("任务超时，尝试取消");
                    f.cancel(true);
                }
            }
        } finally {
            pool.shutdown();
            if (!pool.awaitTermination(5, TimeUnit.SECONDS)) {
                pool.shutdownNow();
            }
        }
    }
}
```

---

## 4. 线程池类型与选择

- Executors 工厂方法（简便但有坑）
  - `newFixedThreadPool(n)`：固定线程数，队列是无界的 LinkedBlockingQueue（可能导致内存膨胀）。
  - `newCachedThreadPool()`：线程数不设上限，瞬时流量大时可能创建过多线程。
  - `newSingleThreadExecutor()`：单线程串行执行，队列无界（同样有内存隐患）。
  - `newScheduledThreadPool(n)`：定时/周期任务。

- 生产建议：直接使用 ThreadPoolExecutor，显式设置队列容量和拒绝策略，实现“背压”。

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class Pools {
    public static ThreadFactory namedThreadFactory(String poolName, boolean daemon) {
        AtomicInteger idx = new AtomicInteger(1);
        return r -> {
            Thread t = new Thread(r, poolName + "-" + idx.getAndIncrement());
            t.setDaemon(daemon);
            // 可设置UncaughtExceptionHandler用于 execute() 抛出的运行时异常
            t.setUncaughtExceptionHandler((thr, ex) ->
                    System.err.println("未捕获异常于 " + thr.getName() + ": " + ex));
            return t;
        };
    }

    public static ThreadPoolExecutor boundedPool(String name,
                                                 int core, int max,
                                                 int queueCapacity) {
        return new ThreadPoolExecutor(
                core,
                max,
                60, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(queueCapacity), // 有界队列，形成背压
                namedThreadFactory(name, false),
                new ThreadPoolExecutor.CallerRunsPolicy() // 拒绝时回退到调用线程执行
        );
    }
}
```

何时用什么（经验值，需按业务压测调整）：
- CPU 密集型：线程 ≈ CPU核数 或 核数+1，队列小，避免上下文切换。
- I/O 密集型：线程数可高于核数（例如 2×~4× 核数），或用虚拟线程（见下文）。
- 使用有界队列（例如 1k~100k 视内存和任务大小），结合 CallerRuns/自定义限流。

---

## 5. Java 21+：虚拟线程（可选但强烈建议了解）

如果是 Java 21+，可以直接使用虚拟线程，大幅简化 I/O 型并发：

```java
try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<String> f = pool.submit(() -> {
        // 看起来像同步写法，但虚拟线程可挂起无需占用内核线程
        TimeUnit.MILLISECONDS.sleep(200);
        return "OK";
    });
    System.out.println(f.get());
}
```

注意：
- 虚拟线程数量几乎可忽略不计（百万级），非常适合阻塞式 I/O。
- 仍需注意：任务中的 `ThreadLocal` 清理、超时与取消、异常处理、关闭池等基本原则。

---

## 6. 提交任务的 API 正确用法

- `execute(Runnable)`：无返回值；任务异常会走线程的 UncaughtExceptionHandler。
- `submit(Callable|Runnable)`：返回 `Future`；异常会封装在 `ExecutionException` 中，只有 `get()` 时你才会知道——常见坑是没人调用 `get()` 导致异常悄悄丢失。
- `invokeAll(Collection, timeout, unit)`：批量并等待全部完成或超时，便于一次性取消未完成任务。
- `invokeAny(Collection, timeout, unit)`：任意一个完成就返回，适合“竞速”策略。
- `CompletionService`：谁先完成先取谁，避免慢任务拖累快任务的结果消费。

示例（CompletionService）：

```java
ExecutorService pool = Pools.boundedPool("work", 4, 8, 1000);
CompletionService<String> ecs = new ExecutorCompletionService<>(pool);

for (int i = 0; i < 10; i++) {
    int n = i;
    ecs.submit(() -> {
        TimeUnit.MILLISECONDS.sleep(100 + n * 10);
        return "task-" + n;
    });
}

for (int i = 0; i < 10; i++) {
    Future<String> f = ecs.take(); // 谁先完成先取谁
    System.out.println("done: " + f.get());
}

pool.shutdown();
```

---

## 7. 定时与周期任务：ScheduledExecutorService

- `schedule(Runnable/Callable, delay, unit)`：延迟一次执行。
- `scheduleAtFixedRate(task, initialDelay, period, unit)`：
  - 按固定频率执行。若任务执行时间 > period，下次会“赶进度”（紧接着再触发）。
- `scheduleWithFixedDelay(task, initialDelay, delay, unit)`：
  - 每次执行完再延迟 delay 后启动下一次，更适合确保不重叠。

重要细节：
- 周期任务如果抛出未捕获异常，将被取消且不再调度（常见坑）。请在任务内部捕获并记录异常。
- 为避免取消的任务残留在队列导致内存泄漏，对 ScheduledThreadPoolExecutor 启动清理策略。

示例：

```java
ScheduledThreadPoolExecutor ses = (ScheduledThreadPoolExecutor)
        Executors.newScheduledThreadPool(2, Pools.namedThreadFactory("sched", true));

// 取消后从队列移除，避免内存积压
ses.setRemoveOnCancelPolicy(true);

ses.scheduleAtFixedRate(() -> {
    try {
        // 你的任务逻辑
        System.out.println("tick " + System.currentTimeMillis());
        // 如果这里抛出异常，整个周期任务会停止；所以务必捕获
    } catch (Throwable t) {
        System.err.println("周期任务异常: " + t);
    }
}, 0, 1, TimeUnit.SECONDS);

// ... 业务结束时关闭
ses.shutdown();
```

---

## 8. 异常处理与日志

- execute vs submit 的异常区别：
  - execute：任务未捕获的 RuntimeException 会交给线程的 UncaughtExceptionHandler。
  - submit：异常包进 Future；如果没人 `get()`，异常就“默默消失”。
- 针对 submit 的“异常吞掉”问题，可以：
  - 始终对返回的 Future 调用 `get()`（建议带超时）。
  - 或自定义 ThreadPoolExecutor，覆盖 `afterExecute`，统一探测并记录 Future 的异常。

示例：统一日志记录任务异常

```java
public class LoggingThreadPool extends ThreadPoolExecutor {
    public LoggingThreadPool(int core, int max, int queueCapacity, String name) {
        super(core, max, 60, TimeUnit.SECONDS,
              new LinkedBlockingQueue<>(queueCapacity),
              Pools.namedThreadFactory(name, false),
              new CallerRunsPolicy());
    }

    @Override
    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);
        // 对 execute() 抛出的异常：t 非空
        if (t != null) {
            System.err.println("任务异常(直接抛出): " + t);
            return;
        }
        // 对 submit() 的异常：需要从 Future 中提取
        if (r instanceof Future<?> f) {
            try {
                if (f.isDone()) f.get();
            } catch (CancellationException e) {
                System.err.println("任务被取消");
            } catch (ExecutionException e) {
                System.err.println("任务异常(Future): " + e.getCause());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }
}
```

---

## 9. 拒绝策略与背压

- 常见策略：
  - AbortPolicy（默认）：抛 RejectedExecutionException
  - CallerRunsPolicy：在提交线程里执行（回退、限速）
  - DiscardPolicy / DiscardOldestPolicy：丢弃（谨慎使用）
- 一般建议搭配有界队列 + CallerRunsPolicy 或自定义策略，确保系统在过载时“慢下来”，而不是 OOM 或过多线程。

---

## 10. 优雅关闭线程池

- 标准模式：

```java
ExecutorService pool = ...;
try {
    // 正常提交/执行任务
} finally {
    pool.shutdown(); // 拒绝新任务，等待在执行任务完成
    if (!pool.awaitTermination(30, TimeUnit.SECONDS)) {
        pool.shutdownNow(); // 尝试中断正在执行的任务
    }
}
```

- 捕获 InterruptedException 时要恢复中断位：
  - `catch (InterruptedException e) { Thread.currentThread().interrupt(); ... }`
- 对周期任务：
  - 可能需要在关闭前 cancel 对应的 Future；
  - ScheduledThreadPoolExecutor 可设置 `setExecuteExistingDelayedTasksAfterShutdownPolicy(false)` 让关闭更快停止。

---

## 11. 常见错误反例与正确写法

1) 无界队列导致内存膨胀（newFixedThreadPool 默认队列无界）
```java
// 错误示例：提交速度远大于执行速度时，队列无限增长
ExecutorService pool = Executors.newFixedThreadPool(8);
while (true) {
    pool.submit(() -> heavyTask()); // 可能 OOM
}
```
正确：
```java
ThreadPoolExecutor pool = Pools.boundedPool("work", 8, 16, 10_000);
// 或者在上游限流、批量、背压
```

2) 忘记关闭线程池，进程无法退出
```java
// 错误：无 finally 关闭，JVM 持续存活
ExecutorService pool = Executors.newFixedThreadPool(4);
pool.submit(...);
```
正确：使用 try/finally 或注册 shutdown hook。

3) 使用 submit 却不调用 get，异常被“吞掉”
```java
// 错误：异常只存在于 Future 中，没人 get 就永远不知道
Future<?> f = pool.submit(() -> { throw new RuntimeException("boom"); });
```
正确：调用 `get()` 或使用自定义 afterExecute 统一日志，或用 `execute()` 并设置 UncaughtExceptionHandler。

4) 同一线程池内的“等待自身”死锁
```java
// 错误：单线程池中任务 A 提交任务 B 并等待 B，但池中无空闲线程来执行 B
ExecutorService single = Executors.newSingleThreadExecutor();
single.submit(() -> {
    Future<?> f = single.submit(() -> doSomething());
    f.get(); // 死锁
});
```
正确：
- 使用不同的线程池执行子任务；
- 或重构为同步调用；
- 或增大线程数并避免在池内阻塞等待池内任务。

5) 线程数配置与任务类型不匹配
```java
// 错误：I/O 密集任务使用线程数 = CPU核数，导致吞吐偏低
ExecutorService pool = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
```
正确：
- I/O 密集任务适度增加线程数（2×~4× 核数，或基于 (1 + wait/compute) 估算）；
- Java 21+ 用虚拟线程。

6) 周期任务抛异常后静默停止
```java
// 错误：抛异常后不再执行
ses.scheduleAtFixedRate(() -> { throw new RuntimeException(); }, 0, 1, TimeUnit.SECONDS);
```
正确：在任务内部 try/catch 记录异常，确保周期不被取消。

7) 忽略取消和中断，任务无法尽快停止
```java
// 错误：捕获 InterruptedException 后不恢复中断位
try {
    TimeUnit.SECONDS.sleep(10);
} catch (InterruptedException e) {
    // 什么都不做
}
```
正确：
```java
catch (InterruptedException e) {
    Thread.currentThread().interrupt(); // 恢复中断位
    return; // 退出或清理
}
```

8) ThreadLocal 泄漏/串味（线程池复用线程）
```java
// 错误：放入 ThreadLocal 却不清理
ThreadLocal<String> TL = new ThreadLocal<>();
pool.submit(() -> TL.set("userA"));
// 之后另一个任务可能读到旧值
```
正确：使用后清理 `TL.remove()`；或使用 try/finally 包裹；谨慎使用 InheritableThreadLocal。

9) 在拒绝时悄悄丢任务
```java
// 错误：DiscardPolicy 直接丢弃，无日志
new ThreadPoolExecutor(..., new ThreadPoolExecutor.DiscardPolicy());
```
正确：使用 CallerRunsPolicy，或自定义 RejectedExecutionHandler 记录并告警。

10) Future.get 永久阻塞
```java
// 错误：无超时，若任务卡死则永久等待
f.get();
```
正确：`f.get(3, TimeUnit.SECONDS)`，超时后 cancel，并记录告警、做降级。

11) 在定时任务中执行耗时阻塞操作但使用 fixedRate
```java
// 错误：任务比 period 更慢，导致“追赶”与执行堆叠
ses.scheduleAtFixedRate(this::slowIoTask, 0, 100, TimeUnit.MILLISECONDS);
```
正确：对耗时/不确定耗时的任务更适合 `scheduleWithFixedDelay`，或使用独立工作池处理业务、定时器仅触发调度。

12) 误把重要后台任务线程设为 daemon
```java
// 错误：daemon 线程在 JVM 退出时会被直接终止，任务可能未完成
ThreadFactory f = Pools.namedThreadFactory("critical", true);
```
正确：关键任务线程使用非 daemon；仅对非关键、短生命周期工具型任务使用 daemon。

---

## 12. 监控与诊断

- ThreadPoolExecutor 提供一些监控指标：
  - `getPoolSize()`、`getActiveCount()`、`getLargestPoolSize()`、`getTaskCount()`、`getCompletedTaskCount()`、`getQueue().size()`
- 在日志/指标系统（如 Micrometer）中定期采集，设置告警阈值（队列长度、拒绝次数）。
- 定期 dump 线程（`jstack`）排查阻塞点；使用超时与取消避免僵死。

---

## 13. 小抄：实践建议

- 生产环境优先使用 ThreadPoolExecutor，显式设置有界队列和拒绝策略。
- 任务中：
  - 注意中断处理与超时控制；
  - 异常不要“裸奔”，提交时考虑如何收集异常（Future.get 或 afterExecute）。
- 定时任务中捕获异常，避免周期任务静默停止；需要时 `setRemoveOnCancelPolicy(true)`。
- 避免在同一池内“自我等待”；慎用单线程池做复杂工作。
- 对 I/O 密集任务考虑虚拟线程（Java 21+），或增加线程数。
- 用 ThreadFactory 命名线程，便于诊断；关键任务线程避免 daemon。
- 始终在 finally 中关闭线程池，或使用 try-with-resources 封装 AutoCloseable 包装类。

---

## 14. 进阶示例：综合配置一个“可观测”的业务线程池

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class BusinessPool extends ThreadPoolExecutor {

    public static ThreadFactory namedFactory(String name) {
        AtomicInteger idx = new AtomicInteger(1);
        return r -> {
            Thread t = new Thread(r, name + "-" + idx.getAndIncrement());
            t.setDaemon(false);
            t.setUncaughtExceptionHandler((thr, ex) ->
                    System.err.println("[UEH] " + thr.getName() + " -> " + ex));
            return t;
        };
    }

    public BusinessPool(String name, int core, int max, int queueCapacity) {
        super(core, max, 60, TimeUnit.SECONDS,
              new LinkedBlockingQueue<>(queueCapacity),
              namedFactory(name),
              new CallerRunsPolicy());
        allowCoreThreadTimeOut(true); // 突发型负载下回收空闲核心线程
        prestartAllCoreThreads();     // 预热（可选）
    }

    @Override
    protected void beforeExecute(Thread t, Runnable r) {
        // 记录开始时间、打点...
        super.beforeExecute(t, r);
    }

    @Override
    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);
        if (t != null) {
            System.err.println("[afterExecute] Throwable: " + t);
        } else if (r instanceof Future<?> f) {
            try { if (f.isDone()) f.get(); }
            catch (CancellationException ignored) {}
            catch (ExecutionException e) { System.err.println("[afterExecute] " + e.getCause()); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        }
    }

    public static void main(String[] args) throws InterruptedException {
        BusinessPool pool = new BusinessPool("biz", 8, 16, 2000);
        try {
            for (int i = 0; i < 100; i++) {
                int n = i;
                pool.submit(() -> {
                    if (n % 15 == 0) throw new RuntimeException("boom:" + n);
                    try { TimeUnit.MILLISECONDS.sleep(50); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
                });
            }
        } finally {
            pool.shutdown();
            if (!pool.awaitTermination(10, TimeUnit.SECONDS)) pool.shutdownNow();
            System.out.printf("active=%d, queue=%d, completed=%d%n",
                    pool.getActiveCount(), pool.getQueue().size(), pool.getCompletedTaskCount());
        }
    }
}
```

---

如果你提供具体的业务场景（CPU/I/O 比例、任务耗时分布、峰值 QPS、内存与时延目标、Java 版本），我可以帮你定制线程池参数、拒绝策略与关闭/调度方案。