*Thinking...*

> 用户想要一个Java版本的Android RecyclerView点击展开下拉详情功能的demo。我需要提供：
> 1. 数据模型类
> 2. RecyclerView Adapter
> 3. 布局文件
> 4. Activity主文件
> 5. 包含动画效果的展开/收起功能
> 
> 我应该用Java而不是Kotlin来编写代码。

我来为你演示如何用Java在Android RecyclerView中实现点击展开下拉详情功能。以下是完整的示例：

## 1. 数据模型类 (DataModel.java)

```java
public class DataModel {
    private int id;
    private String title;
    private String shortDescription;
    private String detailContent;
    private boolean isExpanded;

    public DataModel(int id, String title, String shortDescription, String detailContent) {
        this.id = id;
        this.title = title;
        this.shortDescription = shortDescription;
        this.detailContent = detailContent;
        this.isExpanded = false;
    }

    // Getter和Setter方法
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getShortDescription() {
        return shortDescription;
    }

    public void setShortDescription(String shortDescription) {
        this.shortDescription = shortDescription;
    }

    public String getDetailContent() {
        return detailContent;
    }

    public void setDetailContent(String detailContent) {
        this.detailContent = detailContent;
    }

    public boolean isExpanded() {
        return isExpanded;
    }

    public void setExpanded(boolean expanded) {
        isExpanded = expanded;
    }
}
```

## 2. RecyclerView Adapter (ExpandableAdapter.java)

```java
import android.animation.ValueAnimator;
import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.animation.DecelerateInterpolator;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class ExpandableAdapter extends RecyclerView.Adapter<ExpandableAdapter.ViewHolder> {
    
    private List<DataModel> dataList;
    private Context context;

    public ExpandableAdapter(Context context, List<DataModel> dataList) {
        this.context = context;
        this.dataList = dataList;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_expandable, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        DataModel item = dataList.get(position);
        
        // 设置数据
        holder.titleText.setText(item.getTitle());
        holder.shortDescText.setText(item.getShortDescription());
        holder.detailText.setText(item.getDetailContent());
        
        // 设置初始状态
        if (item.isExpanded()) {
            holder.detailLayout.setVisibility(View.VISIBLE);
            holder.expandIcon.setRotation(180f);
        } else {
            holder.detailLayout.setVisibility(View.GONE);
            holder.expandIcon.setRotation(0f);
        }
        
        // 点击事件
        holder.headerLayout.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // 获取当前位置
                int currentPosition = holder.getAdapterPosition();
                if (currentPosition != RecyclerView.NO_POSITION) {
                    DataModel currentItem = dataList.get(currentPosition);
                    
                    // 切换展开状态
                    currentItem.setExpanded(!currentItem.isExpanded());
                    
                    // 执行动画
                    if (currentItem.isExpanded()) {
                        expandView(holder.detailLayout, holder.expandIcon);
                    } else {
                        collapseView(holder.detailLayout, holder.expandIcon);
                    }
                }
            }
        });
    }

    @Override
    public int getItemCount() {
        return dataList.size();
    }

    // ViewHolder类
    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView titleText;
        TextView shortDescText;
        LinearLayout detailLayout;
        TextView detailText;
        ImageView expandIcon;
        LinearLayout headerLayout;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            titleText = itemView.findViewById(R.id.tv_title);
            shortDescText = itemView.findViewById(R.id.tv_short_desc);
            detailLayout = itemView.findViewById(R.id.layout_detail);
            detailText = itemView.findViewById(R.id.tv_detail);
            expandIcon = itemView.findViewById(R.id.iv_expand);
            headerLayout = itemView.findViewById(R.id.layout_header);
        }
    }

    // 展开动画
    private void expandView(final View view, final ImageView arrow) {
        view.setVisibility(View.VISIBLE);
        view.measure(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        final int targetHeight = view.getMeasuredHeight();

        view.getLayoutParams().height = 0;
        view.requestLayout();

        ValueAnimator animator = ValueAnimator.ofInt(0, targetHeight);
        animator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                view.getLayoutParams().height = (int) animation.getAnimatedValue();
                view.requestLayout();
            }
        });
        animator.setInterpolator(new DecelerateInterpolator());
        animator.setDuration(300);
        animator.start();

        // 旋转箭头
        arrow.animate().rotation(180f).setDuration(300).start();
    }

    // 收起动画
    private void collapseView(final View view, final ImageView arrow) {
        final int initialHeight = view.getMeasuredHeight();

        ValueAnimator animator = ValueAnimator.ofInt(initialHeight, 0);
        animator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                view.getLayoutParams().height = (int) animation.getAnimatedValue();
                view.requestLayout();
                
                if ((int) animation.getAnimatedValue() == 0) {
                    view.setVisibility(View.GONE);
                }
            }
        });
        animator.setInterpolator(new DecelerateInterpolator());
        animator.setDuration(300);
        animator.start();

        // 旋转箭头
        arrow.animate().rotation(0f).setDuration(300).start();
    }
}
```

