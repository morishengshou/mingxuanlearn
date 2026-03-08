*Thinking...*

> **Designing LeetCode Tips**
> 
> I’m thinking about tips and patterns for LeetCode, focusing on pitfalls and practice suggestions. I might want to emphasize using Java 8+, especially since LeetCode often uses Java 17. I could show examples related to lists and mention features like collectors, Optional, and primitive streams. It’s important to clarify that a Stream doesn’t store data and how it differs from InputStream/OutputStream. I should also explain the relationship between streams and collections, along with external vs. internal iteration. Let’s structure this answer!**Structuring Stream API Overview**
> 
> I’m planning an outline related to the Stream API. First, I want an overview that clarifies it’s not a data structure, but rather a one-time, lazy evaluation tool. Then, I’ll discuss design principles, like separating “what” from “how” and highlighting the declarative style of programming. I’ll cover core concepts and common methods, providing examples. I’ll compare traditional loops with streams, detailing when to best use each approach before wrapping up my thoughts.**Compiling LeetCode Tips**
> 
> I’m putting together tips for LeetCode challenges. I want to focus on using a frequency map for grouping characters, counting them, and deduplicating. I'll suggest using arrays for speed in some cases and talk about approaches like matrix flattening with flatMap. 
> 
> For example, reversing words can leverage Collections with streams, but some tasks, like merging intervals or prefix sums, are better with conventional loops. I need to address considerations around performance and when streams might be clearer but slower, especially in core loops.**Identifying Common Pitfalls**
> 
> I’m outlining common pitfalls with streams, like forgetting terminal operations or not realizing that a stream is consumed once. It’s crucial not to modify the source or external state within streams and to watch out for nulls. I need to address the differences between boxed and primitive types as well as how Collectors.toMap handles duplicate keys. 
> 
> For LeetCode, parallel streams might not be the best choice. As for a learning roadmap, I think I should include tutorials with examples in Java, possibly avoiding `var` for beginners. Let's keep it clear and concise, aiming for about 1800-2500 characters in Chinese.**Crafting a Tutorial Example**
> 
> I’m creating an introductory example for streams in Java. I’ll show a snippet that calculates the sum of squares for even numbers. In my design philosophy section, I want to cover concepts like internal iteration, lazy evaluation, and functional composition while minimizing side effects and discussing parallel processing. 
> 
> I think I should clarify the difference between Streams and Collections, emphasizing that Collections store data while Streams are more about computation. I can provide a table to define common methods and present useful patterns, like converting arrays to lists or counting frequencies, and I should note that looping might be faster for certain tasks.**Providing String and Collection Operations**
> 
> I’m sharing examples of using streams for various operations in Java. For counting character frequencies, I can show how to collect data using grouping. Next, I'll demonstrate grouping anagrams, removing duplicates and sorting elements, and checking conditions in arrays. I also want to include examples of generating ranges, flattening two-dimensional lists, and concatenating results. 
> 
> It’s essential to mention when streams are more convenient than conventional approaches, but I should also highlight scenarios where streams are not recommended, like with double pointers, sliding windows, and dynamic programming that requires index transitions.**Highlighting Stream Details and Pitfalls**
> 
> I want to mention that `Collectors.toList()` typically returns a mutable list in older Java versions, while in Java 16 and above, `Stream.toList()` returns an unmodifiable list. It's important to clarify this, especially for LeetCode users who might be working with Java 17. I could provide examples to illustrate this difference.
> 
> I should also explain that `reduce()` is useful for calculations, but I’ll keep the example simple. Additionally, I’ll note that `peek()` is primarily for debugging and that `Optional` can provide safe handling of values. Lastly, I want to ensure users remember the necessary imports for using streams.**Illustrating Stream Operations**
> 
> I’m thinking about creating a visual analogy for stream processing: `Data Source -> Intermediate Operations (0 or more) -> Terminal Operation (1)`. It’s important to emphasize that operations like `filter` and `map` don't execute until the terminal operation, such as `collect`, is called. 
> 
> I can provide an example showing the difference between a regular loop and a stream, illustrating how streams are suitable for answering questions about data flow, transformation, and desired outcomes.  
> 
> I should also touch on design philosophy, including influences from functional programming and the concept of internal vs. external iteration, while ensuring it’s beginner-friendly.**Highlighting Stream Advantages**
> 
> I want to mention how using `.parallelStream()` can make parallelization easier, but I shouldn't overemphasize it. The design separates the API from the data source, allowing any data source to implement `stream()`, including arrays and generated streams. 
> 
> When considering Leetcode challenges, it's helpful to focus on where streams are more convenient than the typical loops. I could provide three case studies that highlight common operations ideal for streams like calculating the sum of squares of even numbers, grouping anagrams, and finding the top K frequent elements. For instance, the operation for removing duplicates, sorting, and converting to an array could be simplified with streams.**Explaining Group Statistics and Patterns**
> 
> For case 2, I want to illustrate how to create a frequency map using streams:
> 
> ```java
> Map<Integer, Long> freq = Arrays.stream(nums).boxed()
>     .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
> ```
> 
> Then, to find the top K elements, I could use:
> 
> ```java
> int[] ans = freq.entrySet().stream()
>     .sorted((a,b) -> Long.compare(b.getValue(), a.getValue()))
>     .limit(k)
>     .mapToInt(Map.Entry::getKey)
>     .toArray();
> ```
> But I need to caution that if `n` is large, using loops or buckets might be faster. 
> 
> For case 3, when it comes to grouping anagrams, a simple string processing example could be 
> 
> ```java
> Arrays.stream(s.trim().split("\\s+")).filter... 
> ```
> 
> I should also highlight that using `Function.identity()` in `groupingBy` helps counting frequencies. Additionally, presenting common patterns would be great for beginners:
> 
> - `Arrays.stream(nums).sum()`
> - `Arrays.stream(nums).max().orElse(-1)`
> - `Arrays.stream(nums).boxed().collect(Collectors.toSet())`
> - `IntStream.range(0, n).filter(i -> ...).forEach(...)`
> 
> Caution should be given about using `forEach` due to side effects, and I could touch on why streams may seem challenging, such as with lambdas and method references. Simple mental models for the core concepts would also be helpful for newcomers.**Crafting a Stream API Tutorial**
> 
> I want to explain `flatMap` with a simple words example:
> 
> ```java
> List<String> words = Arrays.asList("ab", "cd");
> List<String> chars = words.stream()
>     .map(str -> str.split("")) // This creates a Stream<String[]>
> ```
> 
> However, this example is a bit advanced. A clearer example would involve flattening a list of lists. It’s essential to clarify some misconceptions: streaming does not alter the original collection unless there are side effects. The `sorted()` method generates a new stream, and `toList()` after Java 16 returns an unmodifiable list. 
> 
> When using `Collectors.groupingBy` on primitive arrays, it requires boxing, which can add overhead. Note that primitive arrays don't have a `stream()` method; instead, you should use `Arrays.stream(nums)`.
> 
> I see the Stream API as a "data query language targeting pipelines," similar to SQL but in memory, where a `Collection` is like a warehouse, and a `Stream` is akin to a conveyor belt. 
> 
> For beginners, I recommend a practice path: start by learning lambda expressions, master the five key verbs — filter, map, sorted, collect, and reduce. Then, practice converting loops to streams and assess when to use streams.
> 
> To directly respond to the user’s request, I’ll develop a tutorial that includes not only the design philosophy of the Stream API but also handy tips for using streams effectively, especially in Leetcode challenges.**Creating a Java Stream API Beginner’s Guide**
> 
> I’m thinking about a title: "Java Stream API 新手教程". I want to cover "设计思想", "适用场景", and "Leetcode技巧", while crafting polished Chinese examples and including balanced caution. At the start, I might need to add necessary imports:
> 
> ```java
> import java.util.*;
> import java.util.function.Function;
> import java.util.stream.*;
> ```
> 
> I could mention that "The following examples are based on Java 8+, which also applies to LeetCode's Java version." 
> 
> So, the structure would be something like this:
> 
> # Java Stream API 新手教程
> 
> Intro / quick understanding.
> 
> ## 1. 先用一句话理解  
> `Stream = 对数据集合进行“筛选、转换、聚合”的流水线`  
> (Just clarifying it's not an InputStream.)
> 
> ## 2. 设计思想  
> ### 2.1 声明式 rather than imperative  
> With an example comparing loop vs stream.  
> ### 2.2 Internal iteration  
> ### 2.3 Pipeline  
> ### 2.4 Lazy evaluation  
> ### 2.5 Functional & side-effect-free  
> ### 2.6 One-shot, no storage  
> ### 2.7 Mention primitive streams and parallelization.
> 
> ## 3. 核心语法  
> Discuss source, intermediate, terminal with a table of methods. Maybe two tables for intermediate and terminal along with examples.
> 
> ## 4. 常见示例  
> Include a list processing example like `words` and `numbers`, showcasing filter-map-sorted-collect.
> 
> ## 5. 什么时候用 Stream 更方便  
> List bullets for when to use streams, then mention when to avoid them.
> 
> ## 6.  
> I'll continue developing from here!**Essential Leetcode Templates**
> 
> I want to outline the top eight templates worth mastering for Leetcode:  
> 1. Removing duplicates and sorting  
> 2. Finding sums and maxima/minima  
> 3. Frequency counting  
> 4. Grouping data  
> 5. Quickly converting to Set/Map  
> 6. String manipulation  
> 7. Flattening two-dimensional structures  
> 8. Conditional checks with anyMatch/allMatch  
> 
> For each, I'll include relevant code snippets and notes, possibly highlighting performance impacts. 
> 
> Next, I should mention which problems are less suited for using streams. I can make a list of those types. 
> 
> I also want to identify common pitfalls and provide learning advice, suggesting to start with loops and then convert to streams. 
> 
> For the conclusion, I might summarize: "One takeaway: Streams are suitable for preprocessing and postprocessing, but core algorithms often still rely on loops." I’d like to include a complete case example, like "Counting the squares of all even numbers" or "Processing words." 
> 
> For a full example, "Group Anagrams" would work well, and I can also consider a top K frequent words example, though I’ll need to maintain conciseness. Let's carefully craft the necessary code for these!**Group Anagrams Example**
> 
> For grouping anagrams, I have an elegant implementation:  
> ```java
> public List<List<String>> groupAnagrams(String[] strs) {
>     return new ArrayList<>(
>         Arrays.stream(strs)
>             .collect(Collectors.groupingBy(s -> {
>                 char[] arr = s.toCharArray();
>                 Arrays.sort(arr);
>                 return new String(arr);
>             }))
>             .values()
>     );
> }
> ```
> The core idea here isn't solely stream-specific, which is nice. 
> 
> Next, for finding the top K frequent elements:  
> ```java
> public int[] topKFrequent(int[] nums, int k) {
>     Map<Integer, Long> freq = Arrays.stream(nums)
>         .boxed()
>         .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
>       
>     return freq.entrySet().stream()
>         .sorted((a, b) -> Long.compare(b.getValue(), a.getValue()))
>         .limit(k)
>         .mapToInt(Map.Entry::getKey)
>         .toArray();
> }
> ```
> While it's concise, it may not be the most efficient method. 
> 
> I should also demonstrate a simpler example: "Contains Duplicate" using streams:  
> ```java
> public boolean containsDuplicate(int[] nums) {
>     return Arrays.stream(nums).distinct().count() < nums.length;
> }
> ```
> Though it's elegant, I should caution about potential performance issues. Typical implementation with a set is more direct. I need to mention "boxing" from `int[]` to `Set<Integer>` too. Using `Arrays.stream(nums).boxed().collect(Collectors.toSet())` converts primitives to wrappers, which is essential! For char mapping or handling integer arrays like a matrix, `flatMapToInt(Arrays::stream)` could also be useful to note.**Using Streams and Cautions**
> 
> I should mention that while `.parallelStream()` can be useful, it's not recommended for LeetCode or interviews. To help users remember key methods, I think creating a mnemonic could be fun:  
> - `filter` - filters  
> - `map` - maps  
> - `flatMap` - flattens  
> - `collect` - collects  
> - `reduce` - reduces  
> - `match` - matches  
> 
> Next, a comparison of external versus internal iteration can clarify things:  
> ```java
> int sum = 0;
> for (int x : nums) {
>     if (x % 2 == 0) sum += x * x;
> }
> int sum2 = nums.stream().filter(...).map(...).reduce(0, Integer::sum);
> ```
> I'm noting that I can't call a stream on `int[]`, so using `List<Integer> nums` is essential. It’s also good to clarify the difference between `reduce` and `sum` - I prefer specialized methods for primitives when available. For example:  
> ```java
> int sum = Arrays.stream(nums).filter(...).map(x -> x * x).sum();
> ```
> Using `IntStream` makes this easier, so I’ll show that too. I’ll ensure all examples compile, like:  
> ```java
> List<String> result = words.stream()
>     .filter(word -> word.length() >= 3)
>     .map(String::toUpperCase)
>     .sorted()
>     .collect(Collectors.toList());
> ```
> Lastly, I should mention that `.toList()` is only available in Java 16 and higher, so it's safer to use collectors with Java 8 users.**Explaining Java Stream Basics**
> 
> Since the user is likely a Java newbie, I want to focus on Java 8+ basics. I think using `Collectors.toList()` makes it more universal, while mentioning that `.toList()` is available in newer versions will be helpful.
> 
> Should I include imports? Maybe just once:
> ```java
> import java.util.*;
> import java.util.function.Function;
> import java.util.stream.*;
> ```
> That seems sufficient.
> 
> Next, I can introduce small examples, like:
> ```java
> Stream<String> s = Stream.of("a", "b", "c");
> IntStream range = IntStream.range(0, n);
> ```
> I should mention the flow of operations as "source -> intermediate -> terminal." For instance:
> ```java
> List<Integer> ans = nums.stream()      // source
>     .filter(x -> x > 0)                // intermediate
>     .map(x -> x * 2)                   // intermediate
>     .collect(Collectors.toList());     // terminal
> ```
> I might annotate that the "collect" method returns a mutable list but doesn't guarantee it.
> 
> In considering the "design philosophy," I want to include concepts like:
> - Abstraction over iteration
> - Higher-order functions
> - Non-interference and statelessness
> - Laziness and fusion
> 
> Although mentioning "operation fusion" might be too advanced, it might be good to address the user's request about design thoughts.**Clarifying Stream Evaluation and Design**
> 
> I want to highlight that multiple intermediate operations in a stream don’t necessarily mean multiple traversals; thanks to lazy evaluation, many can be fused into one. This is significant because, for example, applying both filter and map processes each element only once. 
> 
> I should also explain "short-circuiting," where methods like `findFirst`, `anyMatch`, and `limit` can terminate early—this is an important design feature. A simple example is:
> ```java
> boolean exists = nums.stream().filter(x -> x > 100).findAny().isPresent();
> ```
> But it could be even simpler with `anyMatch(x -> x > 100)`, which illustrates both design and practicality.
> 
> I’ll mention that being "parallel-friendly" is part of the design too. However, I should advise against using `parallelStream` just to show off during Leetcode or interviews.
> 
> Additionally, I think including a section that compares Stream to an in-memory SQL query would be helpful. For instance:
> ```java
> students.stream()
>     .filter(s -> s.getScore() >= 60)
>     .collect(groupingBy(Student::getClassName));
> ```
> This analogy simplifies understanding.
> 
> I’ll also bring in the concept of "Optional," especially for methods like `max()` or `min()`, with an example: `max().orElse(-1)` to explain that a stream could be empty.
> 
> Finally, I want to touch on "method reference" for newbies, noting that `String::toUpperCase` is equivalent to `s -> s.toUpperCase()`. I could include that in a helpful note.

# Java Stream API 新手教程

如果你是 Java 新手，可以先用一句话理解：

> **Stream API 就是：把“遍历数据并处理”的过程，写成一条清晰的“流水线”。**

它最适合做这几件事：

- 过滤数据
- 转换数据
- 统计/聚合
- 分组
- 排序
- 把结果收集成 `List`、`Set`、`Map`

但它**不是万能的**。在 LeetCode 里，Stream 有时非常优雅，有时反而更慢、更绕。

下面我按“**设计思想 -> 核心概念 -> 什么时候用 -> LeetCode 技巧 -> 常见坑**”来讲。

---

## 1. 先建立正确直觉：Stream 到底是什么？

很多初学者会误以为 Stream 和 `InputStream` / `OutputStream` 是一类东西。**不是。**

这里的 `Stream API` 指的是 Java 8 引入的**集合数据处理工具**。

你可以把它想成：

- `Collection`（如 `List`、`Set`）是**仓库**
- `Stream` 是对仓库中数据进行处理的**流水线**

### 一个最简单的例子

需求：从一组整数里，取出偶数，平方后求和。

### 普通写法

```java
List<Integer> nums = Arrays.asList(1, 2, 3, 4, 5, 6);
int sum = 0;

for (int x : nums) {
    if (x % 2 == 0) {
        sum += x * x;
    }
}
System.out.println(sum);
```

### Stream 写法

```java
List<Integer> nums = Arrays.asList(1, 2, 3, 4, 5, 6);

int sum = nums.stream()
        .filter(x -> x % 2 == 0)
        .mapToInt(x -> x * x)
        .sum();

System.out.println(sum);
```

这段代码读起来像一句话：

> 从 `nums` 开始，过滤出偶数，把每个数变成平方，然后求和。

这就是 Stream 的核心价值：  
**让代码更接近“我想做什么”，而不是“我怎么一步步遍历”。**

---

## 2. Stream API 的设计思想是什么？

理解 Stream，最重要的是理解它背后的设计思想。

---

## 2.1 声明式编程：描述“做什么”，而不是“怎么做”

传统 `for` 循环是“命令式”的：

- 定义变量
- 遍历元素
- 手动判断条件
- 手动保存结果

Stream 是“声明式”的：

- 过滤什么
- 转换成什么
- 最后要什么结果

### 对比

```java
List<String> words = Arrays.asList("apple", "hi", "banana", "cat");
```

### 普通写法

```java
List<String> result = new ArrayList<>();
for (String word : words) {
    if (word.length() >= 3) {
        result.add(word.toUpperCase());
    }
}
Collections.sort(result);
```

### Stream 写法

```java
List<String> result = words.stream()
        .filter(word -> word.length() >= 3)
        .map(String::toUpperCase)
        .sorted()
        .collect(Collectors.toList());
```

Stream 的风格更接近“查询语言”或“流水线语言”。

---

## 2.2 内部迭代：你不再自己控制循环

传统循环是**外部迭代**：

- 你自己写 `for`
- 你自己决定如何取下一个元素

Stream 是**内部迭代**：

- 你只提供规则
- 遍历细节由 Stream 框架处理

这也是为什么它更容易组合、并行化、复用处理逻辑。

---

## 2.3 流水线模型：Source -> Intermediate -> Terminal

Stream 的典型结构是：

```text
数据源 -> 中间操作(可多个) -> 终止操作(一个)
```

例如：

```java
List<Integer> result = Arrays.asList(1, 2, 3, 4, 5).stream() // 数据源
        .filter(x -> x % 2 == 1)                             // 中间操作
        .map(x -> x * 10)                                    // 中间操作
        .collect(Collectors.toList());                       // 终止操作
```

### 数据源

常见来源：

```java
List<Integer> list = Arrays.asList(1, 2, 3);
list.stream();

int[] nums = {1, 2, 3};
Arrays.stream(nums);

Stream.of("a", "b", "c");

IntStream.range(0, 5);        // 0,1,2,3,4
IntStream.rangeClosed(1, 5);  // 1,2,3,4,5
```

---

## 2.4 惰性求值：不终止，就不执行

这是 Stream 很重要的设计思想。

下面这段代码：

```java
Stream<Integer> s = Arrays.asList(1, 2, 3, 4).stream()
        .filter(x -> x % 2 == 0)
        .map(x -> x * 10);
```

**此时还没有真正处理数据。**

只有当你加上终止操作，例如：

```java
List<Integer> result = s.collect(Collectors.toList());
```

整个流水线才会真正执行。

### 这样设计有什么好处？

因为它可以：

- 避免不必要计算
- 支持短路
- 让多个操作组合成一趟处理

例如：

```java
boolean ok = Arrays.asList(1, 3, 5, 8, 9).stream()
        .anyMatch(x -> x % 2 == 0);
```

一旦找到 `8`，就可以停止，不需要遍历剩下元素。

---

## 2.5 函数式风格：尽量少副作用

Stream 鼓励你写：

- 无状态逻辑
- 不修改外部变量
- 不在流里乱改集合

### 不推荐

```java
List<Integer> result = new ArrayList<>();
Arrays.asList(1, 2, 3, 4).stream()
        .filter(x -> x % 2 == 0)
        .forEach(result::add);
```

虽然能跑，但这违背了 Stream 的风格。更推荐：

```java
List<Integer> result = Arrays.asList(1, 2, 3, 4).stream()
        .filter(x -> x % 2 == 0)
        .collect(Collectors.toList());
```

---

## 2.6 Stream 不存数据，只描述处理过程

这一点很关键：

- `List` 会存元素
- `Stream` 不负责存元素
- `Stream` 只负责“怎么处理这些元素”

所以 Stream 有两个典型特征：

### 1）只能消费一次

```java
Stream<Integer> stream = Arrays.asList(1, 2, 3).stream();
stream.count();
// stream.count(); // 再次使用会报错
```

### 2）通常不会修改原集合

它更像是“基于原数据生成新结果”。

---

## 2.7 为并行而设计，但不要滥用并行流

Stream API 的设计天然支持并行：

```java
list.parallelStream()
```

但对于新手和 LeetCode 来说，我建议：

> **先别碰 `parallelStream()`。**

原因：

- 不一定更快
- 有线程切换开销
- 有副作用时代码更危险
- 在线评测中几乎没必要

---

# 3. Stream 的核心操作，怎么记？

你可以先记住 6 个最常用动词：

- `filter`：过滤
- `map`：映射/转换
- `flatMap`：打平
- `sorted`：排序
- `collect`：收集结果
- `reduce`：归约成一个值

---

## 3.1 中间操作

| 方法 | 作用 |
| --- | --- |
| `filter` | 按条件保留元素 |
| `map` | 把每个元素转换成另一个元素 |
| `flatMap` | 一对多后展开 |
| `distinct` | 去重 |
| `sorted` | 排序 |
| `limit` | 取前几个 |
| `skip` | 跳过前几个 |
| `peek` | 调试查看元素，不建议业务依赖 |

### 示例

```java
List<Integer> result = Arrays.asList(5, 2, 2, 8, 1, 6).stream()
        .filter(x -> x > 2)
        .distinct()
        .sorted()
        .limit(3)
        .collect(Collectors.toList());
```

---

## 3.2 终止操作

| 方法 | 作用 |
| --- | --- |
| `collect` | 收集为 `List`、`Set`、`Map` 等 |
| `count` | 计数 |
| `forEach` | 遍历执行 |
| `reduce` | 合并为一个值 |
| `sum` / `max` / `min` | 数值聚合 |
| `findFirst` | 找第一个 |
| `anyMatch` | 任意匹配 |
| `allMatch` | 全部匹配 |
| `noneMatch` | 都不匹配 |

### 示例

```java
int max = Arrays.stream(new int[]{3, 7, 2, 9})
        .max()
        .orElse(-1);
```

这里的 `orElse(-1)` 是因为 `max()` 返回的是 `OptionalInt`，防止空流报错。

---

# 4. 初学者最容易混淆的几个点

---

## 4.1 `map` 和 `flatMap` 的区别

### `map`
一个元素变成一个元素。

```java
List<String> result = Arrays.asList("a", "bb", "ccc").stream()
        .map(String::toUpperCase)
        .collect(Collectors.toList());
```

---

### `flatMap`
一个元素变成多个元素，然后把这些结果打平。

```java
List<List<Integer>> lists = Arrays.asList(
        Arrays.asList(1, 2),
        Arrays.asList(3, 4),
        Arrays.asList(5)
);

List<Integer> result = lists.stream()
        .flatMap(List::stream)
        .collect(Collectors.toList());
```

结果是：

```java
[1, 2, 3, 4, 5]
```

---

## 4.2 `map`、`mapToInt`、`boxed()` 的区别

这在 LeetCode 里很常见。

### 普通对象流

```java
Stream<Integer>
```

### 基本类型流

```java
IntStream
LongStream
DoubleStream
```

### 为什么有基本类型流？

为了避免频繁装箱/拆箱，提高性能。

例如：

```java
int sum = Arrays.stream(new int[]{1, 2, 3, 4})
        .filter(x -> x % 2 == 0)
        .map(x -> x * x)
        .sum();
```

这里是 `IntStream`，很自然。

如果你要把 `int` 变成 `Integer` 对象：

```java
Set<Integer> set = Arrays.stream(new int[]{1, 2, 3})
        .boxed()
        .collect(Collectors.toSet());
```

`boxed()` 就是把基本类型装箱成包装类。

---

# 5. 什么时候使用 Stream API 更方便？

下面这些场景，Stream 往往比常规写法更舒服。

---

## 5.1 数据过滤 + 转换 + 收集

这是 Stream 最擅长的事情。

```java
List<String> result = words.stream()
        .filter(s -> s.length() > 3)
        .map(String::toLowerCase)
        .collect(Collectors.toList());
```

---

## 5.2 统计、求和、求最大最小值

```java
int sum = Arrays.stream(nums).sum();
int max = Arrays.stream(nums).max().orElse(-1);
long count = Arrays.stream(nums).filter(x -> x > 0).count();
```

---

## 5.3 去重、排序、截取

```java
int[] result = Arrays.stream(nums)
        .distinct()
        .sorted()
        .limit(5)
        .toArray();
```

---

## 5.4 分组、频次统计

这类操作用 `Collectors` 非常方便。

```java
Map<Integer, Long> freq = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.groupingBy(
                Function.identity(),
                Collectors.counting()
        ));
```

---

## 5.5 集合间转换

```java
List<Integer> list = Arrays.stream(nums).boxed().collect(Collectors.toList());
Set<Integer> set = Arrays.stream(nums).boxed().collect(Collectors.toSet());
```

---

## 5.6 字符串批量处理

```java
String result = Arrays.stream("  hello   java stream  ".trim().split("\\s+"))
        .map(String::toUpperCase)
        .collect(Collectors.joining("-"));
```

结果：

```java
HELLO-JAVA-STREAM
```

---

# 6. 什么时候不要硬用 Stream？

这一节特别重要，尤其是 LeetCode。

下面这些场景，通常**普通循环更好**。

---

## 6.1 强依赖下标的题

比如：

- 双指针
- 滑动窗口
- 前缀和
- 动态规划
- 单调栈
- 原地修改数组

这些题很多逻辑跟索引、边界、状态转移强相关，`for` 循环会更清晰。

---

## 6.2 回溯、DFS、BFS、图搜索

例如：

- 全排列
- 子集
- 岛屿数量
- 二叉树遍历
- 图最短路

这些题重点在“状态控制”和“递归/队列逻辑”，Stream 帮助不大。

---

## 6.3 性能很敏感的热路径

例如：

- 大量装箱/拆箱
- 高频 map/grouping/sorting
- 需要极致性能的循环

Stream 可能会更慢，因为有：

- lambda 开销
- 对象创建开销
- 装箱/拆箱开销
- collector 开销

---

## 6.4 逻辑本身很复杂，需要中途 `break` / `continue`

虽然 Stream 有 `anyMatch`、`findFirst` 这类短路操作，但复杂控制流通常还是传统循环更自然。

---

# 7. LeetCode 里最实用的 Stream 技巧

这一部分最贴近刷题。

---

## 技巧 1：去重 + 排序 + 转数组

这个特别适合 Stream。

```java
int[] result = Arrays.stream(nums)
        .distinct()
        .sorted()
        .toArray();
```

### 常见用途

- 去重后排序
- 生成答案数组
- 简化预处理

---

## 技巧 2：快速求和 / 最大值 / 最小值

```java
int sum = Arrays.stream(nums).sum();
int max = Arrays.stream(nums).max().orElse(-1);
int min = Arrays.stream(nums).min().orElse(-1);
```

### 适合题型

- 数组统计题
- 预处理
- 简单一维数组题

---

## 技巧 3：频次统计

```java
Map<Integer, Long> freq = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.groupingBy(
                Function.identity(),
                Collectors.counting()
        ));
```

### 理解一下

- `boxed()`：`int` 变 `Integer`
- `Function.identity()`：元素本身就是 key
- `counting()`：统计数量

### 相当于

```java
Map<Integer, Long> map = new HashMap<>();
for (int x : nums) {
    map.put(x, map.getOrDefault(x, 0L) + 1);
}
```

### 哪个更好？

- **代码短**：Stream
- **性能高**：普通 `HashMap` 循环通常更好

所以在 LeetCode 中，**这个技巧适合中小规模数据、追求表达清晰时使用**。

---

## 技巧 4：字母异位词分组

这是 Stream 很经典的例子。

```java
public List<List<String>> groupAnagrams(String[] strs) {
    return new ArrayList<>(
            Arrays.stream(strs)
                    .collect(Collectors.groupingBy(s -> {
                        char[] arr = s.toCharArray();
                        Arrays.sort(arr);
                        return new String(arr);
                    }))
                    .values()
    );
}
```

### 为什么这里适合 Stream？

因为题目的本质就是：

- 把每个字符串映射成“标准形态”
- 按标准形态分组

这非常符合 `groupingBy` 的思想。

---

## 技巧 5：Top K Frequent 的简洁写法

```java
public int[] topKFrequent(int[] nums, int k) {
    Map<Integer, Long> freq = Arrays.stream(nums)
            .boxed()
            .collect(Collectors.groupingBy(
                    Function.identity(),
                    Collectors.counting()
            ));

    return freq.entrySet().stream()
            .sorted((a, b) -> Long.compare(b.getValue(), a.getValue()))
            .limit(k)
            .mapToInt(Map.Entry::getKey)
            .toArray();
}
```

### 优点

- 很短
- 思路清晰：统计 -> 排序 -> 取前 k

### 缺点

- 不一定是最优复杂度
- 面试官如果问优化，仍然要会桶排序 / 堆

所以你可以把它当作：

> **“快速写出可读解法”的工具，而不是所有题的最优解。**

---

## 技巧 6：二维结构打平

### `List<List<Integer>>`

```java
List<Integer> flat = lists.stream()
        .flatMap(List::stream)
        .collect(Collectors.toList());
```

### `int[][]`

```java
int sum = Arrays.stream(matrix)
        .flatMapToInt(Arrays::stream)
        .sum();
```

这在矩阵预处理、统计元素总和时很方便。

---

## 技巧 7：判断是否满足某种条件

### 是否存在

```java
boolean exists = Arrays.stream(nums).anyMatch(x -> x > 100);
```

### 是否全部满足

```java
boolean allPositive = Arrays.stream(nums).allMatch(x -> x > 0);
```

### 是否都不满足

```java
boolean noneNegative = Arrays.stream(nums).noneMatch(x -> x < 0);
```

这比手写布尔变量 + 循环更直接。

---

## 技巧 8：字符串处理特别方便

例如反转单词、清洗空格、拼接结果：

```java
String result = Arrays.stream(s.trim().split("\\s+"))
        .filter(str -> !str.isEmpty())
        .collect(Collectors.joining(" "));
```

或者：

```java
String result = Arrays.stream(s.trim().split("\\s+"))
        .map(String::toUpperCase)
        .collect(Collectors.joining(","));
```

---

## 技巧 9：快速转成 `Set`

LeetCode 经常用来做查重、判存在。

```java
Set<Integer> set = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.toSet());
```

例如求交集时：

```java
public int[] intersection(int[] nums1, int[] nums2) {
    Set<Integer> set1 = Arrays.stream(nums1).boxed().collect(Collectors.toSet());

    return Arrays.stream(nums2)
            .filter(set1::contains)
            .distinct()
            .toArray();
}
```

---

## 技巧 10：生成范围数据

```java
int[] arr = IntStream.rangeClosed(1, n).toArray();
```

或者：

```java
List<Integer> list = IntStream.range(0, n)
        .boxed()
        .collect(Collectors.toList());
```

这在构造测试数据、初始化数组索引时很方便。

---

# 8. LeetCode 中的一个很重要结论

如果你只记一句关于刷题的经验，请记这句：

> **Stream 很适合做“前处理”和“后处理”，但核心算法过程通常还是普通循环更强。**

### 适合 Stream 的地方

- 统计词频
- 去重排序
- 分组
- 结果转换
- 字符串清洗
- 一维数组简单聚合

### 不适合 Stream 的地方

- 滑动窗口
- 双指针
- 原地数组操作
- 动态规划
- 回溯
- 图搜索
- 树递归

---

# 9. 初学者常见坑

---

## 9.1 忘了终止操作

```java
list.stream().filter(x -> x > 0).map(x -> x * 2);
```

这段代码**不会真正执行**，因为没有终止操作。

---

## 9.2 一个 Stream 不能用两次

```java
Stream<Integer> s = list.stream();
s.count();
// s.collect(Collectors.toList()); // 错
```

---

## 9.3 `toMap()` 遇到重复 key 会报错

```java
Map<Integer, Integer> map = list.stream()
        .collect(Collectors.toMap(
                x -> x,
                x -> 1
        ));
```

如果 key 重复，会抛异常。需要提供合并规则：

```java
Map<Integer, Integer> map = list.stream()
        .collect(Collectors.toMap(
                x -> x,
                x -> 1,
                Integer::sum
        ));
```

---

## 9.4 `boxed()` 忘了写

`int[]` 想转 `Set<Integer>` 时，必须装箱：

```java
Set<Integer> set = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.toSet());
```

---

## 9.5 过度使用 `forEach`

`forEach` 不是不能用，但它常常会把 Stream 写回“命令式风格”。

### 不推荐

```java
List<Integer> ans = new ArrayList<>();
Arrays.stream(nums)
        .filter(x -> x > 0)
        .forEach(ans::add);
```

### 更推荐

```java
List<Integer> ans = Arrays.stream(nums)
        .filter(x -> x > 0)
        .boxed()
        .collect(Collectors.toList());
```

---

## 9.6 `peek()` 只适合调试

```java
Arrays.stream(nums)
        .peek(System.out::println)
        .sum();
```

`peek()` 可以调试，但不要依赖它做核心业务逻辑。

---

## 9.7 `.toList()` 和 `Collectors.toList()` 的差异

在新版本 Java 里：

```java
List<Integer> list = Arrays.stream(nums).boxed().toList();
```

这个 `list` 通常是**不可修改**的。

而：

```java
List<Integer> list = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.toList());
```

通常更接近你熟悉的可变列表，但规范并不严格保证具体实现。

如果你**明确需要可变 `ArrayList`**，最稳妥：

```java
List<Integer> list = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.toCollection(ArrayList::new));
```

---

# 10. 新手学习 Stream 的正确顺序

我建议你按这个顺序学：

### 第一步：先掌握这 4 个
- `filter`
- `map`
- `collect`
- `sorted`

### 第二步：再学这 4 个
- `distinct`
- `flatMap`
- `groupingBy`
- `counting`

### 第三步：最后理解这些
- `reduce`
- `Optional`
- `mapToInt` / `boxed`
- `toMap`
- `parallelStream`

---

# 11. 给你一个“刷题够用”的速查模板

先加导包：

```java
import java.util.*;
import java.util.function.Function;
import java.util.stream.*;
```

### 求和
```java
int sum = Arrays.stream(nums).sum();
```

### 最大值
```java
int max = Arrays.stream(nums).max().orElse(-1);
```

### 去重排序
```java
int[] arr = Arrays.stream(nums).distinct().sorted().toArray();
```

### 转 `Set`
```java
Set<Integer> set = Arrays.stream(nums).boxed().collect(Collectors.toSet());
```

### 统计频次
```java
Map<Integer, Long> freq = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
```

### 分组
```java
Map<Integer, List<Integer>> groups = Arrays.stream(nums)
        .boxed()
        .collect(Collectors.groupingBy(x -> x % 3));
```

### 判断存在
```java
boolean ok = Arrays.stream(nums).anyMatch(x -> x > 0);
```

### 拼接字符串
```java
String s = list.stream().map(String::valueOf).collect(Collectors.joining(","));
```

### 展平二维数组
```java
int sum = Arrays.stream(matrix).flatMapToInt(Arrays::stream).sum();
```

---

# 12. 最后帮你总结成一句“实战理解”

你可以这样理解 Stream API：

> **它不是用来替代所有 `for` 循环的，而是用来把“数据处理流水线”写得更清楚。**

所以实战中最好的策略是：

- **能明显简化表达时，用 Stream**
- **涉及复杂状态控制时，用传统循环**
- **LeetCode 里把 Stream 当辅助工具，而不是主战武器**

---

如果你愿意，我下一条可以继续给你写一份：

1. **“Java Stream API 从入门到 LeetCode 的 20 个练习题”**  
或  
2. **“把常见 for 循环一步步改写成 Stream 的对照教程”**

你选一个，我直接继续写。

