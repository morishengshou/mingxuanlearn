# `FreeIf(void *p)` 替换方案

## 一、问题描述

`config_policy_utils.c` 第 94 行定义了一个接受 `void *` 指针的工具函数：

```c
static void FreeIf(void *p)
{
    if (p != NULL) {
        free(p);
    }
}
```

该函数违反了公司代码规范中"禁止 `void *` 类型参数"的要求。
本文档分析全部调用点，给出替换方案。

---

## 二、调用点全量分析

`FreeIf` 共被调用 **15 次**，下表列出每处调用点的实参变量名、声明类型及所在函数：

| 行号 | 实参 | 实参声明类型 | 所在函数 |
|------|------|------------|---------|
| 114 | `value` | `char *` | `CustGetSystemParam` |
| 143 | `opKeyValue` | `char *` | `GetOpkeyPath` |
| 146 | `opKeyValue` | `char *` | `GetOpkeyPath` |
| 147 | `result` | `char *` | `GetOpkeyPath` |
| 177 | `p->orgStr` | `char *`（`SplitedStr.orgStr` 字段）| `FreeSplitedStr` |
| 200 | `search` | `char *` | `GetFollowXRule` |
| 201 | `followRule` | `char *` | `GetFollowXRule` |
| 232 | `followRule` | `char *` | `GetFollowXRule` |
| 233 | `search` | `char *` | `GetFollowXRule` |
| 266 | `followXPath` | `char *` | `GetFollowXPathByMode` |
| 267 | `modePathFromCfg` | `char *` | `GetFollowXPathByMode` |
| 308 | `newPtr` | `char *` | `EnsureHolderSpace` |
| 311 | `holder->p` | `char *`（`StringHolder.p` 字段）| `EnsureHolderSpace` |
| 361 | `value` | `char *`（`QueryFunc` 回调返回值）| `ExpandStr` |
| 373 | `sh.p` | `char *`（`StringHolder.p` 字段）| `ExpandStr` |

**结论：全部 15 处调用的实参均为 `char *` 类型，没有任何其他指针类型。**

---

## 三、替换方案

### 3.1 结论

用**一个**明确类型的函数替换，无需拆分为多个函数：

```c
static void FreeCharIf(char *p)
{
    if (p != NULL) {
        free(p);
    }
}
```

函数体与原 `FreeIf` 完全相同，仅将参数类型从 `void *` 改为 `char *`。
所有 15 处调用点将 `FreeIf` 替换为 `FreeCharIf`，**不需要任何其他改动**。

### 3.2 为何只需一个函数

所有实参均来自以下几类来源，类型一致为 `char *`：

| 来源 | 示例 | 类型 |
|------|------|------|
| `calloc` / `malloc` 分配并强转 | `(char *)calloc(...)` | `char *` |
| `CustGetSystemParam` 返回值 | `char *value = CustGetSystemParam(...)` | `char *` |
| `QueryFunc` 函数指针回调返回值 | `typedef char *(*QueryFunc)(...)` | `char *` |
| 结构体 `char *` 字段 | `StringHolder.p`、`SplitedStr.orgStr` | `char *` |

不存在 `SplitedStr *`、`CfgDir *`、`CfgFiles *` 等其他类型传入 `FreeIf` 的情况。
这些结构体指针均由各自的专用 Free 函数处理（`FreeSplitedStr`、`FreeCfgDirList`、`FreeCfgFiles`）。

---

## 四、完整 diff

只涉及 `config_policy_utils.c` 一个文件，共修改 **16 行**（1 处定义 + 15 处调用）：

```diff
-static void FreeIf(void *p)
+static void FreeCharIf(char *p)
 {
     if (p != NULL) {
         free(p);
     }
 }

 // CustGetSystemParam (line 114)
-    FreeIf(value);
+    FreeCharIf(value);

 // GetOpkeyPath (lines 143, 146, 147)
-        FreeIf(opKeyValue);
+        FreeCharIf(opKeyValue);
         return result;
     }
-    FreeIf(opKeyValue);
-    FreeIf(result);
+    FreeCharIf(opKeyValue);
+    FreeCharIf(result);

 // FreeSplitedStr (line 177)
-        FreeIf(p->orgStr);
+        FreeCharIf(p->orgStr);

 // GetFollowXRule (lines 200, 201, 232, 233)
-        FreeIf(search);
-        FreeIf(followRule);
+        FreeCharIf(search);
+        FreeCharIf(followRule);
 ...
-    FreeIf(followRule);
-    FreeIf(search);
+    FreeCharIf(followRule);
+    FreeCharIf(search);

 // GetFollowXPathByMode (lines 266, 267)
-    FreeIf(followXPath);
-    FreeIf(modePathFromCfg);
+    FreeCharIf(followXPath);
+    FreeCharIf(modePathFromCfg);

 // EnsureHolderSpace (lines 308, 311)
-            FreeIf(newPtr);
+            FreeCharIf(newPtr);
 ...
-        FreeIf(holder->p);
+        FreeCharIf(holder->p);

 // ExpandStr (lines 361, 373)
-                FreeIf(value);
+                FreeCharIf(value);
 ...
-        FreeIf(sh.p);
+        FreeCharIf(sh.p);
```

---

## 五、影响范围确认

| 项目 | 结论 |
|------|------|
| 修改文件数 | 1（仅 `config_policy_utils.c`）|
| 修改行数 | 16 行（1 定义 + 15 调用）|
| 头文件改动 | 无（`FreeIf` / `FreeCharIf` 均为 `static`，不对外暴露）|
| 公共 API 改动 | 无 |
| 行为变化 | 无（函数体逻辑完全相同）|
| 需要同步修改的其他文件 | 无 |

`FreeIf` 声明为 `static`，作用域仅限于本文件，替换后无需更改任何头文件或其他源文件。
