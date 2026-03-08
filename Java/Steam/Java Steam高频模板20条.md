*Thinking...*

> **Considering Java compatibility**
> 
> I’m thinking about whether to use `collect(toList())` instead of just `.toList()` for better compatibility with Java 8+. While LeetCode might support Java 17, sticking to older versions is wise. I believe using `Collectors.toList()` is the way to go. I'll ensure my markdown aligns with CommonMark and consider adding a brief explanation. It might be good to highlight common pitfalls for the different templates, focusing on key coding details like boxing streams. I’ll write up 20 examples with appropriate imports.

下面给你一份 **Java Stream 高频模板 20 条**，按 **Java 8+ 可直接用** 来写，尽量偏 **面试 / LeetCode / 日常开发** 场景。

## 常用导入

```java
import java.util.*;
import java.util.function.Function;
import java.util.stream.*;
import static java.util.stream.Collectors.*;
```

---

# Java Stream 高频模板 20 条

## 1. List 过滤

```java
List<String> ans = list.stream()
    .filter(s -> s != null && !s.isEmpty())
    .collect(toList());
```

**用途**：过滤空值、非法值、满足条件的数据。

---

## 2. 数组过滤

```java
int[] ans = Arrays.stream(nums)
    .filter(x -> x > 0)
    .toArray();
```

**用途**：从数组中筛选元素。

---

## 3. map 映射转换

```java
List<Integer> lengths = list.stream()
    .map(String::length)
    .collect(toList());
```

**用途**：对象转字段、字符串转长度、数字转平方等。

---

## 4. flatMap 打平二维结构

```java
List<Integer> ans = lists.stream()
    .flatMap(List::stream)
    .collect(toList());
```

**用途**：`List<List<T>>` 转 `List<T>`。

---

## 5. 去重

```java
List<Integer> ans = list.stream()
    .distinct()
    .collect(toList());
```

**用途**：去重保留第一次出现顺序。

---

## 6. 排序

### 自然升序

```java
List<Integer> ans = list.stream()
    .sorted()
    .collect(toList());
```

### 降序

```java
List<Integer> ans = list.stream()
    .sorted(Comparator.reverseOrder())
    .collect(toList());
```

### 按对象字段排序

```java
List<User> ans = users.stream()
    .sorted(Comparator.comparing(User::getAge))
    .collect(toList());
```

---

## 7. 去重 + 排序

```java
int[] ans = Arrays.stream(nums)
    .distinct()
    .sorted()
    .toArray();
```

**用途**：LeetCode 预处理高频。

---

## 8. limit / skip 截取

### 取前 10 个

```java
List<String> ans = list.stream()
    .limit(10)
    .collect(toList());
```

### 跳过前 10 个

```java
List<String> ans = list.stream()
    .skip(10)
    .collect(toList());
```

**用途**：分页、截断。

---

## 9. 求和

```java
int sum = Arrays.stream(nums).sum();
```

或者对象字段求和：

```java
int sum = users.stream()
    .mapToInt(User::getAge)
    .sum();
```

---

## 10. 最大值 / 最小值

### 数组

```java
int max = Arrays.stream(nums).max().orElse(0);
int min = Arrays.stream(nums).min().orElse(0);
```

### 对象字段

```java
Optional<User> oldest = users.stream()
    .max(Comparator.comparing(User::getAge));
```

---

## 11. 计数

```java
long cnt = list.stream()
    .filter(x -> x > 10)
    .count();
```

**用途**：统计满足条件的元素个数。

---

## 12. anyMatch / allMatch / noneMatch

```java
boolean hasZero = Arrays.stream(nums).anyMatch(x -> x == 0);
boolean allPositive = Arrays.stream(nums).allMatch(x -> x > 0);
boolean noneNegative = Arrays.stream(nums).noneMatch(x -> x < 0);
```

**用途**：存在性判断、全满足判断。

---

## 13. findFirst / findAny

```java
Optional<String> first = list.stream()
    .filter(s -> s.length() > 3)
    .findFirst();
```

**用途**：找第一个满足条件的元素。

取默认值：

```java
String ans = list.stream()
    .filter(s -> s.length() > 3)
    .findFirst()
    .orElse("default");
```

---

## 14. 转 List / Set

### 数组转 List

```java
List<Integer> list = Arrays.stream(nums)
    .boxed()
    .collect(toList());
```

### 数组转 Set

```java
Set<Integer> set = Arrays.stream(nums)
    .boxed()
    .collect(toSet());
```

**注意**：`IntStream` 转集合前通常要 `boxed()`。

---

## 15. 词频统计

```java
Map<String, Long> freq = words.stream()
    .collect(groupingBy(Function.identity(), counting()));
```

**用途**：单词频次、字符频次、元素出现次数。

---

## 16. 按字段分组

```java
Map<Integer, List<User>> map = users.stream()
    .collect(groupingBy(User::getAge));
```

**用途**：按年龄、类型、状态分类。

---

## 17. 分组后统计数量

```java
Map<Integer, Long> map = users.stream()
    .collect(groupingBy(User::getAge, counting()));
```

