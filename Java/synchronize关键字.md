下面从概念、语法用法、可见性与原子性保证、底层原理、典型应用场景、与不使用 synchronized 的后果、以及与其他并发手段的对比几个方面，系统讲解 Java 的 synchronized 关键字。

一、synchronized 是什么
- synchronized 是 Java 提供的内置（内建）锁机制，用于多线程并发控制。
- 它同时解决两个核心问题：
  1) 原子性：保证被保护的临界区在同一时刻只能被一个线程执行（互斥）。
  2) 有序性/可见性：进入/退出临界区时建立 happens-before 关系，确保共享变量在临界区内的写入对随后获得同一把锁的线程可见（通过内存屏障与缓存刷新）。

二、语法与用法
1) 同步实例方法
- 写法：在方法签名加 synchronized
- 作用：以“当前实例对象 this”为锁，同一对象上的该方法在同一时刻只能被一个线程执行
- 例子：
```java
public class Counter {
    private int count = 0;

    public synchronized void incr() { // 锁对象: this
        count++;
    }

    public synchronized int get() {   // 锁对象: this
        return count;
    }
}
```
- 注意：不同实例互不影响；若多线程持有的是不同实例，仍可能并发修改彼此的状态。

2) 同步静态方法
- 写法：在静态方法签名加 synchronized
- 作用：以“类对象 Class<?>”（如 Counter.class）为锁，保护静态共享资源
```java
public class GlobalId {
    private static long id = 0;

    public static synchronized long nextId() { // 锁对象: GlobalId.class
        return ++id;
    }
}
```

3) 同步代码块
- 写法：synchronized(锁对象) { 临界区 }
- 作用：自定义锁对象，控制更细粒度范围
```java
private final Object lock = new Object();
private int balance = 0;

public void deposit(int amount) {
    synchronized (lock) {
        balance += amount;
    }
}
```
- 要点：
  - 锁对象必须是所有线程可见且一致的引用，常见选择：this、某个私有 final 对象、类对象。
  - 不要使用可变的锁对象引用（避免被替换导致“锁失效”）。
  - 不要用字符串字面量等全局常量作为锁（可能与别处意外共享锁，产生无意的竞争或死锁）。

三、synchronized 解决了什么问题
1) 互斥访问（原子性）
- 确保临界区代码（如复合操作：读取-计算-写入）不可被并发打断。
- 典型：count++ 在字节码层面是读取-加一-写回三步，非原子；加锁后变为原子。

2) 内存可见性与有序性
- 进入 synchronized 块前会从主内存刷新共享变量，退出时会把写入刷新到主内存。
- synchronized 的释放锁操作对随后获得同一锁的线程建立 happens-before：前者在临界区内的写入对后者可见。
- 这避免了 CPU 缓存、指令重排带来的“看不见别人写入”的问题。

四、底层原理（简述）
- 每个对象在 JVM 层面都可以作为监视器锁（monitor）。synchronized 编译后会插入 monitorenter/monitorexit 指令。
- HotSpot 中可能经历无锁 → 偏向锁 → 轻量级锁 → 重量级锁的状态升级，以降低无竞争或轻竞争下的开销。
- 退出临界区时伴随内存屏障，保证可见性和有序性。

五、典型应用场景
- 保护共享可变状态：计数器、余额、队列、缓存结构等。
- 复合操作的原子性：检查-更新（check-then-act）、读取-修改-写回。
- 实现线程安全的懒加载（但现代更推荐使用更清晰的并发工具）。
- 构建更高层并发原语（配合 wait/notify）。

六、与 wait/notify 的配合
- synchronized 还用于对象监视器的条件等待/通知机制：
```java
synchronized (lock) {
    while (!condition) {
        lock.wait();  // 释放锁并挂起，等待被通知
    }
    // 条件满足后的处理
}
```
- 另一个线程在同一锁上执行：
```java
synchronized (lock) {
    // 改变条件
    lock.notify(); // 或 notifyAll()
}
```
- 要点：
  - wait/notify 必须在持有同一把锁的 synchronized 块内调用。
  - 使用 while 而非 if 重复检查条件，防止虚假唤醒和竞态。

七、如果不使用 synchronized 会出现什么问题
- 竞态条件（Race Condition）：多个线程同时读写共享变量，执行顺序不确定导致不一致结果。
  - 示例：未加锁的 count++，最终结果小于预期。
- 可见性问题（Visibility Issue）：一个线程对共享变量的更新，另一个线程可能永远看不见（缓存/重排）。
  - 示例：一个线程设置 flag=true 作为退出信号，另一个线程可能一直读到 false，导致无法退出。
- 失序问题（Reordering）：没有同步约束时，指令可能被重排，破坏逻辑前后依赖。
  - 示例：双重检查锁定在没有适当内存屏障时可能读取到未完全初始化的对象。
- ABA 与中间态观察：读到对象或数据结构的中间更新状态（如链表插入删除过程）。
- 死锁/活锁的规避难度增加：不当的部分同步可能更容易产生复杂的并发缺陷（虽然死锁本身与是否使用 synchronized 无必然正负关系，但正确使用能形成清晰的一致锁顺序）。

八、最佳实践与注意事项
- 锁的粒度：尽量缩小临界区，只包围共享可变状态的读写；但不要过度切分导致竞态。
- 锁对象选择：使用私有 final 对象或 this/类对象，保持一致性与封装性。
- 避免在持锁期间执行可能阻塞的操作（I/O、网络、sleep）或调用外部未知代码，降低死锁与性能风险。
- 避免嵌套多个锁，若必须嵌套，统一锁获取顺序。
- 对于高并发性能需求，考虑替代方案：
  - java.util.concurrent 包中的 ReentrantLock（可中断、公平、尝试加锁、条件队列）、ReadWriteLock。
  - 原子类（AtomicInteger 等）用于简单数值更新。
  - 并发集合（ConcurrentHashMap 等）。
  - volatile 用于仅需可见性的“标志位”场景（不提供复合操作原子性）。

九、synchronized vs volatile vs ReentrantLock（简短对比）
- synchronized：互斥 + 可见性；语义简单，异常安全（自动释放锁），缺点是功能较少，无法中断等待，无法尝试加锁。
- volatile：仅保证可见性与一定的有序性，不保证复合操作原子性；适合状态标志、发布已初始化对象。
- ReentrantLock：功能更强（tryLock、lockInterruptibly、公平锁、多个Condition），需要手动 unlock，适合复杂同步场景或性能调优。

十、简单示例：计数器对比
1) 未加锁（错误）
```java
class BadCounter {
    private int count = 0;
    public void incr() { count++; } // 非原子，存在竞态
    public int get() { return count; }
}
```

2) synchronized 保障
```java
class SyncCounter {
    private int count = 0;
    public synchronized void incr() { count++; }
    public synchronized int get() { return count; }
}
```

3) 使用并发工具的替代（性能更高）
```java
import java.util.concurrent.atomic.AtomicInteger;

class AtomicCounter {
    private final AtomicInteger count = new AtomicInteger();
    public void incr() { count.incrementAndGet(); }
    public int get() { return count.get(); }
}
```

总结
- synchronized 提供内建互斥与内存可见性，解决共享可变状态在多线程下的竞态与可见性问题。
- 正确使用的关键在于：选择一致的锁对象、包裹所有访问共享状态的路径、缩小临界区、避免持锁阻塞。
- 不使用（或错误使用）时，容易出现结果不一致、读到陈旧数据、线程无法退出、甚至隐蔽的并发 bug。