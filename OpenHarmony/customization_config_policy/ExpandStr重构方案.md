# `ExpandStr` 函数重构方案

## 一、原始函数与问题分析

### 1.1 原始代码

```c
static char *ExpandStr(char *src, const char *def, QueryFunc queryFunc)
{
    bool ok = true;
    StringHolder sh = { 0 };
    char *copyCur = NULL;
    char *searchCur = NULL;
    char *end = src + strlen(src);
    for (copyCur = searchCur = src; ok && searchCur < end;) {
        char *varStart = NULL;
        char *varEnd = NULL;
        char *find = strchr(searchCur, '$');
        if (!find) {
            ok = ok && AppendStr(&sh, copyCur);
            break;
        } else if ((varStart = strchr(find, '{')) && (varStart == find + 1) && (varEnd = strchr(find, '}')) &&
            varEnd - varStart > 0) { // Get user defined name
            *find = *varEnd = 0;
            ok = ok && AppendStr(&sh, copyCur);
            char *name = find + 2;
            char *defVal = strstr(name, SEP_FOR_X_VALUE);
            if (defVal) {
                *defVal = 0;
                defVal = TrimInplace(defVal + strlen(SEP_FOR_X_VALUE), false);
            }
            char *value = queryFunc(name);
            if (value || defVal || def) {
                ok = ok && AppendStr(&sh, value ? value : (defVal ? defVal : def));
                FreeIf(value);
            } else {
                errno = EINVAL;
                ok = false;
                break;
            }
            copyCur = searchCur = varEnd + 1;
        } else {
            searchCur = find + 1;
        }
    }
    if (!ok) {
        FreeIf(sh.p);
        sh.p = NULL;
    }
    return sh.p;
}
```

### 1.2 函数功能说明

将字符串 `src` 中的 `${name}` 或 `${name:-default}` 占位符展开为实际值，
类似 Shell 参数展开。展开规则：

```
输入：  "etc/carrier/${key:-value}/config"
         ↑ 字面量    ↑ 变量引用           ↑ 字面量

展开后："etc/carrier/46060/config"
         （若 queryFunc("key") 返回 "46060"）
```

解析优先级：`queryFunc(name)` 返回值 > `:-` 后的默认值 > 参数 `def`。

### 1.3 嵌套深度分析

```
for (...)                               // 第 1 层
    if (!find)                          // 第 2 层
    else if (complex condition...)      // 第 2 层
        if (defVal)                     // 第 3 层
        if (value || defVal || def)     // 第 3 层
            ok = ok && AppendStr(...)   // 第 4 层（含短路运算的条件表达式）
        else                            // 第 3 层
    else                                // 第 2 层
```

最深处逻辑位于第 4 层，且 `else if` 条件行同时包含**4 个副作用赋值**（`varStart = ...`、`varEnd = ...`），
可读性极差。

---

## 二、安全风险

### 风险1：缺少 NULL 指针入参检查（高风险）

```c
// src == NULL 时，strlen(src) 直接崩溃
char *end = src + strlen(src);

// queryFunc == NULL 时，queryFunc(name) 直接崩溃
char *value = queryFunc(name);
```

当前代码对 `src` 和 `queryFunc` 均无 NULL 检查。
虽然现有调用点均保证了非 NULL，但函数本身缺乏防御性。

**修改建议**：在函数入口添加 NULL 守卫，返回 NULL：

```c
if (src == NULL || queryFunc == NULL) {
    return NULL;
}
```

### 风险2：原地修改入参 `src` 是隐式破坏性操作（中风险）

函数通过向 `src` 中写入 `'\0'` 来原地切分字符串：

```c
*find = *varEnd = 0;  // 直接改写调用方传入的缓冲区
```

调用 `ExpandStr` 后，`src` 原有内容已被破坏，不可再用。
函数签名（`char *src`，非 `const`）暗示了可修改性，但调用方若不知情极易误用。

**当前调用点验证**（安全）：

