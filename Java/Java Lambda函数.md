# Java Lambda 表达式新手教程（面向入门）

> 目标：看懂并会写常见 Lambda；知道它和“匿名内部类”是什么关系；能在 `List/Map`、排序、线程、回调里用起来。  
> 说明：以下示例以 Java 8+ 为基础。

---

## 1. Lambda 是什么？解决什么问题？

Lambda 本质上是：**把“一个方法的实现”当作一个值传来传去**。  
它通常用来替代**只有一个抽象方法**的接口实现（也就是 *函数式接口*）。

### 匿名内部类 vs Lambda

**匿名内部类：**
```java
Runnable r = new Runnable() {
    @Override
    public void run() {
        System.out.println("run...");
    }
};
```

**Lambda：**
```java
Runnable r = () -> System.out.println("run...");
```

---

## 2. 函数式接口（Functional Interface）

**函数式接口**：只有 **1 个抽象方法** 的接口。Lambda 就是用来实现它的。

典型例子：
- `Runnable`：`void run()`
- `Comparator<T>`：`int compare(T a, T b)`
- `Callable<V>`：`V call()`
- `Function<T,R>`：`R apply(T t)`
- `Consumer<T>`：`void accept(T t)`
- `Supplier<T>`：`T get()`
- `Predicate<T>`：`boolean test(T t)`

你也可以自己写：
```java
@FunctionalInterface
interface MyFunc {
    int calc(int a, int b);
}
```

---

## 3. Lambda 语法：`(参数) -> { 方法体 }`

### 3.1 最常见的几种形态

#### (1) 无参数、无返回
```java
Runnable r = () -> System.out.println("hello");
```

#### (2) 有参数、无返回（Consumer）
```java
java.util.function.Consumer<String> c = s -> System.out.println(s);
c.accept("hi");
```

#### (3) 有参数、有返回（Function）
```java
java.util.function.Function<String, Integer> f = s -> s.length();
System.out.println(f.apply("abc")); // 3
```

#### (4) 多参数、有返回（自定义或 Comparator）
```java
java.util.function.BiFunction<Integer, Integer, Integer> add = (a, b) -> a + b;
System.out.println(add.apply(10, 20)); // 30
```

### 3.2 省略规则（新手常踩点）

#### 规则 A：只有一个参数时，小括号可省略
```java
Consumer<String> c1 = (s) -> System.out.println(s);
Consumer<String> c2 = s -> System.out.println(s); // OK
```

#### 规则 B：只有一行时，大括号可省略
```java
Function<String, Integer> f1 = s -> { return s.length(); };
Function<String, Integer> f2 = s -> s.length(); // OK（自动 return）
```

#### 规则 C：有大括号且要返回，就必须写 `return`
```java
Function<String, Integer> f = s -> {
    // 多行逻辑
    int n = s.trim().length();
    return n; // 必须写
};
```

---

## 4. 最常用场景 1：集合遍历与过滤

```java
import java.util.*;
import java.util.stream.Collectors;

public class Demo {
    public static void main(String[] args) {
        List<String> names = Arrays.asList("tom", "jack", "alice", "bob");

        // forEach + lambda
        names.forEach(s -> System.out.println(s));

        // 过滤：留下长度 >= 4 的
        List<String> res = names.stream()
                .filter(s -> s.length() >= 4)
                .collect(Collectors.toList());

        System.out.println(res); // [jack, alice]
    }
}
```

> `stream()` 不是必须学会才能用 lambda，但它是 lambda 的高频搭档。

---

## 5. 最常用场景 2：排序 Comparator

### 老写法：
```java
list.sort(new Comparator<String>() {
    @Override
    public int compare(String a, String b) {
        return a.length() - b.length();
    }
});
```

### Lambda：
```java
list.sort((a, b) -> a.length() - b.length());
```

### 更推荐的新手写法（方法引用 + Comparator 工具）：
```java
list.sort(java.util.Comparator.comparingInt(String::length));
```

---

## 6. 最常用场景 3：线程（Runnable）

```java
new Thread(() -> {
    System.out.println("running in thread: " + Thread.currentThread().getName());
}).start();
```

---

## 7. 方法引用（`::`）—— Lambda 的简写

当你的 Lambda 只是“调用一个现成方法”，可以写成方法引用。

### 7.1 静态方法引用
```java
Function<String, Integer> f1 = s -> Integer.parseInt(s);
Function<String, Integer> f2 = Integer::parseInt;
```

### 7.2 实例方法引用（某个对象的实例方法）
```java
String prefix = "hi:";
Function<String, String> f = prefix::concat; // 等价于 s -> prefix.concat(s)
System.out.println(f.apply("tom")); // hi:tom
```

### 7.3 类的实例方法引用（最常见：`String::length`）
```java
Function<String, Integer> len = String::length; // 等价于 s -> s.length()
```

### 7.4 构造方法引用
```java
Supplier<ArrayList<String>> sup = ArrayList::new;
ArrayList<String> list = sup.get();
```

---

## 8. 变量捕获与 `final` 限制（新手必看）

Lambda 里可以用外部变量，但外部变量必须是**“事实上的 final”**（即赋值后不再修改）。

```java
int base = 10;
Function<Integer, Integer> f = x -> x + base; // OK

// base = 20; // 如果你再改 base，会编译错误
```

为什么？因为 Lambda 可能在别的时刻执行，Java 需要保证捕获变量语义清晰。

---

## 9. `this` 在 Lambda 里指向谁？

- **匿名内部类**：`this` 指匿名类对象
- **Lambda**：`this` 指外层对象（它不会创建一个“新的 this”）

一般新手用不到细节，但知道：Lambda 更像“外层方法的一段代码”。

---

## 10. 常见错误与排查

### (1) “target type of a lambda must be an interface”
你写的 Lambda 没有明确要赋值给哪个**函数式接口**。解决：指定类型或放到需要该接口的地方。

```java
// 错误示意（没有目标类型）
/* () -> System.out.println("x"); */

// 正确：给它一个目标类型
Runnable r = () -> System.out.println("x");
```

### (2) 参数类型不匹配
例如你写 `(a, b) -> a + b`，但目标接口可能期望 `String` 或别的类型。  
解决：看 IDE 提示或显式写参数类型：

```java
BiFunction<Integer, Integer, Integer> add = (Integer a, Integer b) -> a + b;
```

### (3) 使用大括号却忘了 return
```java
Function<String, Integer> f = s -> { s.length(); }; // 错
Function<String, Integer> f2 = s -> { return s.length(); }; // 对
```

---

## 11. 新手练习（建议你自己手敲）

1) 用 `List<Integer>` 过滤出偶数。  
2) 给 `List<String>` 按长度排序。  
3) 写一个 `Map<String, Function<Request, Response>>` 的表驱动（你前面就在做）。  
4) 把 `s -> System.out.println(s)` 改成方法引用 `System.out::println`。

---

## 12. 一句话记忆法

- Lambda 只做一件事：**实现函数式接口的那一个抽象方法**  
- 写法：`(参数) -> (逻辑/返回值)`  
- 常用接口：`Function/Consumer/Supplier/Predicate/Comparator/Runnable`

---

如果你告诉我你目前最常写的场景（比如：Spring Controller、集合处理、回调/策略模式、事件监听），我可以按你的场景给一套“从 if-else 重构到 lambda 表驱动”的循序渐进示例。