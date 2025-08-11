下面从“是什么、怎么写、编译器如何处理、如何做编译期处理器、与运行期反射的关系、常见陷阱”这几个角度，完整解释 Java 注解，以及如何理解注解在编译期的实现。

一、注解是什么（Annotation as Metadata）
- 注解是对程序元素（类、方法、字段、参数、类型使用等）的结构化元数据。
- 注解本身是“特殊接口”的语法糖：用 @interface 定义，方法即“元素”，元素只能有默认值或编译期常量。
- 注解不改变语义本身，真正的“作用”来自编译器、注解处理器、工具或运行期反射。

二、基础语法与元注解
1) 定义注解
- 元素类型只能是：基本类型、String、Class、enum、注解、以上类型的一维数组。
- 元素不允许为 null；“可选”用默认值或空数组表示。

示例：
```java
import java.lang.annotation.*;

@Retention(RetentionPolicy.RUNTIME)              // 保留策略
@Target({ElementType.TYPE, ElementType.METHOD})  // 作用目标
@Documented
@Inherited                                       // 仅对类继承有效
@Repeatable(Tags.class)                          // 可重复注解（需容器注解）
public @interface Tag {
    String value();
    int level() default 1;
}

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD})
public @interface Tags {
    Tag[] value();
}
```

2) 常见元注解
- @Retention：SOURCE | CLASS | RUNTIME
  - SOURCE：只在源代码存在（例如 @Override）。
  - CLASS：进入 class 文件，运行期不可见。
  - RUNTIME：进入 class 且运行期可见（可反射）。
- @Target：限定使用位置，含 TYPE, FIELD, METHOD, PARAMETER, CONSTRUCTOR, LOCAL_VARIABLE, ANNOTATION_TYPE, PACKAGE, TYPE_PARAMETER, TYPE_USE 等。
- @Inherited：仅对“类上的注解”在子类上通过反射“可见”，不作用于方法/字段。
- @Repeatable：Java 8 起的可重复注解，需声明容器注解。
- @Documented：生成 Javadoc 时包含注解。

3) 类型注解（Type Annotation）
- Java 8 引入的 @Target(TYPE_USE/TYPE_PARAMETER)，可标注任意类型使用位置（如泛型参数、数组、强转处等），供静态分析器使用（如 Checker Framework）。

三、编译器对注解做了什么（编译期实现的核心）
编译的关键阶段（简化）：
1) 解析与符号表构建：解析注解语法，解析注解类型与元素的默认值。
2) 语义检查：
   - 校验目标是否匹配 @Target。
   - 校验元素值类型必须为编译期常量或允许的字面量。
   - 处理 @Repeatable：若出现多次，会在 class 文件里合成为“容器注解”的一条记录。
   - 处理编译器内建注解的规则（如 @Override 校验、@Deprecated 警告、@SafeVarargs 校验等）。
3) 写入 class 文件（取决于 @Retention）：
   - SOURCE：不写入 class。
   - CLASS：写入 RuntimeInvisibleAnnotations/RuntimeInvisibleTypeAnnotations 等属性。
   - RUNTIME：写入 RuntimeVisibleAnnotations/RuntimeVisibleTypeAnnotations 等属性。
   - 反射只能看到 RuntimeVisible* 里的注解；Invisible 的在 class 文件中存在但不可反射获得。
4) 触发注解处理（JSR 269）：
   - javac 内置了注解处理流程（取代早期 APT 工具），在编译轮次（rounds）中调用处理器，允许生成新源文件、报告错误/警告，直到不再有新文件生成。

小结：编译器对注解的“实现”本质是两件事：
- 把注解按策略编码进 class 文件的属性表（或不写入）。
- 提供标准注解处理 SPI（JSR 269），在编译期可读取注解模型进行校验与代码生成。

四、注解处理器（JSR 269）的工作机制
1) 处理器接口与生命周期
- 实现 javax.annotation.processing.Processor（通常继承 AbstractProcessor）。
- 关键对象：
  - ProcessingEnvironment：提供 Messager（打印编译信息）、Filer（生成文件）、Elements/Types（读取元素/类型模型）。
  - RoundEnvironment：每一轮传入，包含本轮发现的带注解元素；可多轮，直到无新文件生成或出错。
- 声明支持的注解类型与源版本：getSupportedAnnotationTypes()/getSupportedSourceVersion()，或用 @SupportedAnnotationTypes/@SupportedSourceVersion。

