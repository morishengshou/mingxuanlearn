# Java 集合框架完全学习指南（java.util.*）

---

## 一、思维导图总览

```
java.util 集合框架
│
├── 【Collection 体系】（单列集合 — 只存值）
│   │
│   ├── List（有序、可重复、有索引）
│   │   ├── ArrayList
│   │   │     实现：动态数组
│   │   │     特点：随机访问 O(1)，增删尾部 O(1)，中间增删 O(n)
│   │   │     线程：不安全
│   │   │     推荐：绝大多数场景首选
│   │   │
│   │   ├── LinkedList
│   │   │     实现：双向链表
│   │   │     特点：增删 O(1)，随机访问 O(n)
│   │   │     特殊：同时实现 Deque 接口，可当栈/队列用
│   │   │     线程：不安全
│   │   │
│   │   └── Vector（已过时）
│   │         实现：动态数组
│   │         线程：安全（方法加 synchronized）
│   │         └── Stack（已过时）
│   │               继承 Vector，提供 push/pop/peek
│   │               推荐替代：ArrayDeque
│   │
│   ├── Set（无序、不重复、无索引）
│   │   ├── HashSet
│   │   │     实现：HashMap 的 Key 部分（哈希表）
│   │   │     特点：无序，允许一个 null，增删查 O(1)
│   │   │     原理：依赖 hashCode() + equals()
│   │   │
│   │   ├── LinkedHashSet
│   │   │     实现：LinkedHashMap 的 Key 部分
│   │   │     特点：维护插入顺序，性能略低于 HashSet
│   │   │
│   │   └── TreeSet
│   │         实现：TreeMap 的 Key 部分（红黑树）
│   │         特点：自动排序，增删查 O(log n)
│   │         排序：自然顺序 或 传入 Comparator
│   │         限制：不允许 null
│   │
│   └── Queue（队列，FIFO）
│       ├── PriorityQueue
│       │     实现：小顶堆（默认）
│       │     特点：按优先级出队，不保证 FIFO
│       │     排序：自然顺序 或 传入 Comparator
│       │     限制：不允许 null
│       │
│       └── Deque（双端队列接口）
│             ├── ArrayDeque
│             │     实现：循环数组
│             │     特点：两端 O(1)，推荐替代 Stack 和 LinkedList 当队列用
│             │     限制：不允许 null
│             │
│             └── LinkedList（同时实现 List + Deque）
│
├── 【Map 体系】（双列集合 — 存键值对，Key 不重复）
│   │
│   ├── HashMap
│   │     实现：数组 + 链表/红黑树（JDK8+）
│   │     特点：无序，Key/Value 均允许 null，增删查 O(1)
│   │     原理：依赖 hashCode() + equals()
│   │     线程：不安全
│   │     初始容量：16，负载因子：0.75
│   │     推荐：最通用的键值对容器
│   │
│   ├── LinkedHashMap
│   │     实现：HashMap + 双向链表
│   │     特点：维护插入顺序（或 LRU 访问顺序）
│   │     用途：实现 LRU 缓存
│   │
│   ├── TreeMap
│   │     实现：红黑树
│   │     特点：按 Key 自动排序，增删查 O(log n)
│   │     限制：Key 不允许 null
│   │
│   ├── Hashtable（已过时）
│   │     实现：哈希表
│   │     线程：安全（全方法 synchronized）
│   │     限制：Key/Value 均不允许 null
│   │     推荐替代：ConcurrentHashMap
│   │     └── Properties
│   │           继承 Hashtable，专用于配置文件
│   │           Key/Value 均为 String
│   │           用途：读写 .properties 配置文件
│   │
│   └── WeakHashMap
│         特点：Key 为弱引用，GC 时可自动回收 Key
│         用途：缓存场景，防止内存泄漏
│
├── 【并发集合】（java.util.concurrent）
│   ├── CopyOnWriteArrayList   ← 线程安全 List，写时复制
│   ├── ConcurrentHashMap      ← 线程安全 HashMap，分段锁/CAS
│   ├── ConcurrentLinkedQueue  ← 线程安全无界队列，CAS 实现
│   ├── BlockingQueue 接口
│   │   ├── ArrayBlockingQueue   ← 有界阻塞队列
│   │   ├── LinkedBlockingQueue  ← 可选有界阻塞队列
│   │   └── PriorityBlockingQueue ← 优先级阻塞队列
│   └── CopyOnWriteArraySet    ← 线程安全 Set，写时复制
│
└── 【工具类 & 接口】
    ├── Collections            ← 集合操作静态工具类
    │     常用方法：
    │     sort()          排序（需实现 Comparable）
    │     binarySearch()  二分查找
    │     reverse()       反转
    │     shuffle()       随机打乱
    │     frequency()     统计元素出现次数
    │     unmodifiableXxx() 返回只读视图
    │     synchronizedXxx() 返回线程安全视图
    │
    ├── Arrays                 ← 数组操作静态工具类
    │     常用方法：
    │     asList()        数组转 List（固定大小）
    │     sort()          排序
    │     binarySearch()  二分查找
    │     copyOf()        复制数组
    │     fill()          填充
    │     stream()        转换为 Stream
    │
    ├── Iterator               ← 迭代器接口
    │     hasNext() / next() / remove()
    │
    ├── ListIterator           ← List 专用迭代器（支持双向遍历）
    │     hasPrevious() / previous() / set() / add()
    │
    ├── Comparable             ← 自然排序接口（实现 compareTo）
    └── Comparator             ← 定制排序接口（实现 compare）
```

