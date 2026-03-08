要检查一个 ArrayDeque（注意拼写：ArrayDeque，而非 ArrayDqueue）里的数字是否全部相同，可以有多种做法。下面给出几种常见且高效的方法。

前提：ArrayDeque 是一个双端队列，不支持随机访问索引；遍历时应使用迭代器或增强 for。

方法一：取首个元素为基准，遍历比对（推荐）
- 时间复杂度：O(n)
- 额外空间：O(1)

```java
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Iterator;

public class AllEqualCheck {
    public static boolean allEqual(Deque<Integer> dq) {
        if (dq.isEmpty()) return true; // 空集合可视为“全一样”
        Iterator<Integer> it = dq.iterator();
        Integer first = it.next();
        while (it.hasNext()) {
            Integer x = it.next();
            if ((first == null && x != null) || (first != null && !first.equals(x))) {
                return false;
            }
        }
        return true;
    }

    public static void main(String[] args) {
        Deque<Integer> d1 = new ArrayDeque<>();
        d1.add(5); d1.add(5); d1.add(5);
        System.out.println(allEqual(d1)); // true

        Deque<Integer> d2 = new ArrayDeque<>();
        d2.add(5); d2.add(6); d2.add(5);
        System.out.println(allEqual(d2)); // false

        Deque<Integer> d3 = new ArrayDeque<>();
        System.out.println(allEqual(d3)); // true（空）
    }
}
```

如果确定不可能包含 null，可以简化为：
```java
Integer first = dq.peekFirst();
for (Integer x : dq) {
    if (!first.equals(x)) return false;
}
return true;
```

方法二：使用 Set 去重后判断大小
- 简洁但需要额外空间。
- 时间复杂度：O(n)，空间复杂度：O(k)，k 为不同元素个数。

```java
import java.util.*;

public static boolean allEqualWithSet(Deque<Integer> dq) {
    if (dq.isEmpty()) return true;
    Set<Integer> s = new HashSet<>(dq); // 迭代构造
    return s.size() <= 1;
}
```

方法三：流式写法（Java 8+）
- 可读性好，但流有一定开销。

1) 基于 distinct 计数：
```java
public static boolean allEqualStream(Deque<Integer> dq) {
    return dq.stream().distinct().limit(2).count() <= 1;
}
```

2) 与首元素比较：
```java
public static boolean allEqualStream2(Deque<Integer> dq) {
    if (dq.isEmpty()) return true;
    Integer first = dq.peekFirst();
    return dq.stream().allMatch(x -> Objects.equals(x, first));
}
```

注意事项
- ArrayDeque 不允许存 null（向其中 add(null) 会抛出 NullPointerException）。如果你的代码路径可能产生 null，请改用 LinkedList 或先过滤 null。
- 若元素是浮点数（Double/Float），考虑 NaN 与 -0.0/+0.0 的比较行为：
  - Objects.equals(Double.NaN, Double.NaN) 为 true。
  - 0.0 与 -0.0 在 equals 上是不同的；如需视为相同，可以比较 Double.doubleToLongBits 或使用误差阈值。
- 如果队列很大且你只需知道“是否存在不同元素”，在方法一中一旦发现不等就尽早返回即可（已体现）。