2) 注册与加载
- 通过 SPI：META-INF/services/javax.annotation.processing.Processor 文件，内容为处理器的全限定类名。
- Gradle/Maven 使用 annotationProcessor 依赖配置；JPMS（模块系统）可用 provides 指令。

3) 处理器能做什么/不能做什么
- 能：读取源码模型、发出编译错误/警告、生成新 .java 或资源文件（Filer）。
- 不能：标准 API 不能直接修改已存在的源文件 AST；像 Lombok 使用编译器内部 API/插件方式进行 AST 变换，超出标准 JSR 269 能力范畴。

4) 极简示例
定义注解与处理器，看到如何在编译期生成代码。

注解：
```java
package demo.anno;

import java.lang.annotation.*;

@Retention(RetentionPolicy.SOURCE)
@Target(ElementType.TYPE)
public @interface AutoHello {
    String value() default "Hello";
}
```

处理器：
```java
package demo.processor;

import demo.anno.AutoHello;
import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.tools.Diagnostic;
import javax.tools.JavaFileObject;
import java.io.Writer;
import java.util.Set;

@SupportedSourceVersion(SourceVersion.RELEASE_17)
@SupportedAnnotationTypes("demo.anno.AutoHello")
public class AutoHelloProcessor extends AbstractProcessor {

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        for (Element e : roundEnv.getElementsAnnotatedWith(AutoHello.class)) {
            if (e.getKind() != ElementKind.CLASS) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "@AutoHello 只能用于类", e);
                continue;
            }
            TypeElement type = (TypeElement) e;
            String pkg = processingEnv.getElementUtils().getPackageOf(type).getQualifiedName().toString();
            String simpleName = type.getSimpleName() + "Hello";
            AutoHello anno = type.getAnnotation(AutoHello.class);
            String greet = (anno == null ? "Hello" : anno.value()); // SOURCE 期也能在同一编译轮取到值

            String fqcn = (pkg.isEmpty() ? "" : pkg + ".") + simpleName;

            try {
                JavaFileObject file = processingEnv.getFiler().createSourceFile(fqcn, type);
                try (Writer w = file.openWriter()) {
                    w.write("package " + pkg + ";\n");
                    w.write("public class " + simpleName + " {\n");
                    w.write("  public static String greet() { return \"" + greet + ", from processor!\"; }\n");
                    w.write("}\n");
                }
            } catch (Exception ex) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR, ex.getMessage(), e);
            }
        }
        return true; // 声明已处理
    }
}
```

SPI 注册（资源文件内容）：
```
META-INF/services/javax.annotation.processing.Processor
```
文件内容：
```
demo.processor.AutoHelloProcessor
```

使用示例：
```java
package demo.app;

import demo.anno.AutoHello;

@AutoHello("Hi")
public class App {}

// 编译后将生成 demo.app.AppHello 类，可直接使用：AppHello.greet()
```

Gradle 依赖（示意）：
- 将处理器打成单独 artifact，在使用方的 build.gradle 中：
  - implementation 项依赖你的注解（只含 @interface）。
  - annotationProcessor 项依赖你的处理器。

五、编译期 vs 运行期
- 编译期（JSR 269）：以“源代码模型”为主（javax.lang.model.*），可以生成新代码、做静态校验（如 Dagger、Room、MapStruct、自定义校验等）。
- 运行期（反射）：通过 java.lang.reflect.AnnotatedElement 的 getAnnotation(s)/getDeclaredAnnotations 读取 RUNTIME 注解；可配合框架（Spring、JAX-RS 等）在运行时做装配/拦截。
- CLASS 保留策略的注解在 class 文件中，但反射不可见；主要供工具或字节码后处理器使用。
- 类型注解（TYPE_USE）的运行期可见性有限：即便记录在 class 文件中，反射 API 也不全面暴露所有位置（例如本地变量的类型注解），更多用于静态检查器。

六、内建与常见编译期行为
- @Override（SOURCE）：编译器校验方法是否正确覆写父类/接口方法。
- @Deprecated（RUNTIME，通常）：编译器发出使用警告，可加 @SuppressWarnings("deprecation") 屏蔽。
- @SuppressWarnings（SOURCE）：告诉编译器抑制特定类别的警告。
- @SafeVarargs（RUNTIME）：标注不产生堆污染的可变参数方法，编译器据此抑制相关警告。
- 各类静态检查框架（如 Error Prone、Checker Framework）借助注解在编译期做更强的类型/空指针/并发等检查。

