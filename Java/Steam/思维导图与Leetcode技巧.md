*Thinking...*

> **Considering mind map creation**
> 
> I'm planning to use Chinese labels, aiming for something simple and valid. I need one code block for XML and maybe a second one for LeetCode tips in another mind map format. Since the user wants a summary, I think a bullet-point summary could work, but it might be more useful to also provide a compact mind map as a text outline. 
> 
> I’ll create both: a Java Stream API mind map and a LeetCode-specific summary, plus optionally extra content. I want to guide the user on how to use these—like copying to a file and opening with FreeMind or XMind, which I think supports imports.**Organizing Java Stream API mind map**
> 
> I'm working on a mind map for the Java Stream API, breaking it down into several key areas. First, I have design ideas like declarative writing and internal iteration. Then, I'll outline core structures, starting with data sources like List or Set, followed by intermediate operations like filter and map.
> 
> Next, I want to include application scenarios and those where streams aren't suitable. I'll also add common LeetCode strategies, pointing out pitfalls, like forgetting terminal operations or misusing `forEach`. 
> 
> For code examples, I need to apply valid XML escapes to avoid special characters. Simplicity is key!**Structuring the mind map**
> 
> I need to consider assigning `POSITION="left"` or `"right"` for the first-level children in my mind map, alternating those positions. Unique IDs might not be essential, but including them can be safer, so I'll probably add them anyway. 
> 
> I’ll also think about adding creation and modification dates, but they may not be necessary for this. 
> 
> For the LeetCode-specific Stream tricks, I'll summarize them by categorizing pre-processing and post-processing, focusing on common scenarios. A concise mind map summary could work well here, emphasizing that streams are great for handling tasks before and after, but not for core loops. Bullet points will help as well!**Creating a compact tip map**
> 
> I think I should create a compact "技巧图（文本版）" focusing on key Java Stream techniques. This might include steps like de-duplication and sorting, aggregation counts, Set/Map building, grouping counts, flattening, conditional checks, and string preprocessing. 
> 
> I'll provide examples for clarity, noting that `toList()` returns an immutable list, so `collect(Collectors.toList())` might be needed for mutable collections. 
> 
> Since the user asked for a summary of LeetCode-specific Stream tricks, I could offer two `.mm` files: one for the Java Stream API and a bonus for LeetCode tricks. I’ll structure my response with a brief intro and then include both files along with a concise summary to ensure everything is clear and helpful!**Validating XML for mind maps**
> 
> I should probably mention that XMind allows importing `.mm` files via FreeMind. I can say something like, "若导入 XMind，选导入 FreeMind" to clarify that process. It’s crucial to ensure the XML is valid.
> 
> I want to avoid characters like `>` in code snippets, but I think using the Chinese arrow `→` in text is acceptable. If I include descriptions, I'll stick with clear Chinese terms instead of raw code, which will be helpful. 
> 
> I need to ensure elements like `List::stream` and `Collectors.toMap(...)` use safe characters. Descriptive attributes will make everything clearer!**Drafting mind maps**
> 
> I need to alternate the positions of top-level nodes to create a visually appealing layout in both mind maps. I might also offer a more aesthetically organized XMind file if the user wants that. For the first `.mm` file, I’ll start with a root node for the Java Stream API featuring design thoughts and key concepts. 
> 
> Next, I’ll structure the second file titled "LeetCode 专用版 Stream 技巧图," including sections for positioning, high-frequency techniques, common templates, pitfalls, inappropriate scenarios, and memory aids. Keeping it concise will be important, focusing on clarity and utility for the user!**Building the template structure**
> 
> I should provide actual code snippets outside of the XML for the templates since including them will help create a useful summary. A compact table showcasing "场景 | Stream模板" in Markdown could be a good format. 
> 
> I want to keep the number of code fences reasonable and ensure the response doesn't get excessively long, especially given there are two `.mm` files plus a summary. I'll try to build valid XML carefully and might include the XML prologue: `<?xml version="1.0" encoding="UTF-8"?>`.
> 
> I don't need to include comments for simplicity, and I’ll draft the first mind map with around six children. Although IDs aren't required, I'll make sure anything included is unique if I decide to add them.**Structuring the mind map**
> 
> I'm considering if I should include `ID="root"` in the mind map. While nested IDs might not be necessary, it's tempting to simplify the format. From what I remember, FreeMind accepts the format `<node TEXT="... ID="...">`, with IDs being optional. It might even allow for maps without the CREATED/MODIFIED attributes, but I could add simple numeric timestamps for compatibility.
> 
> For the layout, I’ll ensure the first-level six nodes alternate positions, and I'll mention I'm providing two `.mm` files — one original and one for LeetCode — with a summary as requested. Let's craft this final version elegantly!

