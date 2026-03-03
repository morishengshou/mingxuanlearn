# Java 新手排序 `Comparator` 教程（深入浅出 + 易记诀窍 + 示例）

## 1) 先搞清楚：到底在比什么？

Java 排序的核心就是一句话：

> **排序 = 不断比较两个元素，决定谁在前。**  
> `Comparator` 就是“比较规则”。

### `Comparator` 的方法长什么样？
```java
int compare(T a, T b)
```

它的返回值含义（非常重要，背下来）：

- `< 0`：`a` 应该排在 `b` 前面
- `= 0`：`a` 和 `b` 一样（排序不强制交换）
- `> 0`：`a` 应该排在 `b` 后面

### 记忆诀窍（建议直接记这句）
> **负前零平正后**（返回负数在前，0 平手，正数在后）

---

## 2) `Comparable` vs `Comparator`：新手最容易混淆的点

- `Comparable`：**对象自己**定义“天然排序”（例如 `String` 按字典序）。
  - 写在类里：`class Person implements Comparable<Person>`
- `Comparator`：**外部**定义“临时排序规则”（例如同一个 Person 你想按年龄排、也想按姓名排）。
  - 写在外部：`Comparator<Person> byAge = ...`

### 记忆诀窍
> **Comparable = 我天生怎么比**  
> **Comparator = 你想让我怎么比**

---

## 3) 最基本的排序：对 `List` 排序

### 3.1 排数字（升序/降序）
```java
import java.util.*;

public class Demo1 {
    public static void main(String[] args) {
        List<Integer> nums = new ArrayList<>(Arrays.asList(5, 2, 9, 1));

        nums.sort(Integer::compareTo); // 升序
        System.out.println(nums);      // [1, 2, 5, 9]

        nums.sort(Comparator.reverseOrder()); // 降序
        System.out.println(nums);             // [9, 5, 2, 1]
    }
}
```

---

## 4) 自定义对象排序：最常见、最实用

假设我们有 `Person(name, age, score)`，我们想按不同规则排序。

```java
import java.util.*;

class Person {
    String name;
    int age;
    double score;

    Person(String name, int age, double score) {
        this.name = name;
        this.age = age;
        this.score = score;
    }

    @Override
    public String toString() {
        return name + "(age=" + age + ", score=" + score + ")";
    }
}
```

### 4.1 写一个最“直观”的 Comparator（适合新手理解）
按年龄升序：
```java
Comparator<Person> byAgeAsc = (a, b) -> a.age - b.age; // 直观，但有坑（见后面）
```

用起来：
```java
List<Person> list = Arrays.asList(
    new Person("Tom", 20, 88.5),
    new Person("Alice", 18, 91.0),
    new Person("Bob", 20, 79.0)
);

list.sort(byAgeAsc);
System.out.println(list);
```

### 4.2 更推荐的写法（安全 + 易读）：`comparingInt`
```java
list.sort(Comparator.comparingInt(p -> p.age));
```

### 记忆诀窍（强烈建议记住这个“模板”）
> **按 int 排：`Comparator.comparingInt(对象 -> int字段)`**  
> **按 String 排：`Comparator.comparing(对象 -> String字段)`**  
> **按 double 排：`Comparator.comparingDouble(对象 -> double字段)`**

---

## 5) 升序/降序怎么写？（一看就会）

### 5.1 单字段降序：`reversed()`
按年龄降序：
```java
list.sort(Comparator.comparingInt((Person p) -> p.age).reversed());
```

> 注意：这里我写了 `(Person p) -> p.age` 是为了让类型更明确，新手更不容易迷糊。

---

## 6) 多条件排序：先按 A，再按 B（非常常用）

需求：**先按年龄升序**，年龄一样再按**分数降序**，再按**名字升序**。

```java
list.sort(
    Comparator.comparingInt((Person p) -> p.age)
              .thenComparing(Comparator.comparingDouble((Person p) -> p.score).reversed())
              .thenComparing(p -> p.name)
);
```

### 记忆诀窍（背这个链式结构）
> **主键：`comparing...`**  
> **次键：`thenComparing...`**  
> **降序：在对应比较器上 `.reversed()`**

把排序当成“排序链”，从左到右优先级递减。

---

## 7) 新手常见坑：`a.age - b.age` 可能溢出

`a.age - b.age` 直观但在大数时可能溢出（比如比较很大的 `int`），导致结果错。

更安全的写法：
```java
Comparator<Person> byAgeSafe = (a, b) -> Integer.compare(a.age, b.age);
```

或更推荐的模板：
```java
Comparator<Person> byAgeSafe2 = Comparator.comparingInt(p -> p.age);
```

### 记忆诀窍
> **比较 int：用 `Integer.compare` 或 `comparingInt`，别用减法。**

---

## 8) 处理 null：`nullsFirst / nullsLast`

如果 `name` 可能为 `null`，直接 `p -> p.name` 排序会 `NullPointerException`。

```java
list.sort(
    Comparator.comparing(
        (Person p) -> p.name,
        Comparator.nullsLast(String::compareTo)
    )
);
```

### 记忆诀窍
> **可能 null 的字段：给它套一层 `nullsFirst/nullsLast`**

---

## 9) 最小可运行完整示例（复制就跑）

```java
import java.util.*;

public class ComparatorTutorialDemo {

    static class Person {
        String name;
        int age;
        double score;

        Person(String name, int age, double score) {
            this.name = name;
            this.age = age;
            this.score = score;
        }

        @Override
        public String toString() {
            return name + "(age=" + age + ", score=" + score + ")";
        }
    }

    public static void main(String[] args) {
        List<Person> list = new ArrayList<>(Arrays.asList(
                new Person("Tom", 20, 88.5),
                new Person("Alice", 18, 91.0),
                new Person("Bob", 20, 79.0),
                new Person("Carol", 20, 91.0)
        ));

        // 1) 按年龄升序
        list.sort(Comparator.comparingInt(p -> p.age));
        System.out.println("by age asc: " + list);

        // 2) 按年龄降序
        list.sort(Comparator.comparingInt((Person p) -> p.age).reversed());
        System.out.println("by age desc: " + list);

        // 3) 多条件：年龄升序 -> 分数降序 -> 名字升序
        list.sort(
                Comparator.comparingInt((Person p) -> p.age)
                          .thenComparing(Comparator.comparingDouble((Person p) -> p.score).reversed())
                          .thenComparing(p -> p.name)
        );
        System.out.println("age asc, score desc, name asc: " + list);
    }
}
```

---

## 10) 一页记忆卡（建议你保存）

1. **compare 口诀**：**负前零平正后**  
2. **Comparable vs Comparator**：  
   - Comparable：我天生怎么比  
   - Comparator：你想让我怎么比  
3. **推荐模板**：  
   - `comparingInt(x -> x.intField)`  
   - `comparing(x -> x.stringField)`  
   - `thenComparing(...)`  
   - 降序：对“那个字段的比较器” `.reversed()`  
4. **别用减法比较 int**：用 `Integer.compare`/`comparingInt`  
5. **可能有 null**：`nullsFirst/nullsLast`

---

如果你告诉我你的实际排序对象（比如学生、订单、商品）和排序规则（例如“按价格降序，同价按销量降序”），我可以按你的场景再写一版更贴近业务的示例，并解释每一段代码怎么读、怎么记。