## 3. Item布局文件 (item_expandable.xml)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:layout_margin="8dp">

    <androidx.cardview.widget.CardView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:elevation="4dp"
        app:cardCornerRadius="8dp"
        xmlns:app="http://schemas.android.com/apk/res-auto">

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical">

            <!-- 头部区域（可点击） -->
            <LinearLayout
                android:id="@+id/layout_header"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:padding="16dp"
                android:background="?attr/selectableItemBackground"
                android:clickable="true"
                android:focusable="true">

                <LinearLayout
                    android:layout_width="0dp"
                    android:layout_height="wrap_content"
                    android:layout_weight="1"
                    android:orientation="vertical">

                    <TextView
                        android:id="@+id/tv_title"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="标题"
                        android:textSize="18sp"
                        android:textStyle="bold"
                        android:textColor="#333333" />

                    <TextView
                        android:id="@+id/tv_short_desc"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:layout_marginTop="4dp"
                        android:text="简短描述"
                        android:textSize="14sp"
                        android:textColor="#666666" />

                </LinearLayout>

                <ImageView
                    android:id="@+id/iv_expand"
                    android:layout_width="24dp"
                    android:layout_height="24dp"
                    android:layout_gravity="center_vertical"
                    android:src="@drawable/ic_expand_more"
                    android:tint="#666666" />

            </LinearLayout>

            <!-- 分割线 -->
            <View
                android:layout_width="match_parent"
                android:layout_height="1dp"
                android:background="#E0E0E0" />

            <!-- 详情区域（展开/收起） -->
            <LinearLayout
                android:id="@+id/layout_detail"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp"
                android:visibility="gone">

                <TextView
                    android:id="@+id/tv_detail"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="详细内容"
                    android:textSize="14sp"
                    android:textColor="#444444"
                    android:lineSpacingExtra="4dp" />

            </LinearLayout>

        </LinearLayout>

    </androidx.cardview.widget.CardView>

</LinearLayout>
```

## 4. 主Activity (MainActivity.java)

```java
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    private RecyclerView recyclerView;
    private ExpandableAdapter adapter;
    private List<DataModel> dataList;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // 初始化视图
        recyclerView = findViewById(R.id.recyclerView);
        
        // 准备数据
        prepareData();
        
        // 设置RecyclerView
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        adapter = new ExpandableAdapter(this, dataList);
        recyclerView.setAdapter(adapter);
        
        // 可选：添加item动画
        recyclerView.setItemAnimator(new DefaultItemAnimator());
    }

    private void prepareData() {
        dataList = new ArrayList<>();
        
        dataList.add(new DataModel(1, 
            "Android开发", 
            "原生Android应用开发技术", 
            "Android是一个基于Linux内核的开源移动操作系统，主要用于触摸屏移动设备。" +
            "Android开发通常使用Java或Kotlin编程语言，配合Android SDK进行应用开发。" +
            "开发工具主要是Android Studio，它提供了完整的开发环境。"));
        
        dataList.add(new DataModel(2, 
            "RecyclerView", 
            "高效的列表展示组件", 
            "RecyclerView是Android中用于展示大量数据集的高级组件。" +
            "它通过回收和重用视图来提高性能，支持多种布局管理器，" +
            "包括线性布局、网格布局和瀑布流布局。还支持动画和装饰器。"));
        
        dataList.add(new DataModel(3, 
            "Material Design", 
            "Google的设计语言", 
            "Material Design是Google开发的设计语言，强调纸张和墨水的隐喻。" +
            "它提供了一套完整的设计规范，包括颜色、字体、形状、动画等。" +
            "Material Design让应用看起来更加美观和统一。"));
        
        dataList.add(new DataModel(4, 
            "Jetpack Compose", 
            "声明式UI框架", 
            "Jetpack Compose是Android的现代化声明式UI工具包。" +
            "它简化了UI开发，使用Kotlin编程语言，通过更少的代码实现更多功能。" +
            "Compose提供了直观的API，让UI开发变得更加简单和高效。"));
    }
}
```

## 5. 主布局文件 (activity_main.xml)

```xml
<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#F5F5F5">

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerView"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:padding="8dp"
        android:clipToPadding="false" />

</RelativeLayout>
```

## 6. 展开图标 (ic_expand_more.xml)

在 `res/drawable` 目录下创建：

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FF000000"
        android:pathData="M16.59,8.59L12,13.17 7.41,8.59 6,10l6,6 6,-6z"/>
</vector>
```

## 使用说明

1. 将以上代码复制到对应的文件中
2. 确保在 `build.gradle` 中添加了 RecyclerView 和 CardView 依赖：

```gradle
dependencies {
    implementation 'androidx.recyclerview:recyclerview:1.2.1'
    implementation 'androidx.cardview:cardview:1.0.0'
}
```

3. 运行应用，点击列表项即可看到展开/收起的动画效果

这个示例实现了：
- 点击item展开显示详细内容
- 平滑的展开/收起动画
- 箭头图标旋转指示状态
- 使用CardView实现卡片式设计
- 支持多个item同时展开