可以。下面我直接给你 **2 份可保存为 `.mm` 的 FreeMind/Freeplane 格式文件内容**：

1. **原来的 Java Stream API 思维导图 `.mm` 版**
2. **LeetCode 专用版 Stream 技巧图 `.mm` 版**

你只要把代码分别保存成：

- `java-stream-api.mm`
- `leetcode-stream-tricks.mm`

然后用 **FreeMind / Freeplane** 打开即可。  
如果你用 **XMind**，一般也可以通过 **导入 FreeMind 文件** 的方式打开。

---

## 1）Java Stream API 思维导图（`.mm` 版）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  <node TEXT="Java Stream API 思维导图" ID="ID_ROOT">
    <node TEXT="1. 设计思想" POSITION="left" ID="ID_1">
      <node TEXT="声明式：写做什么，不强调怎么一步步遍历" ID="ID_1_1"/>
      <node TEXT="内部迭代：循环细节交给框架处理" ID="ID_1_2"/>
      <node TEXT="惰性求值：没有终止操作，通常不会真正执行" ID="ID_1_3"/>
      <node TEXT="少副作用：尽量不要在流中修改外部变量" ID="ID_1_4"/>
      <node TEXT="一次性消费：同一个 Stream 不能重复使用" ID="ID_1_5"/>
    </node>

    <node TEXT="2. 核心结构" POSITION="right" ID="ID_2">
      <node TEXT="数据源：List、Set、数组、IntStream.range" ID="ID_2_1"/>
      <node TEXT="中间操作：filter、map、flatMap、distinct、sorted、limit" ID="ID_2_2"/>
      <node TEXT="终止操作：collect、count、sum、max、findFirst、anyMatch" ID="ID_2_3"/>
      <node TEXT="基本类型流：IntStream、LongStream、DoubleStream" ID="ID_2_4"/>
      <node TEXT="主线记忆：数据源 → 中间操作 → 终止操作" ID="ID_2_5"/>
    </node>

    <node TEXT="3. 什么时候用最方便" POSITION="left" ID="ID_3">
      <node TEXT="过滤 + 转换 + 收集" ID="ID_3_1"/>
      <node TEXT="统计：求和、计数、最大值、最小值" ID="ID_3_2"/>
      <node TEXT="去重 + 排序 + 截取" ID="ID_3_3"/>
      <node TEXT="分组、聚合、词频统计" ID="ID_3_4"/>
      <node TEXT="字符串清洗、拼接、批量处理" ID="ID_3_5"/>
    </node>

    <node TEXT="4. 哪些场景不要硬用" POSITION="right" ID="ID_4">
      <node TEXT="强依赖下标、边界控制" ID="ID_4_1"/>
      <node TEXT="双指针、滑动窗口" ID="ID_4_2"/>
      <node TEXT="动态规划、回溯、DFS、BFS、图搜索" ID="ID_4_3"/>
      <node TEXT="原地修改数组、频繁 break / continue" ID="ID_4_4"/>
      <node TEXT="极致性能要求场景，普通 for 往往更直接" ID="ID_4_5"/>
    </node>

    <node TEXT="5. LeetCode 常用技巧" POSITION="left" ID="ID_5">
      <node TEXT="去重排序：distinct + sorted" ID="ID_5_1"/>
      <node TEXT="快速统计：sum、max、min、count" ID="ID_5_2"/>
      <node TEXT="转 Set / List / Map：collect" ID="ID_5_3"/>
      <node TEXT="词频统计：groupingBy + counting" ID="ID_5_4"/>
      <node TEXT="打平嵌套结构：flatMap" ID="ID_5_5"/>
      <node TEXT="条件判断：anyMatch、allMatch、noneMatch" ID="ID_5_6"/>
    </node>

    <node TEXT="6. 常见坑 + 最后结论" POSITION="right" ID="ID_6">
      <node TEXT="忘记终止操作：流不会真正执行" ID="ID_6_1"/>
      <node TEXT="toMap 遇到重复 key 会报错，要写合并规则" ID="ID_6_2"/>
      <node TEXT="基本类型流转集合时常常需要 boxed" ID="ID_6_3"/>
      <node TEXT="滥用 forEach，容易又写回命令式代码" ID="ID_6_4"/>
      <node TEXT="toList 返回结果可能不可变" ID="ID_6_5"/>
      <node TEXT="最终原则：Stream 擅长数据加工，不是替代所有循环" ID="ID_6_6"/>
    </node>
  </node>
