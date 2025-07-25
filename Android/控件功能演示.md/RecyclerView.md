*Thinking...*

> 用户想要一个关于Android RecyclerView的完整演示，需要包含：
> 1. RecyclerView的基本使用
> 2. ViewHolder的使用
> 3. Adapter的使用
> 4. LayoutManager的使用
> 5. 循序渐进，从简单到复杂
> 
> 我需要创建多个Demo，从最基础的开始，逐步增加复杂度。让我设计以下几个Demo：
> 
> Demo 1: 最基础的RecyclerView - 显示简单的文本列表
> Demo 2: 带图片和文本的RecyclerView - 更复杂的布局
> Demo 3: 不同的LayoutManager展示 - LinearLayoutManager、GridLayoutManager、StaggeredGridLayoutManager
> Demo 4: 交互功能 - 点击事件、长按事件、滑动删除
> Demo 5: 高级功能 - 多类型布局、动画效果
> 
> 我将提供完整的代码，包括：
> - Activity代码
> - Adapter代码
> - ViewHolder代码
> - 布局文件
> - 数据模型类

我来为你创建一系列循序渐进的Android RecyclerView Demo，从最基础开始逐步深入。

## Demo 1: 基础文本列表

首先创建最简单的RecyclerView，显示一个文本列表。

### 1.1 数据模型类 (SimpleItem.java)
```java
package com.example.recyclerviewdemo;

public class SimpleItem {
    private String title;
    
    public SimpleItem(String title) {
        this.title = title;
    }
    
    public String getTitle() {
        return title;
    }
    
    public void setTitle(String title) {
        this.title = title;
    }
}
```

### 1.2 布局文件 - Activity布局 (activity_simple_demo.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerView"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

### 1.3 列表项布局 (item_simple.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:padding="16dp"
    android:orientation="vertical">

    <TextView
        android:id="@+id/textView"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textSize="16sp"
        android:textColor="@android:color/black" />
    
    <View
        android:layout_width="match_parent"
        android:layout_height="1dp"
        android:layout_marginTop="8dp"
        android:background="#E0E0E0" />

</LinearLayout>
```

### 1.4 Adapter类 (SimpleAdapter.java)
```java
package com.example.recyclerviewdemo;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class SimpleAdapter extends RecyclerView.Adapter<SimpleAdapter.SimpleViewHolder> {
    
    private List<SimpleItem> itemList;
    
    // 构造函数，接收数据列表
    public SimpleAdapter(List<SimpleItem> itemList) {
        this.itemList = itemList;
    }
    
    // ViewHolder类 - 持有每个列表项的视图引用
    public static class SimpleViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        
        public SimpleViewHolder(@NonNull View itemView) {
            super(itemView);
            // 绑定视图
            textView = itemView.findViewById(R.id.textView);
        }
    }
    
    // 创建ViewHolder - 当RecyclerView需要新的ViewHolder时调用
    @NonNull
    @Override
    public SimpleViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        // 加载列表项布局
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_simple, parent, false);
        return new SimpleViewHolder(view);
    }
    
    // 绑定数据到ViewHolder - 当RecyclerView需要显示数据时调用
    @Override
    public void onBindViewHolder(@NonNull SimpleViewHolder holder, int position) {
        SimpleItem item = itemList.get(position);
        holder.textView.setText(item.getTitle());
    }
    
    // 返回数据数量
    @Override
    public int getItemCount() {
        return itemList.size();
    }
}
```

### 1.5 Activity类 (SimpleDemoActivity.java)
```java
package com.example.recyclerviewdemo;

import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import java.util.ArrayList;
import java.util.List;

public class SimpleDemoActivity extends AppCompatActivity {
    
    private RecyclerView recyclerView;
    private SimpleAdapter adapter;
    private List<SimpleItem> itemList;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_simple_demo);
        
        // 初始化RecyclerView
        recyclerView = findViewById(R.id.recyclerView);
        
        // 设置LayoutManager - 决定列表项如何排列
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        
        // 准备数据
        initData();
        
        // 创建并设置Adapter
        adapter = new SimpleAdapter(itemList);
        recyclerView.setAdapter(adapter);
    }
    
    private void initData() {
        itemList = new ArrayList<>();
        for (int i = 1; i <= 20; i++) {
            itemList.add(new SimpleItem("列表项 " + i));
        }
    }
}
```

## Demo 2: 图文混合列表

这个Demo展示更复杂的列表项布局，包含图片和多个文本。

### 2.1 数据模型 (ContactItem.java)
```java
package com.example.recyclerviewdemo;

