*Thinking...*

> **Planning comprehensive tutorial**

太好了，这个阶段学线程池非常合适。你已经有 Java 基础语法了，接下来把线程池吃透，会让你对并发理解上一个台阶。

我给你一篇**“新手友好版线程池教程”**：先讲概念，再上代码，再给口诀记忆。

---

## 1. 先用一句话理解线程池

**线程池 = 一组可复用的工作线程 + 一个任务队列 + 一套调度规则。**

你可以把它想象成餐厅：

- 厨师 = 线程  
- 点菜单 = 任务  
- 后厨等单区 = 队列  
- 厨师团队管理规则 = 线程池参数

---

## 2. 为什么要线程池，不直接 `new Thread()`？

直接 `new Thread()` 的问题：

1. 创建/销毁线程有开销  
2. 线程太多会抢 CPU、抢内存  
3. 缺少统一管理（命名、监控、拒绝策略）

线程池的好处：

- 线程复用，性能更稳  
- 可以限制并发数量，防止系统被压垮  
- 有拒绝策略，系统“可控降级”

---

## 3. 线程池的核心类

Java 里你最需要掌握的是：

- `Executor`：执行任务的顶层接口  
- `ExecutorService`：增强版（可关闭、提交有返回值任务）  
- `ThreadPoolExecutor`：最核心实现类（生产常用）

---

## 4. 线程池最重要：7个参数（必须会）

`ThreadPoolExecutor` 构造器常见版：

```java
new ThreadPoolExecutor(
    corePoolSize,        // 核心线程数
    maximumPoolSize,     // 最大线程数
    keepAliveTime,       // 非核心线程空闲存活时间
    unit,                // 时间单位
    workQueue,           // 任务队列
    threadFactory,       // 线程工厂（用于命名等）
    handler              // 拒绝策略
);
```

---

## 5. 一条最关键的“执行流程口诀”

### 口诀（非常重要）
**核心先上岗，队列后排队，队满再扩容，满员走拒绝。**

对应流程：

1. 当前线程数 < `corePoolSize`：创建核心线程执行任务  
2. 否则任务进队列 `workQueue`  
3. 队列满了且线程数 < `maximumPoolSize`：创建非核心线程  
4. 如果也到上限：触发拒绝策略 `handler`

---

## 6. 第一个可运行例子（入门版）

> 用 `execute()` 提交无返回值任务

```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class PoolDemo1 {
    public static void main(String[] args) {
        ExecutorService pool = Executors.newFixedThreadPool(3);

        for (int i = 1; i <= 8; i++) {
            int taskId = i;
            pool.execute(() -> {
                String t = Thread.currentThread().getName();
                System.out.println(t + " 正在执行任务 " + taskId);
                try {
                    Thread.sleep(500);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
        }

        pool.shutdown();
    }
}
```

你会看到：只有 3 个线程来回处理 8 个任务（线程复用）。

---

## 7. 第二个例子：`submit()` + `Future`（有返回值）

```java
import java.util.concurrent.*;

public class PoolDemo2 {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        Future<Integer> future = pool.submit(() -> {
            Thread.sleep(1000);
            return 42;
        });

        System.out.println("主线程先做别的事...");
        Integer result = future.get(); // 阻塞等待结果
        System.out.println("异步任务结果: " + result);

        pool.shutdown();
    }
}
```

记忆点：

- `execute(Runnable)`：只执行，不关心返回值  
- `submit(Callable)`：可拿结果（`Future`）

---

## 8. 生产更推荐：手动创建 `ThreadPoolExecutor`

`Executors` 工厂方法学习方便，但生产常常建议手动指定参数，避免无界队列/线程导致风险。

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class PoolDemo3 {
    public static void main(String[] args) {
        ThreadFactory factory = new ThreadFactory() {
            private final AtomicInteger idx = new AtomicInteger(1);
            @Override
            public Thread newThread(Runnable r) {
                return new Thread(r, "biz-pool-" + idx.getAndIncrement());
            }
        };

        RejectedExecutionHandler rejectHandler = new ThreadPoolExecutor.CallerRunsPolicy();

        ThreadPoolExecutor pool = new ThreadPoolExecutor(
                2,                              // core
                4,                              // max
                30, TimeUnit.SECONDS,           // keepAlive
                new ArrayBlockingQueue<>(2),    // queue
                factory,
                rejectHandler
        );

        for (int i = 1; i <= 10; i++) {
            int taskId = i;
            pool.execute(() -> {
                String t = Thread.currentThread().getName();
                System.out.println(t + " 执行任务 " + taskId);
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
        }

        pool.shutdown();
    }
}
```

---

## 9. 拒绝策略（面试高频）

常见 4 种：

1. `AbortPolicy`：直接抛异常（默认）  
2. `CallerRunsPolicy`：让提交任务的线程自己执行（削峰限流常用）  
3. `DiscardPolicy`：静默丢弃  
4. `DiscardOldestPolicy`：丢弃队列最老任务，再尝试提交

### 口诀
**“抛、调、丢、挤老”**  
- 抛：抛异常  
- 调：调用者执行  
- 丢：直接丢  
- 挤老：挤掉最老任务

---

## 10. 线程池大小怎么估算？

粗略经验：

- **CPU 密集型**：线程数约 \(N_{cpu} + 1\)  
- **IO 密集型**：线程数可更大，常见约 \(2 \times N_{cpu}\) 起步，再压测调整

更通用估算：

\[
N_{threads} \approx N_{cpu} \times \left(1 + \frac{W}{C}\right)
\]

其中 \(W\) 是等待时间（IO），\(C\) 是计算时间。

---

## 11. 正确关闭线程池（非常容易忘）

```java
pool.shutdown(); // 平滑关闭：不接收新任务，等待旧任务完成
```

如果需要强制：

```java
pool.shutdownNow(); // 尝试中断正在执行任务
```

推荐模板：

```java
pool.shutdown();
try {
    if (!pool.awaitTermination(60, TimeUnit.SECONDS)) {
        pool.shutdownNow();
    }
} catch (InterruptedException e) {
    pool.shutdownNow();
    Thread.currentThread().interrupt();
}
```

---

## 12. 新手常见坑

1. 任务里吞掉异常，不打印日志  
2. 队列设太大，导致内存压力  
3. 用 `Future.get()` 放在循环里导致“伪并发”  
4. 忘记 `shutdown()`，程序不退出  
5. 线程池里执行“长时间阻塞任务”却没隔离池子

---

## 13. 最后给你一套“总口诀”

### 线程池总口诀（建议背）
**“核心先干活，忙了先排队；队满再扩容，满了走拒绝；任务分类型，参数靠压测；提交要控错，结束要关闭。”**

---

如果你愿意，我下一步可以给你一份：

- **“线程池练习题 10 道（附答案）”**  
- 或者 **“从 0 手写一个简化版线程池”**（非常锻炼理解）  
你选一个，我按你的节奏继续带你学。