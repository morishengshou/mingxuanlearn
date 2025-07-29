*Thinking...*

> 用户问了三个关于Java ArrayList的问题：
> 1. ArrayList的默认排序方式
> 2. 使用addAll合并两个ArrayList的排序结果
> 3. 如何为自定义对象的ArrayList实现自定义排序规则
> 
> 我需要用中文回答，因为用户使用的是中文。
> 
> 让我逐一回答：
> 
> 1. ArrayList本身是没有默认排序的，它维护元素的插入顺序。
> 2. addAll方法只是将第二个集合的元素按顺序添加到第一个集合的末尾，不会进行排序。
> 3. 对于自定义排序，可以使用Comparator或让对象实现Comparable接口。

Java的ArrayList本身**没有默认排序方式**，它按照元素的**插入顺序**来维护元素。ArrayList是一个有序集合（ordered collection），但这里的"有序"指的是保持插入顺序，而不是排序顺序。

## 使用addAll合并ArrayList

当使用`addAll()`方法合并两个ArrayList时，第二个集合的元素会按照它们在原集合中的顺序**依次追加**到第一个集合的末尾，不会进行任何排序。例如：

```java
ArrayList<Integer> list1 = new ArrayList<>(Arrays.asList(3, 1, 4));
ArrayList<Integer> list2 = new ArrayList<>(Arrays.asList(2, 5, 0));
list1.addAll(list2);
// 结果：[3, 1, 4, 2, 5, 0]
```

## 自定义对象的排序实现

对于根据Product和Manufacture属性排序，有以下几种实现方式：

### 方法1：使用Comparator（推荐）

```java
import java.util.*;

class Item {
    private String product;
    private String manufacture;
    
    // 构造函数、getter、setter省略
    public Item(String product, String manufacture) {
        this.product = product;
        this.manufacture = manufacture;
    }
    
    public String getProduct() { return product; }
    public String getManufacture() { return manufacture; }
    
    @Override
    public String toString() {
        return product + " - " + manufacture;
    }
}

// 使用示例
public class Main {
    public static void main(String[] args) {
        ArrayList<Item> items = new ArrayList<>();
        items.add(new Item("Phone", "Apple"));
        items.add(new Item("Phone", "Samsung"));
        items.add(new Item("Laptop", "Dell"));
        items.add(new Item("Laptop", "Apple"));
        
        // 方式1：使用Comparator.comparing链式调用
        items.sort(Comparator.comparing(Item::getProduct)
                            .thenComparing(Item::getManufacture));
        
        // 方式2：自定义Comparator
        items.sort(new Comparator<Item>() {
            @Override
            public int compare(Item o1, Item o2) {
                int productCompare = o1.getProduct().compareTo(o2.getProduct());
                if (productCompare != 0) {
                    return productCompare;
                }
                return o1.getManufacture().compareTo(o2.getManufacture());
            }
        });
        
        // 方式3：使用Lambda表达式
        items.sort((o1, o2) -> {
            int productCompare = o1.getProduct().compareTo(o2.getProduct());
            if (productCompare != 0) {
                return productCompare;
            }
            return o1.getManufacture().compareTo(o2.getManufacture());
        });
    }
}
```

### 方法2：实现Comparable接口

```java
class Item implements Comparable<Item> {
    private String product;
    private String manufacture;
    
    // 构造函数、getter、setter省略
    
    @Override
    public int compareTo(Item other) {
        int productCompare = this.product.compareTo(other.product);
        if (productCompare != 0) {
            return productCompare;
        }
        return this.manufacture.compareTo(other.manufacture);
    }
}

// 使用时直接调用
Collections.sort(items);
// 或者
items.sort(null);  // null表示使用自然排序（Comparable）
```

### 方法3：使用Collections.sort()

```java
// 使用静态方法
Collections.sort(items, Comparator.comparing(Item::getProduct)
                                 .thenComparing(Item::getManufacture));
```

## 注意事项

1. **大小写敏感**：默认的字符串比较是大小写敏感的。如果需要忽略大小写，可以使用：
   ```java
   items.sort(Comparator.comparing(Item::getProduct, String.CASE_INSENSITIVE_ORDER)
                        .thenComparing(Item::getManufacture, String.CASE_INSENSITIVE_ORDER));
   ```

2. **null值处理**：如果属性可能为null，需要特殊处理：
   ```java
   items.sort(Comparator.comparing(Item::getProduct, 
                                   Comparator.nullsFirst(String::compareTo))
                        .thenComparing(Item::getManufacture, 
                                      Comparator.nullsFirst(String::compareTo)));
   ```

3. **性能考虑**：对于大量数据，排序的时间复杂度是O(n log n)。如果需要保持元素始终有序，可以考虑使用TreeSet或PriorityQueue等数据结构。