</map>
```

---

## 2）LeetCode 专用版 Stream 技巧图（`.mm` 版）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  <node TEXT="LeetCode 专用版 Stream 技巧图" ID="LC_ROOT">
    <node TEXT="1. 核心定位" POSITION="left" ID="LC_1">
      <node TEXT="最适合：前处理、后处理" ID="LC_1_1"/>
      <node TEXT="不适合：核心状态转移和复杂控制流程" ID="LC_1_2"/>
      <node TEXT="一句话：前后处理用 Stream，核心算法多用 for" ID="LC_1_3"/>
    </node>

    <node TEXT="2. 高频技巧" POSITION="right" ID="LC_2">
      <node TEXT="去重排序：Arrays.stream(nums).distinct().sorted().toArray()" ID="LC_2_1"/>
      <node TEXT="聚合统计：sum、average、max、min、count" ID="LC_2_2"/>
      <node TEXT="转 Set：Arrays.stream(nums).boxed().collect(toSet)" ID="LC_2_3"/>
      <node TEXT="词频统计：groupingBy + counting" ID="LC_2_4"/>
      <node TEXT="条件判断：anyMatch、allMatch、noneMatch" ID="LC_2_5"/>
      <node TEXT="打平：flatMap 处理二维或嵌套集合" ID="LC_2_6"/>
      <node TEXT="索引流：IntStream.range(0, n)" ID="LC_2_7"/>
    </node>

    <node TEXT="3. 常用题型" POSITION="left" ID="LC_3">
      <node TEXT="数组预处理：去重、排序、过滤非法值" ID="LC_3_1"/>
      <node TEXT="集合清洗：null 过滤、字段提取、去重收集" ID="LC_3_2"/>
      <node TEXT="字符串统计：字符频次、单词分组" ID="LC_3_3"/>
      <node TEXT="结果整理：把答案转成 List、Set、Map" ID="LC_3_4"/>
    </node>

    <node TEXT="4. 常用模板" POSITION="right" ID="LC_4">
      <node TEXT="数组去重排序模板" ID="LC_4_1">
        <node TEXT="Arrays.stream(nums).distinct().sorted().toArray()" ID="LC_4_1_1"/>
      </node>
      <node TEXT="数组求和模板" ID="LC_4_2">
        <node TEXT="Arrays.stream(nums).sum()" ID="LC_4_2_1"/>
      </node>
      <node TEXT="转 Set 模板" ID="LC_4_3">
        <node TEXT="Arrays.stream(nums).boxed().collect(Collectors.toSet())" ID="LC_4_3_1"/>
      </node>
      <node TEXT="词频模板" ID="LC_4_4">
        <node TEXT="words.stream().collect(Collectors.groupingBy(x -> x, Collectors.counting()))" ID="LC_4_4_1"/>
      </node>
      <node TEXT="打平模板" ID="LC_4_5">
        <node TEXT="list.stream().flatMap(List::stream)" ID="LC_4_5_1"/>
      </node>
    </node>

    <node TEXT="5. 避坑" POSITION="left" ID="LC_5">
      <node TEXT="toMap 重复 key 会报错" ID="LC_5_1"/>
      <node TEXT="基本类型流收集到集合前要 boxed" ID="LC_5_2"/>
      <node TEXT="toList 结果可能不可变" ID="LC_5_3"/>
      <node TEXT="forEach 里不要塞复杂逻辑" ID="LC_5_4"/>
      <node TEXT="不要为了用 Stream 而用 Stream" ID="LC_5_5"/>
    </node>

    <node TEXT="6. 不推荐场景" POSITION="right" ID="LC_6">
      <node TEXT="双指针、滑动窗口" ID="LC_6_1"/>
      <node TEXT="动态规划" ID="LC_6_2"/>
      <node TEXT="回溯、DFS、BFS" ID="LC_6_3"/>
      <node TEXT="原地交换、复杂下标控制" ID="LC_6_4"/>
      <node TEXT="需要频繁提前退出的复杂流程" ID="LC_6_5"/>
    </node>

    <node TEXT="7. 记忆口诀" POSITION="left" ID="LC_7">
      <node TEXT="去重、排序、统计、分组、打平、判断" ID="LC_7_1"/>
      <node TEXT="前处理、后处理很香；核心循环还是 for 更强" ID="LC_7_2"/>
    </node>
  </node>
</map>
```