七、class 文件层面的实现细节（理解“存储方式”）
- 注解被序列化为 attributes：
  - RuntimeVisibleAnnotations / RuntimeInvisibleAnnotations
  - RuntimeVisibleParameterAnnotations / RuntimeInvisibleParameterAnnotations
  - RuntimeVisibleTypeAnnotations / RuntimeInvisibleTypeAnnotations
- SOURCE 策略不写入上述属性。
- RUNTIME 策略写入 RuntimeVisible*，反射可见；CLASS 策略写入 RuntimeInvisible*，反射不可见。
- 重复注解在 class 文件里记录为“容器注解”的一条记录；反射层会自动“拆箱”为重复注解数组。

八、常见陷阱与最佳实践
- 选择合适的 Retention：
  - 仅供编译期处理器使用：SOURCE（体积最小、不会泄漏到产物）。
  - 运行时框架读取：RUNTIME。
  - CLASS 较少单独使用，除非特定工具链约定。
- @Inherited 只对“类上的注解”通过反射向下可见，不会传递到方法/字段。
- 注解元素不能为 null；需要“可选”就给默认值或用 Optional-like 语义（空字符串、空数组）。
- 注解元素类型不支持泛型参数；例如不能写 Class<? extends X>，只能写 Class，并依约束在处理器或运行期自行校验。
- 处理器生成代码时务必使用 Filer，不要手写文件路径；正确设置 originating elements 便于增量编译。
- 处理器应输出清晰诊断信息（Messager），避免“静默失败”；并注意线程安全与性能（避免在 process 中做重 IO）。
- @Repeatable 需要正确定义容器注解；编译器会在 class 中使用容器形式存储。

九、一个快速对照表
- 目的：编译期校验/生成 -> 用 JSR 269 处理器 + SOURCE/CLASS 注解。
- 目的：运行时框架读取 -> 用 RUNTIME 注解 + 反射。
- 想让编译器做语义校验（如覆盖、抑制告警）-> 使用编译器内建注解（@Override 等）或自定义处理器。

如果你希望，我可以：
- 根据你的具体业务场景，帮你设计注解与处理器的 API。
- 给出可直接运行的 Gradle/Maven 最小工程骨架。
- 演示如何用 javap 观察 class 文件中的注解属性，以及如何在处理器中读取复杂注解值。

# 如何自定义注解

下面给你一份从零开始的“自定义 Java 注解”速成指南：怎么定义、怎么用、怎么在运行期/编译期处理，以及注意事项与示例代码。

一、定义一个注解的基本步骤
1) 选择用途
- 运行期让框架/反射读取（如 Spring、JAX‑RS）。
- 编译期做校验或代码生成（如 Dagger、MapStruct、自定义处理器）。
- 仅文档/警告辅助（如 @Override、@SuppressWarnings）。

2) 选定元注解
- @Retention：SOURCE | CLASS | RUNTIME（决定保留到何处）
- @Target：限制能标注到哪些元素（类、方法、字段、参数、类型使用等）
- @Documented：被 Javadoc 收录
- @Inherited：类上的注解对子类可见（仅类，非方法/字段）
- @Repeatable：允许重复标注（需容器注解）

3) 编写 @interface
- 注解元素的合法类型：
  - 基本类型、String、Class（可写 Class<? extends X>）、枚举、其他注解、以及这些类型的一维数组
- 元素不可为 null；可用默认值或空数组表示“可选”
- 可将元素名定义为 value，这样使用时可省略键名

示例：一个可运行时读取的业务注解
```java
import java.lang.annotation.*;

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD, ElementType.FIELD})
@Documented
public @interface Tag {
    String value();          // 必填元素
    int level() default 1;   // 可选，默认值
}
```

二、注解的使用方式
```java
@Tag("service")                 // 等价于 @Tag(value = "service")
public class OrderService {

    @Tag(value = "endpoint", level = 2)
    public void create() {}

    @Tag("config")
    private String region;
}
```

- 数组元素示例：roles = {"admin", "ops"}，单元素也可写 roles = "admin"
- 嵌套注解、枚举、Class 示例：
```java
enum Env { DEV, PROD }

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
@interface Config {
    Env env();
    Class<? extends Runnable> runner();
    SuppressWarnings suppress();   // 嵌套注解
    String[] features() default {};
}
```

三、重复注解与类型注解
- 重复注解
```java
import java.lang.annotation.*;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
@Repeatable(Roles.class)
@interface Role { String value(); }

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
@interface Roles { Role[] value(); }

// 使用
@Role("admin")
@Role("ops")
class User {}

// 读取
Role[] roles = User.class.getAnnotationsByType(Role.class);
```