```c
// GetFollowXPathByMode 中：
char *expandVal = ExpandStr(followXPath, "-x-", CustGetSystemParam);
FreeCharIf(followXPath);   // ← src 使用后立即释放，不存在误用
```

**修改建议**：补充注释，明确说明 `src` 在调用后内容未定义：

```c
/**
 * @brief 展开 src 中的 ${name} / ${name:-default} 变量引用
 * @warning src 在调用后内容被原地修改，调用方不应在调用后继续使用 src。
 */
static char *ExpandStr(char *src, const char *def, QueryFunc queryFunc)
```

### 风险3：条件中混有副作用赋值，掩盖逻辑错误（低风险）

原始条件：

```c
} else if ((varStart = strchr(find, '{')) && (varStart == find + 1) &&
           (varEnd = strchr(find, '}'))   && varEnd - varStart > 0) {
```

赋值写在条件表达式中，若阅读者或静态分析工具将 `=` 误读为 `==`，
或调整短路求值顺序，均会导致逻辑错误。这类代码在代码审查工具中通常会触发警告。

**修改建议**：提取为独立的辅助函数，消除条件中的副作用（见第三节）。

---

## 三、重构策略

采用**提取辅助函数 + 提前返回/continue**的组合方式降低嵌套：

| 策略 | 说明 |
|------|------|
| 提取 `FindVarEnd` | 将 `else if` 中 4 个副作用赋值抽离为独立函数，返回 `varEnd` 或 `NULL` |
| 提取 `ExtractVarNameAndDefault` | 将名称与默认值的切分逻辑独立，消除内层 `if` |
| `continue` 替代 `else` | "跳过无效 `$`" 分支用 `continue` 表达，避免 else 嵌套 |
| `break` on error | 错误后立即 `break`，不让后续代码在 `ok == false` 状态下继续执行 |
| `for` 改 `while` | 变量声明提到循环外，循环体职责更清晰 |

---

## 四、重构后代码

### 4.1 新增辅助函数1：`FindVarEnd`

```c
/**
 * @brief 检查 dollarPos 是否指向合法的 ${...} 引用起始位置，并返回闭合 '}' 的位置。
 *
 * 合法形式：'$' 紧跟 '{'，且之后存在 '}'。
 *
 * @param dollarPos  指向 '$' 字符的指针
 * @return 指向闭合 '}' 的指针；若不是合法 ${...} 则返回 NULL
 */
static char *FindVarEnd(char *dollarPos)
{
    if (dollarPos[1] != '{') {
        return NULL;
    }
    /* 从 '{' 之后开始搜索 '}'，自然满足内容非空的要求 */
    return strchr(dollarPos + 2, '}');
}
```

### 4.2 新增辅助函数2：`ExtractVarNameAndDefault`

```c
/**
 * @brief 在 src 原地切分 ${name:-defval} 中的名称与默认值。
 *
 * 向 *varEnd 写入 '\0'，终止整个变量引用区间。
 * 若存在 ":-" 分隔符，同样写入 '\0' 终止名称，并返回默认值字符串。
 *
 * @param nameStart  '{' 之后第一个字符的指针（即名称起始）
 * @param varEnd     '}' 字符的指针（调用后被置为 '\0'）
 * @return 指向默认值字符串（已 trim）的指针；无默认值则返回 NULL
 *
 * @warning 会修改 nameStart 和 varEnd 所在的缓冲区。
 */
static char *ExtractVarNameAndDefault(char *nameStart, char *varEnd)
{
    *varEnd = '\0';
    char *sep = strstr(nameStart, SEP_FOR_X_VALUE);
    if (sep == NULL) {
        return NULL;
    }
    *sep = '\0';
    return TrimInplace(sep + strlen(SEP_FOR_X_VALUE), false);
}
```

### 4.3 重构后的 `ExpandStr`