---

## 二、继承 / 实现关系图

```
Iterable<T>
  └── Collection<T>
        ├── List<T>
        │     ├── ArrayList<E>
        │     ├── LinkedList<E>  ──────────┐
        │     └── Vector<E>               │
        │           └── Stack<E>          │
        ├── Set<T>                         │
        │     ├── HashSet<E>              │
        │     │     └── LinkedHashSet<E>  │
        │     └── SortedSet<E>            │
        │           └── TreeSet<E>        │
        └── Queue<T>                      │
              ├── PriorityQueue<E>        │
              └── Deque<T>  ◄─────────────┘
                    ├── ArrayDeque<E>
                    └── LinkedList<E>（同上）

Map<K,V>（独立体系，不继承 Collection）
  ├── HashMap<K,V>
  │     └── LinkedHashMap<K,V>
  ├── SortedMap<K,V>
  │     └── TreeMap<K,V>
  ├── Hashtable<K,V>
  │     └── Properties
  └── WeakHashMap<K,V>
```

---

## 三、核心选型速查表

| 需求场景 | 推荐集合 | 原因 |
|----------|----------|------|
| 有序列表，随机访问多 | `ArrayList` | 数组结构，索引 O(1) |
| 有序列表，频繁头尾增删 | `ArrayDeque` | 循环数组，两端 O(1) |
| 有序列表，频繁中间增删 | `LinkedList` | 链表增删 O(1) |
| 去重集合，不关心顺序 | `HashSet` | 哈希表，O(1) |
| 去重集合，保持插入顺序 | `LinkedHashSet` | 哈希表+链表 |
| 去重集合，自动排序 | `TreeSet` | 红黑树，O(log n) |
| 键值对，最通用 | `HashMap` | 哈希表，O(1) |
| 键值对，保持插入顺序 | `LinkedHashMap` | 哈希表+链表 |
| 键值对，按 Key 排序 | `TreeMap` | 红黑树，O(log n) |
| 优先级队列 | `PriorityQueue` | 小顶堆 |
| 替代 Stack | `ArrayDeque` | 性能更好 |
| 读配置文件 | `Properties` | 专为配置设计 |
| 多线程键值对 | `ConcurrentHashMap` | 分段锁，高并发 |
| 多线程列表，读多写少 | `CopyOnWriteArrayList` | 写时复制 |

---

## 四、时间复杂度对比

| 集合 | 查 get | 增 add | 删 remove | 是否有序 | 线程安全 |
|------|--------|--------|-----------|----------|----------|
| ArrayList | O(1) | O(1)尾/O(n)中 | O(n) | 是 | 否 |
| LinkedList | O(n) | O(1) | O(1) | 是 | 否 |
| HashSet | O(1) | O(1) | O(1) | 否 | 否 |
| TreeSet | O(log n) | O(log n) | O(log n) | 是(排序) | 否 |
| HashMap | O(1) | O(1) | O(1) | 否 | 否 |
| TreeMap | O(log n) | O(log n) | O(log n) | 是(排序) | 否 |
| PriorityQueue | O(n) | O(log n) | O(log n) | 否 | 否 |

---

## 五、学习路线建议

### 第一阶段：基础三件套（必须掌握）