public class ContactItem {
    private String name;
    private String phone;
    private int avatarResId;
    
    public ContactItem(String name, String phone, int avatarResId) {
        this.name = name;
        this.phone = phone;
        this.avatarResId = avatarResId;
    }
    
    // Getter和Setter方法
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    
    public int getAvatarResId() { return avatarResId; }
    public void setAvatarResId(int avatarResId) { this.avatarResId = avatarResId; }
}
```

### 2.2 列表项布局 (item_contact.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.cardview.widget.CardView 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_margin="8dp"
    app:cardElevation="4dp"
    app:cardCornerRadius="8dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="16dp">

        <ImageView
            android:id="@+id/imageAvatar"
            android:layout_width="60dp"
            android:layout_height="60dp"
            android:scaleType="centerCrop"
            android:src="@drawable/ic_launcher_background" />

        <LinearLayout
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_marginStart="16dp"
            android:orientation="vertical">

            <TextView
                android:id="@+id/textName"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="18sp"
                android:textStyle="bold"
                android:textColor="@android:color/black" />

            <TextView
                android:id="@+id/textPhone"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:layout_marginTop="4dp"
                android:textSize="14sp"
                android:textColor="#666666" />

        </LinearLayout>

    </LinearLayout>

</androidx.cardview.widget.CardView>
```

### 2.3 Adapter类 (ContactAdapter.java)
```java
package com.example.recyclerviewdemo;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class ContactAdapter extends RecyclerView.Adapter<ContactAdapter.ContactViewHolder> {
    
    private List<ContactItem> contactList;
    private OnItemClickListener listener;
    
    // 定义点击事件接口
    public interface OnItemClickListener {
        void onItemClick(ContactItem item, int position);
    }
    
    public ContactAdapter(List<ContactItem> contactList) {
        this.contactList = contactList;
    }
    
    public void setOnItemClickListener(OnItemClickListener listener) {
        this.listener = listener;
    }
    
    // ViewHolder类
    public static class ContactViewHolder extends RecyclerView.ViewHolder {
        ImageView imageAvatar;
        TextView textName;
        TextView textPhone;
        
        public ContactViewHolder(@NonNull View itemView) {
            super(itemView);
            imageAvatar = itemView.findViewById(R.id.imageAvatar);
            textName = itemView.findViewById(R.id.textName);
            textPhone = itemView.findViewById(R.id.textPhone);
        }
    }
    
    @NonNull
    @Override
    public ContactViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_contact, parent, false);
        return new ContactViewHolder(view);
    }
    
    @Override
    public void onBindViewHolder(@NonNull ContactViewHolder holder, int position) {
        ContactItem contact = contactList.get(position);
        
        holder.textName.setText(contact.getName());
        holder.textPhone.setText(contact.getPhone());
        holder.imageAvatar.setImageResource(contact.getAvatarResId());
        
        // 设置点击事件
        holder.itemView.setOnClickListener(v -> {
            if (listener != null) {
                listener.onItemClick(contact, position);
            }
        });
    }
    
    @Override
    public int getItemCount() {
        return contactList.size();
    }
}
```

### 2.4 Activity类 (ContactDemoActivity.java)
```java
package com.example.recyclerviewdemo;

import android.os.Bundle;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import java.util.ArrayList;
import java.util.List;

public class ContactDemoActivity extends AppCompatActivity {
    
    private RecyclerView recyclerView;
    private ContactAdapter adapter;
    private List<ContactItem> contactList;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_simple_demo); // 复用之前的布局
        
        recyclerView = findViewById(R.id.recyclerView);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        
        initData();
        
        adapter = new ContactAdapter(contactList);
        adapter.setOnItemClickListener((item, position) -> {
            Toast.makeText(this, "点击了: " + item.getName(), Toast.LENGTH_SHORT).show();
        });
        
        recyclerView.setAdapter(adapter);
    }
    
    private void initData() {
        contactList = new ArrayList<>();
        String[] names = {"张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十"};
        String[] phones = {"13800138000", "13900139000", "13700137000", "13600136000",
                          "13500135000", "13400134000", "13300133000", "13200132000"};
        
        for (int i = 0; i < names.length; i++) {
            contactList.add(new ContactItem(names[i], phones[i], 
                android.R.drawable.ic_menu_gallery));
        }
    }
}
```