```c
/**
 * @brief 展开 src 中所有 ${name} / ${name:-default} 变量引用。
 *
 * 变量值解析优先级：queryFunc(name) > ":-" 后的内联默认值 > 参数 def。
 * 若三者均无法提供值，errno 置为 EINVAL 并返回 NULL。
 *
 * @param src        待展开的字符串（原地修改，调用后内容未定义）
 * @param def        全局兜底默认值，可为 NULL
 * @param queryFunc  参数查询回调，不可为 NULL
 * @return 展开后的新字符串（堆分配，调用方负责 free）；失败返回 NULL
 *
 * @warning src 在调用后内容被原地修改，调用方不应在调用后继续使用 src。
 */
static char *ExpandStr(char *src, const char *def, QueryFunc queryFunc)
{
    if (src == NULL || queryFunc == NULL) {
        return NULL;
    }

    bool ok = true;
    StringHolder sh = { 0 };
    char *end = src + strlen(src);
    char *copyCur = src;
    char *searchCur = src;

    while (ok && searchCur < end) {
        char *find = strchr(searchCur, '$');

        /* 无更多 '$'：将剩余字面量追加后退出 */
        if (find == NULL) {
            ok = AppendStr(&sh, copyCur);
            break;
        }

        char *varEnd = FindVarEnd(find);

        /* '$' 后不是合法 '{...}'：跳过此 '$'，继续向后搜索 */
        if (varEnd == NULL) {
            searchCur = find + 1;
            continue;
        }

        /* 将 '$' 前的字面量追加到输出 */
        *find = '\0';
        ok = AppendStr(&sh, copyCur);
        if (!ok) {
            break;
        }

        /* 切分出变量名与内联默认值，调用查询函数 */
        char *name = find + 2;                                 /* 跳过 '$' 和 '{' */
        char *defVal = ExtractVarNameAndDefault(name, varEnd); /* 可能为 NULL */
        char *queryResult = queryFunc(name);

        const char *resolved = queryResult != NULL ? queryResult :
                               defVal      != NULL ? defVal      : def;
        if (resolved != NULL) {
            ok = AppendStr(&sh, resolved);
        } else {
            errno = EINVAL;
            ok = false;
        }
        FreeCharIf(queryResult);

        copyCur = searchCur = varEnd + 1;
    }

    if (!ok) {
        FreeCharIf(sh.p);
        sh.p = NULL;
    }
    return sh.p;
}
```

---

## 五、完整 diff

