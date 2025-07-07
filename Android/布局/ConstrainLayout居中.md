这是 ConstraintLayout 的一个**常见现象**：  
当你在 ConstraintLayout 上设置了 `android:background`（无论是颜色还是图片），并且使用 `wrap_content`，**它的实际尺寸会包含内容区域以及背景绘制的区域**。通常，背景本身不会直接影响布局大小，但由于 Android 的渲染优化机制，**有些背景资源（比如带阴影、九宫格图、带内边距的 shape）会让 ConstraintLayout 布局自适应时比内容大一圈**。

---

## 你要的效果

你希望外层和内层 ConstraintLayout 大小完全一致，即：  
**外层 wrap_content + 背景，内层指定尺寸，二者尺寸重叠。**

---

## 问题本质

- 如果你的 `background` 是纯色（无内边距），**理论上尺寸不会变大**。
- 如果你的 `background` 是带有 padding 的 drawable（如 shape、九宫格图），**wrap_content 的父 ConstraintLayout 会自动加上 background 的 padding**。

**这会导致外层比内层大一圈。**

---

## 解决方法

### 1. 检查 background 是否有 padding

- 如果你用的是 shape/selector/9-patch 等 drawable，**请检查 XML 文件是否设置了 `<padding>` 或 9-patch 边缘区域**。
- 如果是纯色，通常没有这个问题。

### 2. 强制去掉 padding 影响

**方法A：给外层设置 `android:padding="0dp"`**

```xml
<androidx.constraintlayout.widget.ConstraintLayout
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:background="@drawable/your_bg"
    android:padding="0dp">
    ...
</androidx.constraintlayout.widget.ConstraintLayout>
```

**方法B：把背景下沉到内层 ConstraintLayout**

如果背景只是为了视觉效果，不一定非要加在外层，可以直接加到内层：

```xml
<androidx.constraintlayout.widget.ConstraintLayout
    android:layout_width="wrap_content"
    android:layout_height="wrap_content">
    <androidx.constraintlayout.widget.ConstraintLayout
        android:layout_width="200dp"
        android:layout_height="200dp"
        android:background="@drawable/your_bg"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"/>
</androidx.constraintlayout.widget.ConstraintLayout>
```

**方法C：外层尺寸直接指定和内层一样**

如果内层是 200dp，外层也直接写死：

```xml
<androidx.constraintlayout.widget.ConstraintLayout
    android:layout_width="200dp"
    android:layout_height="200dp"
    android:background="@drawable/your_bg">
    <androidx.constraintlayout.widget.ConstraintLayout
        android:layout_width="match_parent"
        android:layout_height="match_parent"/>
</androidx.constraintlayout.widget.ConstraintLayout>
```

---

## 进阶（完全消除背景 padding 影响）

如果你**必须把背景放在外层**，并且背景 drawable 有 padding，  
可以用 `foreground` 代替 `background`（如果只是纯色覆盖），  
或直接用 `android:includeFontPadding="false"`（仅对 TextView 有效，不适用于 ConstraintLayout）。

---

## 总结

- **外层 ConstraintLayout + wrap_content + background + 内层指定尺寸，尺寸不一致，通常是 background drawable 带 padding。**
- **最通用的做法：确保 background 没有 padding 或外层 padding=0，或者直接把 background 放到内层。**
- **如必须外层加背景且 background 有 padding，可以考虑用无 padding 的 drawable 或直接指定外层尺寸。**

---

如果还有问题，欢迎贴出你的 background 资源和 XML 代码，我可以帮你具体分析！