---

# LeetCode 专用版 Stream 技巧图总结

## 一句话总结

**Stream 在 LeetCode 里最适合做“前处理”和“后处理”，不适合承担核心算法流程。**

---

## 你可以重点记这 7 类

### 1. 去重 + 排序
最常用的预处理手段。

```java
int[] arr = Arrays.stream(nums).distinct().sorted().toArray();
```

适用：

- 去重后再二分
- 去重后再遍历
- 压缩值域前的预整理

---

### 2. 聚合统计
求和、计数、最大最小值很方便。

```java
int sum = Arrays.stream(nums).sum();
int max = Arrays.stream(nums).max().orElse(0);
long cnt = Arrays.stream(nums).filter(x -> x > 0).count();
```

适用：

- 数组总和
- 正数个数
- 最大/最小元素

---

### 3. 转成 Set / List / Map
适合快速构造辅助容器。

```java
Set<Integer> set = Arrays.stream(nums).boxed().collect(Collectors.toSet());
List<Integer> list = Arrays.stream(nums).boxed().collect(Collectors.toList());
```

适用：

- 判重
- 快速查找
- 结果收集

> 注意：基本类型流如 `IntStream` 收集到集合前，常常要先 `boxed()`。

---

### 4. 词频统计 / 分组
这类题 Stream 很顺手。

```java
Map<String, Long> freq = words.stream()
    .collect(Collectors.groupingBy(x -> x, Collectors.counting()));
```

适用：

- 单词出现次数
- 字母分组
- 按类别分桶

---

### 5. 打平嵌套结构
二维列表、嵌套集合可以用 `flatMap`。

```java
List<Integer> flat = lists.stream()
    .flatMap(List::stream)
    .collect(Collectors.toList());
```

适用：

- 二维列表转一维
- 多组结果合并

---

### 6. 条件判断
快速做“是否存在 / 是否全部满足”。

```java
boolean hasZero = Arrays.stream(nums).anyMatch(x -> x == 0);
boolean allPositive = Arrays.stream(nums).allMatch(x -> x > 0);
```

适用：

- 是否存在目标值
- 是否全部满足条件
- 是否都不满足

---

### 7. 索引流
有时能替代简单的下标遍历。

```java
IntStream.range(0, nums.length)
```

适用：

- 生成区间
- 简单按下标映射

但注意：

- 一旦涉及复杂边界、双指针、窗口移动，**还是普通 `for` 更清晰**。

---

# LeetCode 中最推荐的使用原则

## 推荐用 Stream 的地方
- 输入预处理
- 去重、排序、过滤
- 结果收集
- 频次统计
- 简单判断和聚合

## 不推荐用 Stream 的地方
- 双指针
- 滑动窗口
- 动态规划
- 回溯
- DFS / BFS
- 图论
- 原地交换 / 原地修改数组

---

# 最后给你一个“背诵版”

**LeetCode 用 Stream：**
- 前处理：过滤、去重、排序
- 统计：sum / max / count
- 转换：toList / toSet / toMap
- 分组：groupingBy
- 打平：flatMap
- 判断：anyMatch / allMatch

**不要硬用在：**
- 双指针
- 滑窗
- DP
- 回溯
- 图搜索
- 复杂索引控制

---

如果你愿意，我下一条可以继续直接给你：

1. **XMind 更适合导入的层级版文本**
2. **Markdown 大纲版**
3. **LeetCode Stream 高频模板 20 条速查表**
4. **把这两份 `.mm` 再整理成更适合考试背诵的极简版**