```diff
+/**
+ * @brief 检查 dollarPos 是否指向合法的 ${...} 引用起始位置。
+ * @return 闭合 '}' 的指针；非合法 ${...} 则返回 NULL
+ */
+static char *FindVarEnd(char *dollarPos)
+{
+    if (dollarPos[1] != '{') {
+        return NULL;
+    }
+    return strchr(dollarPos + 2, '}');
+}
+
+/**
+ * @brief 原地切分 ${name:-defval}，返回默认值字符串或 NULL。
+ * @warning 修改 nameStart 和 varEnd 所在缓冲区。
+ */
+static char *ExtractVarNameAndDefault(char *nameStart, char *varEnd)
+{
+    *varEnd = '\0';
+    char *sep = strstr(nameStart, SEP_FOR_X_VALUE);
+    if (sep == NULL) {
+        return NULL;
+    }
+    *sep = '\0';
+    return TrimInplace(sep + strlen(SEP_FOR_X_VALUE), false);
+}
+
+/**
+ * @brief 展开 src 中所有 ${name} / ${name:-default} 变量引用。
+ * @warning src 在调用后内容被原地修改，调用方不应继续使用 src。
+ */
 static char *ExpandStr(char *src, const char *def, QueryFunc queryFunc)
 {
-    bool ok = true;
-    StringHolder sh = { 0 };
-    char *copyCur = NULL;
-    char *searchCur = NULL;
-    char *end = src + strlen(src);
-    for (copyCur = searchCur = src; ok && searchCur < end;) {
-        char *varStart = NULL;
-        char *varEnd = NULL;
-        char *find = strchr(searchCur, '$');
-        if (!find) {
-            ok = ok && AppendStr(&sh, copyCur);
-            break;
-        } else if ((varStart = strchr(find, '{')) && (varStart == find + 1) && (varEnd = strchr(find, '}')) &&
-            varEnd - varStart > 0) { // Get user defined name
-            *find = *varEnd = 0;
-            ok = ok && AppendStr(&sh, copyCur);
-            char *name = find + 2;
-            char *defVal = strstr(name, SEP_FOR_X_VALUE);
-            if (defVal) {
-                *defVal = 0;
-                defVal = TrimInplace(defVal + strlen(SEP_FOR_X_VALUE), false);
-            }
-            char *value = queryFunc(name);
-            if (value || defVal || def) {
-                ok = ok && AppendStr(&sh, value ? value : (defVal ? defVal : def));
-                FreeIf(value);
-            } else {
-                errno = EINVAL;
-                ok = false;
-                break;
-            }
-            copyCur = searchCur = varEnd + 1;
-        } else {
-            searchCur = find + 1;
-        }
-    }
-    if (!ok) {
-        FreeIf(sh.p);
-        sh.p = NULL;
-    }
-    return sh.p;
+    if (src == NULL || queryFunc == NULL) {
+        return NULL;
+    }
+
+    bool ok = true;
+    StringHolder sh = { 0 };
+    char *end = src + strlen(src);
+    char *copyCur = src;
+    char *searchCur = src;
+
+    while (ok && searchCur < end) {
+        char *find = strchr(searchCur, '$');
+
+        if (find == NULL) {
+            ok = AppendStr(&sh, copyCur);
+            break;
+        }
+
+        char *varEnd = FindVarEnd(find);
+
+        if (varEnd == NULL) {
+            searchCur = find + 1;
+            continue;
+        }
+
+        *find = '\0';
+        ok = AppendStr(&sh, copyCur);
+        if (!ok) {
+            break;
+        }
+
+        char *name = find + 2;
+        char *defVal = ExtractVarNameAndDefault(name, varEnd);
+        char *queryResult = queryFunc(name);
+
+        const char *resolved = queryResult != NULL ? queryResult :
+                               defVal      != NULL ? defVal      : def;
+        if (resolved != NULL) {
+            ok = AppendStr(&sh, resolved);
+        } else {
+            errno = EINVAL;
+            ok = false;
+        }
+        FreeCharIf(queryResult);
+
+        copyCur = searchCur = varEnd + 1;
+    }
+
+    if (!ok) {
+        FreeCharIf(sh.p);
+        sh.p = NULL;
+    }
+    return sh.p;
 }
```

---

## 六、逻辑等价性验证

| 场景 | 原始行为 | 重构后行为 |
|------|---------|----------|
| `src` 中无 `$` | 追加全部字面量，返回副本 | 同左 |
| `$` 后无 `{` | `searchCur = find + 1` 跳过 | 同左（`continue`）|
| `${name}` 且 queryFunc 有值 | 追加查询结果 | 同左 |
| `${name:-def}` 且 queryFunc 无值 | 追加内联默认值 | 同左 |
| `${name}` 且三者均无值 | `errno=EINVAL`，返回 NULL | 同左 |
| `AppendStr` 失败 | `ok=false`，后续短路，返回 NULL | `ok=false`，`break`，返回 NULL |
| `src == NULL` | 崩溃（`strlen(NULL)`）| 返回 NULL（已修复）|
| `queryFunc == NULL` | 崩溃（NULL 函数指针调用）| 返回 NULL（已修复）|

---

## 七、修改文件与影响范围

| 项目 | 说明 |
|------|------|
| 修改文件 | 仅 `config_policy_utils.c` |
| 新增函数 | `FindVarEnd`、`ExtractVarNameAndDefault`（均为 `static`，不对外暴露）|
| 删除代码 | `varStart` 局部变量（已无用）|
| 公共 API 变化 | 无 |
| 头文件变化 | 无 |
| 与 `FreeIf→FreeCharIf` 的关系 | 重构后代码中已同步使用 `FreeCharIf`，两项修改可合并提交 |

> **注意**：`FindVarEnd` 和 `ExtractVarNameAndDefault` 需声明在 `ExpandStr` 之前，
> 或在文件顶部补充前向声明。