**用途**：每个分组有多少个元素。

---

## 18. toMap 构造 Map

### 键值一一对应

```java
Map<Integer, String> map = users.stream()
    .collect(toMap(User::getId, User::getName));
```

### 有重复 key 时指定合并规则

```java
Map<Integer, String> map = users.stream()
    .collect(toMap(
        User::getId,
        User::getName,
        (a, b) -> a
    ));
```

**注意**：不写合并规则，重复 key 会报错。

---

## 19. joining 字符串拼接

```java
String s = list.stream()
    .collect(joining(","));
```

带前后缀：

```java
String s = list.stream()
    .collect(joining(", ", "[", "]"));
```

**用途**：输出结果、拼接日志、格式化展示。

---

## 20. IntStream.range 生成下标 / 区间

### 生成 0 到 n-1

```java
List<Integer> idx = IntStream.range(0, n)
    .boxed()
    .collect(toList());
```

### 按下标访问数组

```java
List<String> ans = IntStream.range(0, arr.length)
    .mapToObj(i -> i + ":" + arr[i])
    .collect(toList());
```

**用途**：需要“索引流”的场景。

---

# 再送你 5 个特别常用的加分模板

虽然你要的是 20 条，但这 5 条也非常高频，建议一起记。

## A. summaryStatistics 一次拿全统计

```java
IntSummaryStatistics stat = Arrays.stream(nums).summaryStatistics();

long count = stat.getCount();
int sum = (int) stat.getSum();
int min = stat.getMin();
int max = stat.getMax();
double avg = stat.getAverage();
```

---

## B. partitioningBy 二分组

```java
Map<Boolean, List<Integer>> map = list.stream()
    .collect(partitioningBy(x -> x % 2 == 0));
```

**用途**：按“是否满足条件”分两组。

---

## C. reduce 归约

### 求和

```java
int sum = list.stream().reduce(0, Integer::sum);
```

### 求乘积

```java
int product = list.stream().reduce(1, (a, b) -> a * b);
```

---

## D. 分组后映射字段

```java
Map<Integer, List<String>> map = users.stream()
    .collect(groupingBy(
        User::getAge,
        mapping(User::getName, toList())
    ));
```

**用途**：按年龄分组后，只保留名字。

---

## E. 排序后取前 K 个

```java
List<Integer> topK = list.stream()
    .sorted(Comparator.reverseOrder())
    .limit(k)
    .collect(toList());
```

---

# 最值得背的 8 条

如果你只想背最核心的，优先这 8 条：

1. `filter`
2. `map`
3. `flatMap`
4. `distinct`
5. `sorted`
6. `collect(toList())`
7. `groupingBy(..., counting())`
8. `anyMatch / findFirst`

---

# 高频坑点

## 1. `toMap` 遇到重复 key 会报错

```java
.collect(toMap(User::getId, User::getName, (a, b) -> a))
```

---

## 2. `IntStream` 转 `List<Integer>` 要 `boxed()`

```java
Arrays.stream(nums).boxed().collect(toList());
```

---

## 3. 没有终止操作就不会真正执行

比如只有 `filter`、`map` 不会执行，必须配合：

- `collect`
- `count`
- `sum`
- `forEach`
- `findFirst`

---

## 4. Stream 不适合复杂流程控制

不适合硬写：

- 双指针
- 滑动窗口
- DP
- 回溯
- DFS / BFS

---

# 一页背诵版

```java
// 1 过滤
list.stream().filter(x -> 条件).collect(toList());

// 2 映射
list.stream().map(x -> 转换).collect(toList());

// 3 打平
lists.stream().flatMap(List::stream).collect(toList());

// 4 去重
list.stream().distinct().collect(toList());

// 5 排序
list.stream().sorted().collect(toList());

// 6 去重排序
Arrays.stream(nums).distinct().sorted().toArray();

// 7 求和
Arrays.stream(nums).sum();

// 8 最值
Arrays.stream(nums).max().orElse(0);

// 9 计数
list.stream().filter(x -> 条件).count();

// 10 判断
list.stream().anyMatch(x -> 条件);

// 11 找第一个
list.stream().filter(x -> 条件).findFirst().orElse(默认值);

// 12 转 List
Arrays.stream(nums).boxed().collect(toList());

// 13 转 Set
Arrays.stream(nums).boxed().collect(toSet());

// 14 词频
list.stream().collect(groupingBy(Function.identity(), counting()));

// 15 分组
list.stream().collect(groupingBy(x -> key));

// 16 toMap
list.stream().collect(toMap(k, v, (a, b) -> a));

// 17 拼接
list.stream().collect(joining(","));

// 18 分页
list.stream().skip(a).limit(b).collect(toList());

// 19 下标流
IntStream.range(0, n).boxed().collect(toList());

// 20 归约
list.stream().reduce(0, Integer::sum);
```

如果你愿意，我下一条可以继续给你：

1. **LeetCode 专用 Stream 模板 20 条**
2. **Java Stream 高频模板 `.mm` 极简思维导图版**
3. **Stream 常见面试题 + 标准答案版**