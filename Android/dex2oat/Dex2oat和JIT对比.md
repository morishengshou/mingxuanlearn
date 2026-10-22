*Thinking...*

> **Considering word limits for documentation**
> 
> I need to clarify the word limits for the documentation source. It seems like we have a target of around 1600 characters in Chinese, which equates to about 1400 tokens. I’m thinking I should also look at the existing config and code to see what’s cached for grounded sources. My aim is to ensure the answer meets these requirements effectively. Let’s get this sorted!

**AOT 机器码和 JIT 机器码，本质上都是 CPU 可以执行的原生指令。“AOT”和“JIT”主要标记它们是怎样生成的，而不是两种不同的 CPU 指令类型。**ART 的两条编译路径还共享编译器基础设施，只是编译时掌握的信息、采用的策略和产物管理方式不同。([android.googlesource.com](https://android.googlesource.com/platform/art/%2B/master/compiler/optimizing/optimizing_compiler.cc?utm_source=openai))

结合你前面关于“方法开始执行”的问题，我们分几个层次看。

## 一、执行层面：都是机器码，不需要逐条解释 DEX

对于同一个方法，两条路径可以概括为：

```text
                     同一个 DEX 方法
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       dex2oat 提前编译          JIT 在运行时编译
              │                       │
              ▼                       ▼
         AOT 机器码                JIT 机器码
              │                       │
              └───────────┬───────────┘
                          ▼
                     CPU 执行指令
```

**执行 JIT 机器码时，不是“JIT 编译器逐条执行它”，也不是“一边执行每条指令，一边编译这条指令”。**JIT 编译器先生成代码，之后程序进入这些代码执行；AOT 代码也是如此，只不过生成时间更早。([android.googlesource.com](https://android.googlesource.com/platform/art/%2B/master/compiler/optimizing/optimizing_compiler.cc?utm_source=openai))

因此，如果某次调用已经进入编译代码，AOT 与 JIT 的区别不是“一个直接执行，一个还要解释”。

## 二、主要区别：生成条件和生命周期不同

下面描述的是普通应用方法的典型情况：

| 对比项 | AOT 机器码 | JIT 机器码 |
|---|---|---|
| 生成时机 | 提前为后续执行生成 | 应用运行期间按需生成 |
| 编译依据 | DEX、编译选项，可结合 Profile | DEX、运行时状态和分析信息 |
| 产物位置 | 保存在持久化编译产物中，运行时加载 | 提交到内存中的 JIT Code Cache |
| 后续启动 | 产物仍有效时可以复用 | 普通应用的现场编译结果通常不作为下次启动的持久化产物 |
| 主要价值 | 减少后续预热和现场编译成本 | 根据实际运行情况优化热点代码 |

AOT 的文件产物、Profile 引导流程，以及 JIT 向代码缓存提交编译结果的过程，在官方文档和编译器实现中都有对应说明。([source.android.com](https://source.android.com/docs/core/runtime/configure))

**注意：“AOT 在文件中、JIT 在内存中”说的是产物管理方式，不是执行位置。AOT 代码运行时同样需要被加载或映射到进程内存中。**([source.android.com](https://source.android.com/docs/core/runtime/configure))

## 三、同一个方法，两者生成的指令一定相同吗？

**不一定。**

虽然共享编译器，并使用相似的优化手段，但 JIT 可以利用当前运行中的类型信息，进行更有针对性的内联；JIT 还可以生成用于 OSR 的代码。这些因素都可能让最终指令与 AOT 版本不同。([source.android.google.cn](https://source.android.google.cn/docs/core/runtime/jit-compiler?hl=en))

例如，假设有：

```java
int calculate(Operation op, int x) {
    return op.apply(x);
}
```

用一个**概念性示例**说明差异：

- 如果编译时无法确定 `op` 的实际类型，就可能需要保留动态方法调用。
- 如果运行时观察到这个位置几乎总是某一种具体类型，JIT 就可能利用这些信息，在适当检查或保障机制下，直接内联对应实现。

这不是说上述代码一定会这样编译，而是说明：**可用信息不同，会影响优化决策。**官方文档明确指出，运行时类型信息是 JIT 能够改善内联的原因之一。([source.android.google.cn](https://source.android.google.cn/docs/core/runtime/jit-compiler?hl=en))

但不要进一步推导成：

> AOT 完全不了解实际使用情况，只有 JIT 才有 Profile。

**AOT 也可以使用 Profile。**ART 可以把运行期间收集的信息保存下来，供后续 dex2oat 编译使用。只是“保存下来的分析信息”与“当前进程中的实时运行状态”不是完全相同的东西。([source.android.com](https://source.android.com/docs/core/runtime/configure))

## 四、哪一种机器码执行得更快？

**不能仅凭“AOT”或“JIT”标签判断。**共享编译器不保证生成相同指令；运行信息与优化策略不同，也不保证哪一方在所有方法上都更优。([android.googlesource.com](https://android.googlesource.com/platform/art/%2B/master/compiler/optimizing/optimizing_compiler.cc?utm_source=openai))

这里应区分两个问题：

### 1. 代码已经生成后，执行这段代码有多快？

要看具体生成了什么指令、做了哪些优化。例如，某次 JIT 编译利用类型信息成功内联，就可能比未完成该优化的版本更高效。([source.android.google.cn](https://source.android.google.cn/docs/core/runtime/jit-compiler?hl=en))

### 2. 从启动到代码变快，总共付出了多少成本？

AOT 的优势是关键代码可以提前准备好；JIT 则可能需要先运行、收集信息，再消耗 CPU 和内存进行编译。因此，**机器码本身的执行性能，与包含预热、编译在内的整体体验，不是同一个指标。**([source.android.com](https://source.android.com/docs/core/runtime/configure))

## 五、它们的联系：不是“机器码互转”，而是共享编译能力与分析信息

正常的 Profile 引导流程可以理解为：

```text
运行 DEX
   │
   ├── 按需 JIT 编译 → 本次运行使用的机器码
   │
   └── 收集并保存 Profile
                  │
                  ▼
          dex2oat 读取 DEX + Profile
                  │
                  ▼
          为后续运行生成 AOT 机器码
```

**这里不是把 JIT 机器码直接改名或复制成 AOT 文件，而是利用 Profile，重新对 DEX 进行编译。**([source.android.com](https://source.android.com/docs/core/runtime/configure))

另外，同一个方法在特定情况下可以同时存在 AOT 和 JIT 编译版本；“存在两份代码”不等于“一次调用同时执行两份代码”。这也对应你前面的理解：应区分**可用的代码版本**与**当前调用正在执行的代码版本**。([source.android.google.cn](https://source.android.google.cn/docs/core/runtime/jit-compiler?hl=en))

---

**最终可以这样记：**

> **从执行结果看，二者都是机器码；从生成过程看，AOT 是提前编译，JIT 是运行时编译；从优化效果看，二者可能生成不同指令，但不存在仅凭名称就能判断的绝对快慢关系。**([android.googlesource.com](https://android.googlesource.com/platform/art/%2B/master/compiler/optimizing/optimizing_compiler.cc?utm_source=openai))