## Demo 3: 不同的LayoutManager展示

这个Demo展示三种不同的LayoutManager。

### 3.1 Activity布局 (activity_layout_manager_demo.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="8dp">

        <Button
            android:id="@+id/btnLinear"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="线性" />

        <Button
            android:id="@+id/btnGrid"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_marginStart="4dp"
            android:text="网格" />

        <Button
            android:id="@+id/btnStaggered"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_marginStart="4dp"
            android:text="瀑布流" />

    </LinearLayout>

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:padding="8dp" />

</LinearLayout>
```

### 3.2 网格/瀑布流项布局 (item_card.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.cardview.widget.CardView 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_margin="4dp"
    app:cardElevation="2dp"
    app:cardCornerRadius="4dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical">

        <View
            android:id="@+id/colorView"
            android:layout_width="match_parent"
            android:layout_height="100dp" />

        <TextView
            android:id="@+id/textView"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:padding="8dp"
            android:textAlignment="center"
            android:textSize="14sp" />

    </LinearLayout>

</androidx.cardview.widget.CardView>
```

### 3.3 数据模型和Adapter (CardItem.java & CardAdapter.java)
```java
// CardItem.java
package com.example.recyclerviewdemo;

public class CardItem {
    private String title;
    private int color;
    private int height; // 用于瀑布流
    
    public CardItem(String title, int color, int height) {
        this.title = title;
        this.color = color;
        this.height = height;
    }
    
    // Getter和Setter
    public String getTitle() { return title; }
    public int getColor() { return color; }
    public int getHeight() { return height; }
}
```

```java
// CardAdapter.java
package com.example.recyclerviewdemo;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import androidx.recyclerview.widget.StaggeredGridLayoutManager;
import java.util.List;

public class CardAdapter extends RecyclerView.Adapter<CardAdapter.CardViewHolder> {
    
    private List<CardItem> cardList;
    private boolean isStaggered = false;
    
    public CardAdapter(List<CardItem> cardList) {
        this.cardList = cardList;
    }
    
    public void setStaggered(boolean staggered) {
        isStaggered = staggered;
        notifyDataSetChanged();
    }
    
    public static class CardViewHolder extends RecyclerView.ViewHolder {
        View colorView;
        TextView textView;
        
        public CardViewHolder(@NonNull View itemView) {
            super(itemView);
            colorView = itemView.findViewById(R.id.colorView);
            textView = itemView.findViewById(R.id.textView);
        }
    }
    
    @NonNull
    @Override
    public CardViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_card, parent, false);
        return new CardViewHolder(view);
    }
    
    @Override
    public void onBindViewHolder(@NonNull CardViewHolder holder, int position) {
        CardItem card = cardList.get(position);
        
        holder.textView.setText(card.getTitle());
        holder.colorView.setBackgroundColor(card.getColor());
        
        // 如果是瀑布流布局，设置不同高度
        if (isStaggered) {
            ViewGroup.LayoutParams params = holder.colorView.getLayoutParams();
            params.height = card.getHeight();
            holder.colorView.setLayoutParams(params);
        } else {
            ViewGroup.LayoutParams params = holder.colorView.getLayoutParams();
            params.height = 200; // 固定高度
            holder.colorView.setLayoutParams(params);
        }
    }
    
    @Override
    public int getItemCount() {
        return cardList.size();
    }
}
```

