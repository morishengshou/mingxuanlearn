下面给出几种常见实现方式，你可根据需求选择。核心是使用 RecyclerView 配合 LayoutManager 来实现两列并按从左到右、从上到下的顺序排布。

方案一：GridLayoutManager（最简单、推荐）
- 适用于普通均匀网格，两列，默认按行从左到右、从上到下布局。
- 支持 item 跨列（可选）。

示例代码（Kotlin）：
```kotlin
val recyclerView = findViewById<RecyclerView>(R.id.recyclerView)
recyclerView.setHasFixedSize(true)

// 两列
val layoutManager = GridLayoutManager(this, 2)
// 若需要某些 item 跨列，可设置 SpanSizeLookup（可选）
// layoutManager.spanSizeLookup = object : GridLayoutManager.SpanSizeLookup() {
//     override fun getSpanSize(position: Int): Int {
//         return if (position == 0) 2 else 1
//     }
// }
recyclerView.layoutManager = layoutManager

val adapter = YourAdapter(items)
recyclerView.adapter = adapter
```

Adapter 关键点（简化示例）：
```kotlin
class YourAdapter(private val data: List<Item>) : RecyclerView.Adapter<YourVH>() {
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): YourVH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_cell, parent, false)
        return YourVH(view)
    }

    override fun onBindViewHolder(holder: YourVH, position: Int) {
        val item = data[position]
        holder.bind(item)
    }

    override fun getItemCount(): Int = data.size
}

class YourVH(itemView: View) : RecyclerView.ViewHolder(itemView) {
    fun bind(item: Item) {
        // 绑定数据
    }
}
```

item 布局（item_cell.xml）建议：
- 宽度用 match_parent，高度 wrap_content，再配合外层使用合适的间距装饰。
- 真正的两列宽度由 GridLayoutManager 负责计算分配，不建议在 item 内再用权重分栏。

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.cardview.widget.CardView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:foreground="?attr/selectableItemBackground"
    android:layout_margin="4dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="12dp"
        android:orientation="vertical">
        <!-- 你的内容 -->
        <TextView
            android:id="@+id/title"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="16sp"/>
    </LinearLayout>
</androidx.cardview.widget.CardView>
```

添加间距（ItemDecoration）：
```kotlin
class GridSpacingDecoration(
    private val spanCount: Int,
    private val spacing: Int,
    private val includeEdge: Boolean = true
) : RecyclerView.ItemDecoration() {
    override fun getItemOffsets(outRect: Rect, view: View, parent: RecyclerView, state: RecyclerView.State) {
        val position = parent.getChildAdapterPosition(view)
        val column = position % spanCount

        if (includeEdge) {
            outRect.left = spacing - column * spacing / spanCount
            outRect.right = (column + 1) * spacing / spanCount
            if (position < spanCount) outRect.top = spacing
            outRect.bottom = spacing
        } else {
            outRect.left = column * spacing / spanCount
            outRect.right = spacing - (column + 1) * spacing / spanCount
            if (position >= spanCount) outRect.top = spacing
        }
    }
}

// 使用
recyclerView.addItemDecoration(GridSpacingDecoration(spanCount = 2, spacing = dp(8)))
```

方案二：StaggeredGridLayoutManager（瀑布流）
- 如果每个 item 高度不一致且想要瀑布流效果，可以用：
```kotlin
recyclerView.layoutManager = StaggeredGridLayoutManager(2, RecyclerView.VERTICAL)
```
- 注意：默认会“填缝”导致列顺序看起来不严格按行排列；若你需要严格按行从左到右，不建议用这个方案。

方案三：自定义 LayoutManager（特殊需求）
- 当需要更复杂的对齐、分页、固定行高/列宽、整页滚动等，可自定义 LayoutManager。
- 成本较高，一般用不到。若仅仅是两列并按行从左到右，GridLayoutManager 足够。

常见注意点
- 保证 RecyclerView 的宽度是 match_parent，并且在父布局有确定的测量约束，否则网格分配可能不准确。
- 如果 item 想要等高，最好在布局里固定高度或使用约束计算，避免因 wrap_content 导致行高不一致。
- 如果在嵌套滚动容器中（如 NestedScrollView），尽量不要把 RecyclerView 放在可滚动父容器里，或禁用父容器滚动，否则性能和测量会有问题。
- 使用 DiffUtil 提升刷新性能；开启 setHasStableIds(true) 并提供稳定 ID 可减少闪烁。
- 如需横向两行而非纵向两列，可设置 orientation=RecyclerView.HORIZONTAL 并在 ItemDecoration 中控制行距。

总结
- 你要的效果（两列，按行从左到右排布）直接用 GridLayoutManager(spanCount=2) 即可，再加一个 ItemDecoration 控制间距，最简洁、性能最好。需要跨列时用 SpanSizeLookup。