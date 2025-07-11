在 Java 中，你可以通过**方法重载**（Overloading）来实现一个可以接受不同数据类型（如 `long`, `float`, `double`）的平均值计算函数，并且都返回 `double`。Java 的方法重载允许你定义多个同名方法，只要参数类型或数量不同即可。

下面是一个示例，支持 `long[]`, `float[]`, `double[]` 三种数组输入，每种情况都返回 `double`：

```java
public class AverageCalculator {

    // 计算 long 数组的平均值
    public static double average(long[] nums) {
        if (nums == null || nums.length == 0) return 0.0;
        long sum = 0L;
        for (long n : nums) sum += n;
        return (double) sum / nums.length;
    }

    // 计算 float 数组的平均值
    public static double average(float[] nums) {
        if (nums == null || nums.length == 0) return 0.0;
        float sum = 0f;
        for (float n : nums) sum += n;
        return (double) sum / nums.length;
    }

    // 计算 double 数组的平均值
    public static double average(double[] nums) {
        if (nums == null || nums.length == 0) return 0.0;
        double sum = 0.0;
        for (double n : nums) sum += n;
        return sum / nums.length;
    }

    public static void main(String[] args) {
        long[] longs = {1, 2, 3};
        float[] floats = {1.0f, 2.0f, 3.0f};
        double[] doubles = {1.0, 2.0, 3.0};

        System.out.println(average(longs));   // 输出 2.0
        System.out.println(average(floats));  // 输出 2.0
        System.out.println(average(doubles)); // 输出 2.0
    }
}
```

### 说明

- `average(long[] nums)` 适用于 long 型数组。
- `average(float[] nums)` 适用于 float 型数组。
- `average(double[] nums)` 适用于 double 型数组。

**全部函数都返回 double 类型**，保证了输入无论是哪种数值类型，返回类型一致，便于后续处理。

---

#### 扩展

如果你想用**可变参数**（varargs）方式，也可以这样写：

```java
public static double average(long... nums) { ... }
public static double average(float... nums) { ... }
public static double average(double... nums) { ... }
```

这样你就可以直接传入多个参数而不必先构造数组。

---

如需支持更多数据类型（如 `int`），可继续扩展重载方法。  
如果希望更通用（比如混合类型），则需要使用 `Number[]` 或 `Object[]`，但这样会涉及类型判断和转换，通常用法不如上述简洁明了。

如需进一步举例或扩展，欢迎继续提问！


这是个很有代表性的问题！**Java 的泛型（Generics）**主要用于类和方法的类型参数化，但**泛型不支持基本数据类型（如 `int`, `long`, `float`, `double`）**，只能用它们的包装类型（如 `Integer`, `Long`, `Float`, `Double`）。而且，泛型不支持类型约束，比如“只能是数值类型”，只能限定为某个类的子类。

你**可以写一个泛型方法，参数类型为 `T extends Number`**，然后用 `Number` 的方法（如 `doubleValue()`）统一获取数值，来实现对多种数值类型的兼容。这样可以处理 `Integer`, `Long`, `Float`, `Double` 等包装类数组或集合。

### 示例代码：泛型实现平均值计算

```java
public class AverageCalculator {

    // 支持多种 Number 子类类型的泛型平均值计算
    public static <T extends Number> double average(T[] nums) {
        if (nums == null || nums.length == 0) return 0.0;
        double sum = 0.0;
        for (T n : nums) {
            sum += n.doubleValue();
        }
        return sum / nums.length;
    }

    public static void main(String[] args) {
        Long[] longs = {1L, 2L, 3L};
        Float[] floats = {1.0f, 2.0f, 3.0f};
        Double[] doubles = {1.0, 2.0, 3.0};
        Integer[] ints = {1, 2, 3};

        System.out.println(average(longs));   // 输出 2.0
        System.out.println(average(floats));  // 输出 2.0
        System.out.println(average(doubles)); // 输出 2.0
        System.out.println(average(ints));    // 输出 2.0
    }
}
```

---

### 重点说明

- **只能用包装类型数组**：如 `Long[]`, `Float[]`, `Double[]`, `Integer[]`，不能直接用 `long[]`、`float[]`、`double[]`、`int[]`。
- **通过 `doubleValue()` 实现类型统一**：`Number` 类有 `doubleValue()` 方法，所有其子类都可用。
- 如果用集合，如 `List<T extends Number>`，也可以类似实现。

### 结论

- **泛型可以让代码更通用**，但**不能直接用于基本类型**。
- 如果你需要兼容基本类型数组（如 `long[]`），**只能用方法重载**。
- 如果你愿意用包装类型数组或集合，**泛型方案是可行的**。

---

如需更通用的范型写法或支持集合（`List`），可以继续提问！