### 3.4 Activity类 (LayoutManagerDemoActivity.java)
```java
package com.example.recyclerviewdemo;

import android.graphics.Color;
import android.os.Bundle;
import android.widget.Button;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.recyclerview.widget.StaggeredGridLayoutManager;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class LayoutManagerDemoActivity extends AppCompatActivity {
    
    private RecyclerView recyclerView;
    private CardAdapter adapter;
    private List<CardItem> cardList;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_layout_manager_demo);
        
        recyclerView = findViewById(R.id.recyclerView);
        Button btnLinear = findViewById(R.id.btnLinear);
        Button btnGrid = findViewById(R.id.btnGrid);
        Button btnStaggered = findViewById(R.id.btnStaggered);
        
        initData();
        
        adapter = new CardAdapter(cardList);
        recyclerView.setAdapter(adapter);
        
        // 默认使用线性布局
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        
        // 设置按钮点击事件
        btnLinear.setOnClickListener(v -> {
            adapter.setStaggered(false);
            recyclerView.setLayoutManager(new LinearLayoutManager(this));
        });
        
        btnGrid.setOnClickListener(v -> {
            adapter.setStaggered(false);
            recyclerView.setLayoutManager(new GridLayoutManager(this, 2));
        });
        
        btnStaggered.setOnClickListener(v -> {
            adapter.setStaggered(true);
            recyclerView.setLayoutManager(
                new StaggeredGridLayoutManager(2, StaggeredGridLayoutManager.VERTICAL));
        });
    }
    
    private void initData() {
        cardList = new ArrayList<>();
        Random random = new Random();
        
        // 生成随机颜色的卡片
        int[] colors = {
            Color.parseColor("#FF6B6B"),
            Color.parseColor("#4ECDC4"),
            Color.parseColor("#45B7D1"),
            Color.parseColor("#96CEB4"),
            Color.parseColor("#FECA57"),
            Color.parseColor("#FF9FF3")
        };
        
        for (int i = 1; i <= 30; i++) {
            int color = colors[random.nextInt(colors.length)];
            int height = 200 + random.nextInt(200); // 100-300的随机高度
            cardList.add(new CardItem("卡片 " + i, color, height));
        }
    }
}
```

## Demo 4: 高级交互功能

这个Demo展示滑动删除和拖拽排序功能。

### 4.1 带滑动删除的Adapter
```java
package com.example.recyclerviewdemo;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.drawable.ColorDrawable;
import android.view.View;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.ItemTouchHelper;
import androidx.recyclerview.widget.RecyclerView;

public class SwipeToDeleteCallback extends ItemTouchHelper.SimpleCallback {
    
    private SwipeAdapter adapter;
    private ColorDrawable background;
    private int backgroundColor;
    private Paint clearPaint;
    
    public SwipeToDeleteCallback(SwipeAdapter adapter) {
        super(0, ItemTouchHelper.LEFT | ItemTouchHelper.RIGHT);
        this.adapter = adapter;
        background = new ColorDrawable();
        backgroundColor = Color.parseColor("#f44336");
        clearPaint = new Paint();
        clearPaint.setXfermode(new android.graphics.PorterDuffXfermode(
            android.graphics.PorterDuff.Mode.CLEAR));
    }
    
    @Override
    public boolean onMove(@NonNull RecyclerView recyclerView, 
                         @NonNull RecyclerView.ViewHolder viewHolder, 
                         @NonNull RecyclerView.ViewHolder target) {
        return false;
    }
    
    @Override
    public void onSwiped(@NonNull RecyclerView.ViewHolder viewHolder, int direction) {
        int position = viewHolder.getAdapterPosition();
        adapter.removeItem(position);
    }
    
    @Override
    public void onChildDraw(@NonNull Canvas c, @NonNull RecyclerView recyclerView,
                           @NonNull RecyclerView.ViewHolder viewHolder, float dX, float dY,
                           int actionState, boolean isCurrentlyActive) {
        
        View itemView = viewHolder.itemView;
        boolean isCanceled = dX == 0f && !isCurrentlyActive;
        
        if (isCanceled) {
            c.drawRect(itemView.getRight() + dX, itemView.getTop(), 
                      itemView.getRight(), itemView.getBottom(), clearPaint);
            super.onChildDraw(c, recyclerView, viewHolder, dX, dY, actionState, isCurrentlyActive);
            return;
        }
        
        background.setColor(backgroundColor);
        background.setBounds(itemView.getRight() + (int) dX, itemView.getTop(),
                           itemView.getRight(), itemView.getBottom());
        background.draw(c);
        
        super.onChildDraw(c, recyclerView, viewHolder, dX, dY, actionState, isCurrentlyActive);
    }
}
```