```
Week 1-2
  ├── ArrayList   ← List 的核心，增删改查、遍历方式
  ├── HashMap     ← Map 的核心，put/get/遍历、null 处理
  └── HashSet     ← Set 的核心，去重原理（hashCode+equals）

重点实践：
  □ 用 ArrayList 实现增删改查
  □ 用 HashMap 统计单词频率
  □ 理解 hashCode/equals 契约
```

### 第二阶段：横向扩展（熟练使用）

```
Week 3-4
  ├── LinkedList / ArrayDeque  ← 双端队列、栈的替代
  ├── LinkedHashMap            ← 实现 LRU 缓存
  ├── TreeMap / TreeSet        ← 排序场景
  └── PriorityQueue            ← 优先级调度场景

重点实践：
  □ 用 ArrayDeque 实现 BFS/DFS
  □ 用 LinkedHashMap(accessOrder=true) 实现 LRU
  □ 用 TreeMap 实现按分数排名
```

### 第三阶段：深入原理（理解本质）

```
Week 5-6
  ├── HashMap 源码   ← 扩容机制、哈希冲突、红黑树转换
  ├── ArrayList 源码 ← 扩容机制（1.5倍）
  ├── ConcurrentHashMap ← 分段锁 → CAS+synchronized
  └── Comparable vs Comparator ← 自定义排序

重点学习：
  □ HashMap 为什么初始容量是 16？负载因子 0.75 的意义？
  □ JDK8 链表转红黑树的阈值（8）和退化阈值（6）
  □ fail-fast 与 fail-safe 迭代器
```

### 第四阶段：并发与生产实践

```
Week 7-8
  ├── ConcurrentHashMap      ← 多线程键值对
  ├── CopyOnWriteArrayList   ← 读多写少场景
  ├── BlockingQueue          ← 生产者消费者模式
  └── Collections 工具类     ← unmodifiable / synchronized 包装

重点实践：
  □ 线程池 + BlockingQueue 实现生产者消费者
  □ ConcurrentHashMap vs Collections.synchronizedMap 性能对比
```

---

## 六、常见陷阱与注意事项

### 1. Arrays.asList() 的坑
```java
// 返回固定大小的 List，不支持 add/remove！
List<String> list = Arrays.asList("a", "b", "c");
list.add("d");  // 抛出 UnsupportedOperationException

// 正确做法：
List<String> list = new ArrayList<>(Arrays.asList("a", "b", "c"));
```

### 2. 遍历时删除元素
```java
// 错误：ConcurrentModificationException
for (String s : list) {
    if (s.equals("x")) list.remove(s);
}

// 正确：使用 Iterator
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if (it.next().equals("x")) it.remove();
}

// 或用 JDK8+：
list.removeIf(s -> s.equals("x"));
```

### 3. HashMap 与 null
```java
HashMap<String, String> map = new HashMap<>();
map.put(null, "value");    // Key 可以为 null
map.put("key", null);      // Value 可以为 null

// Hashtable / TreeMap 的 Key 不允许为 null！
```

### 4. equals/hashCode 契约
```java
// 自定义类放入 HashSet/HashMap 前，必须重写 equals 和 hashCode
// 规则：equals 返回 true，则 hashCode 必须相同
@Override
public boolean equals(Object o) { ... }

@Override
public int hashCode() { ... }
```

### 5. 初始容量优化
```java
// 已知元素数量时，指定初始容量，避免频繁扩容
// 公式：initialCapacity = expectedSize / 0.75 + 1
Map<String, String> map = new HashMap<>(256);
List<String> list = new ArrayList<>(100);
```

---

## 七、记忆口诀

```
┌─────────────────────────────────────────────┐
│  List 有序可重复：Array 数组 Link 链表          │
│  Set  无序不重复：Hash 哈希 Tree 排序           │
│  Queue 先进先出：Priority 堆，Deque 双端        │
│  Map  键值不重 Key：HashMap 最通用             │
│                                               │
│  线程安全老三样：Vector / Hashtable / Stack    │
│  三个已过时，用 concurrent 包                  │
│                                               │
│  工具类两兄弟：Collections 操集合，Arrays 操数组 │
│  排序两接口：Comparable 自身，Comparator 外传   │
└─────────────────────────────────────────────┘
```

---

*文件生成日期：2026-03-02*
*适用版本：JDK 8 及以上*