- 类型注解（Type Use）
```java
@Target(ElementType.TYPE_USE)
@Retention(RetentionPolicy.CLASS)  // 给静态分析或字节码工具
@interface NonNull {}

java.util.List<@NonNull String> names;
String s = (@NonNull String) obj;
```

四、运行期读取（反射）
要用反射读取，Retention 必须是 RUNTIME。
```java
import java.lang.reflect.AnnotatedElement;

Tag t1 = OrderService.class.getAnnotation(Tag.class);
Tag t2 = OrderService.class.getDeclaredAnnotation(Tag.class);
Tag[] all = OrderService.class.getAnnotationsByType(Tag.class); // 兼容重复注解

// 读取方法/字段
var m = OrderService.class.getDeclaredMethod("create");
Tag mt = m.getAnnotation(Tag.class);
```

五、编译期处理（JSR 269 注解处理器，代码生成/校验）
如果注解只为了编译期使用，设为 SOURCE 或 CLASS，更轻量。下面给一个最小可用示例：用注解触发生成一个“问候类”。

1) 定义注解（单独的 annotations 模块/包）
```java
package demo.anno;
import java.lang.annotation.*;

@Retention(RetentionPolicy.SOURCE)
@Target(ElementType.TYPE)
public @interface AutoHello {
    String value() default "Hello";
}
```

2) 编写处理器（processor 模块）
```java
package demo.processor;

import demo.anno.AutoHello;
import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.tools.Diagnostic;
import javax.tools.JavaFileObject;
import java.io.Writer;
import java.util.Set;

@SupportedSourceVersion(SourceVersion.RELEASE_17)
@SupportedAnnotationTypes("demo.anno.AutoHello")
public class AutoHelloProcessor extends AbstractProcessor {

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        for (Element e : roundEnv.getElementsAnnotatedWith(AutoHello.class)) {
            if (e.getKind() != ElementKind.CLASS) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "@AutoHello 只能用于类", e);
                continue;
            }
            TypeElement type = (TypeElement) e;
            String pkg = processingEnv.getElementUtils().getPackageOf(type).getQualifiedName().toString();
            String simpleName = type.getSimpleName() + "Hello";
            String greet = type.getAnnotation(AutoHello.class).value(); // 读取注解值

            String fqcn = (pkg.isEmpty() ? "" : pkg + ".") + simpleName;

            try {
                JavaFileObject file = processingEnv.getFiler().createSourceFile(fqcn, type);
                try (Writer w = file.openWriter()) {
                    w.write("package " + pkg + ";\n");
                    w.write("public class " + simpleName + " {\n");
                    w.write("  public static String greet() { return \"" + greet + ", from processor!\"; }\n");
                    w.write("}\n");
                }
            } catch (Exception ex) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR, ex.getMessage(), e);
            }
        }
        return true;
    }
}
```

3) 注册处理器（resources/META-INF/services/javax.annotation.processing.Processor）
```
demo.processor.AutoHelloProcessor
```

4) 使用注解（在业务模块）
```java
import demo.anno.AutoHello;

@AutoHello("Hi")
public class App {}

// 编译后会生成 AppHello 类：
// String s = AppHello.greet(); // "Hi, from processor!"
```

构建提示：
- 处理器与注解通常分成两个 artifact：使用方只依赖“注解”，在 annotationProcessor 配置中引入“处理器”
- Gradle（示意）：
  - implementation("group:annotations:1.0")
  - annotationProcessor("group:processor:1.0")

六、选择 Retention 的建议
- 仅编译期用：SOURCE（不进 class，产物最小）
- 运行时要反射读取：RUNTIME
- CLASS：较少单独使用，主要给字节码工具或后处理器

七、常见注意点
- 注解元素不能为 null；用默认值或空数组表达“缺省”
- 元素值必须是编译期常量或字面量（new 语句不行）
- @Inherited 只对“类上的注解”有效，方法/字段不会“继承”
- 重复注解必须定义容器注解，并用 @Repeatable 标注
- 生成代码时使用 Filer 并传入 originating elements，利于增量编译
- 反射只能看到 RUNTIME 注解；CLASS 策略的注解虽写入 class，但反射不可见

如果你给我你的应用场景（运行期读取还是编译期生成、标注在哪些元素、需要哪些参数），我可以为你定制注解设计和最小可运行示例工程（Gradle/Maven 两种都可以）。