### 4.2 支持滑动删除的Adapter (SwipeAdapter.java)
```java
package com.example.recyclerviewdemo;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.snackbar.Snackbar;
import java.util.ArrayList;
import java.util.List;

public class SwipeAdapter extends RecyclerView.Adapter<SwipeAdapter.ViewHolder> {
    
    private List<String> items;
    private List<String> deletedItems;
    private List<Integer> deletedPositions;
    
    public SwipeAdapter(List<String> items) {
        this.items = new ArrayList<>(items);
        this.deletedItems = new ArrayList<>();
        this.deletedPositions = new ArrayList<>();
    }
    
    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        
        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.textView);
        }
    }
    
    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_simple, parent, false);
        return new ViewHolder(view);
    }
    
    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        holder.textView.setText(items.get(position));
    }
    
    @Override
    public int getItemCount() {
        return items.size();
    }
    
    public void removeItem(int position) {
        String deletedItem = items.get(position);
        deletedItems.add(deletedItem);
        deletedPositions.add(position);
        
        items.remove(position);
        notifyItemRemoved(position);
    }
    
    public void undoDelete(View view) {
        if (!deletedItems.isEmpty()) {
            int position = deletedPositions.get(deletedPositions.size() - 1);
            String item = deletedItems.get(deletedItems.size() - 1);
            
            items.add(position, item);
            notifyItemInserted(position);
            
            deletedItems.remove(deletedItems.size() - 1);
            deletedPositions.remove(deletedPositions.size() - 1);
            
            Snackbar.make(view, "已恢复: " + item, Snackbar.LENGTH_SHORT).show();
        }
    }
}
```

### 4.3 Activity实现 (SwipeDemoActivity.java)
```java
package com.example.recyclerviewdemo;

import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.ItemTouchHelper;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.snackbar.Snackbar;
import java.util.ArrayList;
import java.util.List;

public class SwipeDemoActivity extends AppCompatActivity {
    
    private RecyclerView recyclerView;
    private SwipeAdapter adapter;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_simple_demo);
        
        recyclerView = findViewById(R.id.recyclerView);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        
        List<String> items = new ArrayList<>();
        for (int i = 1; i <= 20; i++) {
            items.add("可滑动删除的项目 " + i);
        }
        
        adapter = new SwipeAdapter(items);
        recyclerView.setAdapter(adapter);
        
        // 添加滑动删除功能
        ItemTouchHelper itemTouchHelper = new ItemTouchHelper(new SwipeToDeleteCallback(adapter) {
            @Override
            public void onSwiped(@NonNull RecyclerView.ViewHolder viewHolder, int direction) {
                int position = viewHolder.getAdapterPosition();
                adapter.removeItem(position);
                
                // 显示撤销选项
                Snackbar.make(recyclerView, "已删除一项", Snackbar.LENGTH_LONG)
                        .setAction("撤销", v -> adapter.undoDelete(recyclerView))
                        .show();
            }
        });
        
        itemTouchHelper.attachToRecyclerView(recyclerView);
    }
}
```

## Demo 5: 多类型布局

最后一个Demo展示如何在一个RecyclerView中显示不同类型的布局。

