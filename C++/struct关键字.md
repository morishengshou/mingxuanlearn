`struct` 是 C 和 C++ 语言中的一个关键字，用于定义一个结构体（Structure）。结构体是一种用户自定义的数据类型，它允许将不同或相同类型的数据项组合成一个单一的类型。使用结构体可以更方便地管理相关数据，使得数据组织更加逻辑化和模块化。

### 基本语法

在 C 和 C++ 中，`struct` 的基本语法如下：

```c
struct struct_name {
    type1 member1;
    type2 member2;
    type3 member3;
    ...
};
```

- `struct_name` 是结构体的名称。
- `type1`, `type2`, `type3`, ... 是结构体成员的数据类型。
- `member1`, `member2`, `member3`, ... 是结构体成员的名称。

### 举例说明

下面是一个简单的例子，展示如何使用 `struct` 来定义一个结构体，并创建该结构体的实例。

```c
#include <stdio.h>

struct Person {
    char name[50];
    int age;
    float height;
};

int main() {
    // 创建结构体变量
    struct Person person1;

    // 赋值
    strcpy(person1.name, "Alice");
    person1.age = 30;
    person1.height = 5.5;

    // 访问结构体成员并打印
    printf("Name: %s\n", person1.name);
    printf("Age: %d\n", person1.age);
    printf("Height: %.1f ft\n", person1.height);

    return 0;
}
```

在这个例子中，我们定义了一个名为 `Person` 的结构体，它有三个成员：`name`（字符数组），`age`（整数），和 `height`（浮点数）。然后，在 `main` 函数中，我们创建了一个 `Person` 类型的变量 `person1`，给它的成员赋值，并打印出来。

### 结构体的特点和用途

结构体在程序设计中非常有用，特别是在需要组织和处理大量相关数据时。以下是结构体的一些主要特点和用途：

1. **封装**：结构体可以封装多个相关的数据项，使得数据管理更加结构化和清晰。
2. **易于管理**：通过结构体，可以将数据处理逻辑集中在一个单一的数据结构上，便于理解和维护。
3. **可用于数组**：结构体可以创建数组，用于存储多个结构体实例，这对于处理数据集非常有用。
4. **作为函数参数**：结构体可以作为整体传递给函数，或者通过指针传递，以减少数据复制的开销。
5. **基础构建块**：在 C++ 中，结构体和类非常相似，事实上，结构体可以包含函数（方法）和访问修饰符（如 public 和 private），使它们成为面向对象编程的基础构建块。

总之，`struct` 关键字在 C 和 C++ 中是定义复杂数据结构的基础工具，它帮助程序员以更结构化的方式处理和组织数据。