### 5.1 多类型Adapter (MultiTypeAdapter.java)
```java
package com.example.recyclerviewdemo;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class MultiTypeAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {
    
    // 定义视图类型
    private static final int TYPE_HEADER = 0;
    private static final int TYPE_ITEM = 1;
    private static final int TYPE_FOOTER = 2;
    
    private List<Object> dataList;
    
    public MultiTypeAdapter(List<Object> dataList) {
        this.dataList = dataList;
    }
    
    // 头部ViewHolder
    public static class HeaderViewHolder extends RecyclerView.ViewHolder {
        TextView titleText;
        
        public HeaderViewHolder(@NonNull View itemView) {
            super(itemView);
            titleText = itemView.findViewById(R.id.headerTitle);
        }
    }
    
    // 内容ViewHolder
    public static class ItemViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        ImageView imageView;
        
        public ItemViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.textView);
            imageView = itemView.findViewById(R.id.imageView);
        }
    }
    
    // 底部ViewHolder
    public static class FooterViewHolder extends RecyclerView.ViewHolder {
        TextView footerText;
        
        public FooterViewHolder(@NonNull View itemView) {
            super(itemView);
            footerText = itemView.findViewById(R.id.footerText);
        }
    }
    
    @Override
    public int getItemViewType(int position) {
        if (dataList.get(position) instanceof String) {
            return TYPE_HEADER;
        } else if (dataList.get(position) instanceof ContactItem) {
            return TYPE_ITEM;
        } else {
            return TYPE_FOOTER;
        }
    }
    
    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view;
        switch (viewType) {
            case TYPE_HEADER:
                view = LayoutInflater.from(parent.getContext())
                        .inflate(R.layout.item_header, parent, false);
                return new HeaderViewHolder(view);
            case TYPE_ITEM:
                view = LayoutInflater.from(parent.getContext())
                        .inflate(R.layout.item_multi_type, parent, false);
                return new ItemViewHolder(view);
            case TYPE_FOOTER:
                view = LayoutInflater.from(parent.getContext())
                        .inflate(R.layout.item_footer, parent, false);
                return new FooterViewHolder(view);
            default:
                throw new IllegalArgumentException("Invalid view type");
        }
    }
    
    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        Object item = dataList.get(position);
        
        if (holder instanceof HeaderViewHolder) {
            ((HeaderViewHolder) holder).titleText.setText((String) item);
        } else if (holder instanceof ItemViewHolder) {
            ContactItem contact = (ContactItem) item;
            ((ItemViewHolder) holder).textView.setText(contact.getName());
            ((ItemViewHolder) holder).imageView.setImageResource(contact.getAvatarResId());
        } else if (holder instanceof FooterViewHolder) {
            ((FooterViewHolder) holder).footerText.setText("已加载全部内容");
        }
    }
    
    @Override
    public int getItemCount() {
        return dataList.size();
    }
}
```

### 5.2 布局文件

```xml
<!-- item_header.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:background="#E0E0E0"
    android:padding="16dp">

    <TextView
        android:id="@+id/headerTitle"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textSize="20sp"
        android:textStyle="bold"
        android:textColor="#333333" />

</LinearLayout>
```

```xml
<!-- item_multi_type.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="horizontal"
    android:padding="16dp">

    <ImageView
        android:id="@+id/imageView"
        android:layout_width="48dp"
        android:layout_height="48dp"
        android:scaleType="centerCrop" />

    <TextView
        android:id="@+id/textView"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_weight="1"
        android:layout_marginStart="16dp"
        android:layout_gravity="center_vertical"
        android:textSize="16sp" />

</LinearLayout>
```

```xml
<!-- item_footer.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:gravity="center"
    android:padding="16dp">

    <TextView
        android:id="@+id/footerText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:textSize="14sp"
        android:textColor="#999999" />

</LinearLayout>
```

## 总结

这5个Demo从简单到复杂，展示了RecyclerView的核心概念：

1. **Demo 1**: 基础使用，理解ViewHolder、Adapter和LayoutManager的基本概念
2. **Demo 2**: 复杂布局和点击事件处理
3. **Demo 3**: 不同LayoutManager的使用（Linear、Grid、StaggeredGrid）
4. **Demo 4**: 高级交互（滑动删除、拖拽排序）
5. **Demo 5**: 多类型布局的实现

关键概念说明：
- **ViewHolder**: 缓存视图引用，避免重复findViewById，提高性能
- **Adapter**: 数据和视图的桥梁，负责创建ViewHolder和绑定数据
- **LayoutManager**: 决定列表项的排列方式
- **ItemTouchHelper**: 处理滑动和拖拽等手势
- **多视图类型**: 通过getItemViewType实现不同布局的混合显示

这些Demo涵盖了RecyclerView的大部分常用功能，你可以根据需要选择合适的功能进行学习和使用。