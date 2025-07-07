*Thinking...*

> 用户想要一个Android原生应用的Demo，而不是React模拟的。我需要创建一个完整的Android应用代码，包括：
> 1. MainActivity.java - 主要的Activity代码
> 2. activity_main.xml - 布局文件
> 3. 可能需要的其他资源文件
> 
> 我应该展示CheckBox的所有主要功能：
> - 基本使用
> - 监听器
> - 状态改变
> - 启用/禁用
> - 自定义样式
> - 分组使用
> - 与其他组件交互
> - 三态复选框（虽然Android原生不直接支持，但可以模拟）
> - 编程方式控制
> - 属性设置
> 
> 我需要提供完整的代码，不能使用省略。

我将为您创建一个完整的Android原生应用Demo，展示CheckBox的所有功能。这个Demo包含了MainActivity和布局文件。

## MainActivity.java

```java
package com.example.checkboxdemo;

import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    
    // 基本复选框
    private CheckBox checkBoxBasic;
    private TextView textViewBasicStatus;
    
    // 监听器演示
    private CheckBox checkBoxListener;
    private TextView textViewEventLog;
    private StringBuilder eventLog = new StringBuilder();
    
    // 禁用状态
    private CheckBox checkBoxDisabledChecked;
    private CheckBox checkBoxDisabledUnchecked;
    private Button buttonToggleEnabled;
    
    // 自定义样式
    private CheckBox checkBoxCustom1;
    private CheckBox checkBoxCustom2;
    private CheckBox checkBoxCustom3;
    
    // 分组复选框
    private CheckBox checkBoxSelectAll;
    private List<CheckBox> groupCheckBoxes = new ArrayList<>();
    private LinearLayout layoutGroupItems;
    
    // 功能演示
    private CheckBox checkBoxFeature1;
    private CheckBox checkBoxFeature2;
    private CheckBox checkBoxFeature3;
    private Button buttonGetSelected;
    private TextView textViewSelected;
    
    // 编程控制
    private CheckBox checkBoxProgrammatic;
    private Button buttonCheck;
    private Button buttonUncheck;
    private Button buttonToggle;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        setupListeners();
        setupGroupCheckBoxes();
        applyCustomStyles();
    }
    
    private void initViews() {
        // 基本复选框
        checkBoxBasic = findViewById(R.id.checkBoxBasic);
        textViewBasicStatus = findViewById(R.id.textViewBasicStatus);
        
        // 监听器演示
        checkBoxListener = findViewById(R.id.checkBoxListener);
        textViewEventLog = findViewById(R.id.textViewEventLog);
        
        // 禁用状态
        checkBoxDisabledChecked = findViewById(R.id.checkBoxDisabledChecked);
        checkBoxDisabledUnchecked = findViewById(R.id.checkBoxDisabledUnchecked);
        buttonToggleEnabled = findViewById(R.id.buttonToggleEnabled);
        
        // 自定义样式
        checkBoxCustom1 = findViewById(R.id.checkBoxCustom1);
        checkBoxCustom2 = findViewById(R.id.checkBoxCustom2);
        checkBoxCustom3 = findViewById(R.id.checkBoxCustom3);
        
        // 分组复选框
        checkBoxSelectAll = findViewById(R.id.checkBoxSelectAll);
        layoutGroupItems = findViewById(R.id.layoutGroupItems);
        
        // 功能演示
        checkBoxFeature1 = findViewById(R.id.checkBoxFeature1);
        checkBoxFeature2 = findViewById(R.id.checkBoxFeature2);
        checkBoxFeature3 = findViewById(R.id.checkBoxFeature3);
        buttonGetSelected = findViewById(R.id.buttonGetSelected);
        textViewSelected = findViewById(R.id.textViewSelected);
        
        // 编程控制
        checkBoxProgrammatic = findViewById(R.id.checkBoxProgrammatic);
        buttonCheck = findViewById(R.id.buttonCheck);
        buttonUncheck = findViewById(R.id.buttonUncheck);
        buttonToggle = findViewById(R.id.buttonToggle);
    }
    
    private void setupListeners() {
        // 基本复选框监听器
        checkBoxBasic.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                textViewBasicStatus.setText("状态: " + (isChecked ? "已选中" : "未选中"));
            }
        });
        
        // 详细事件监听器
        checkBoxListener.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                addEventLog("onCheckedChanged: " + isChecked);
            }
        });
        
        checkBoxListener.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addEventLog("onClick被触发");
            }
        });
        
        // 启用/禁用切换
        buttonToggleEnabled.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                boolean newEnabled = !checkBoxDisabledChecked.isEnabled();
                checkBoxDisabledChecked.setEnabled(newEnabled);
                checkBoxDisabledUnchecked.setEnabled(newEnabled);
                buttonToggleEnabled.setText(newEnabled ? "禁用" : "启用");
                Toast.makeText(MainActivity.this, 
                    newEnabled ? "复选框已启用" : "复选框已禁用", 
                    Toast.LENGTH_SHORT).show();
            }
        });
        
        // 全选复选框
        checkBoxSelectAll.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                for (CheckBox cb : groupCheckBoxes) {
                    cb.setChecked(isChecked);
                }
            }
        });
        
        // 获取选中项按钮
        buttonGetSelected.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                StringBuilder selected = new StringBuilder("选中的项目:\n");
                if (checkBoxFeature1.isChecked()) selected.append("- WiFi\n");
                if (checkBoxFeature2.isChecked()) selected.append("- 蓝牙\n");
                if (checkBoxFeature3.isChecked()) selected.append("- GPS\n");
                
                if (selected.toString().equals("选中的项目:\n")) {
                    selected.append("(没有选中任何项目)");
                }
                
                textViewSelected.setText(selected.toString());
            }
        });
        
        // 编程控制按钮
        buttonCheck.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                checkBoxProgrammatic.setChecked(true);
                Toast.makeText(MainActivity.this, "已通过代码选中", Toast.LENGTH_SHORT).show();
            }
        });
        
        buttonUncheck.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                checkBoxProgrammatic.setChecked(false);
                Toast.makeText(MainActivity.this, "已通过代码取消选中", Toast.LENGTH_SHORT).show();
            }
        });
        
        buttonToggle.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                checkBoxProgrammatic.toggle();
                Toast.makeText(MainActivity.this, "已切换状态", Toast.LENGTH_SHORT).show();
            }
        });
    }
    
    private void setupGroupCheckBoxes() {
        String[] items = {"选项 1", "选项 2", "选项 3", "选项 4"};
        
        for (int i = 0; i < items.length; i++) {
            CheckBox checkBox = new CheckBox(this);
            checkBox.setText(items[i]);
            checkBox.setTextSize(16);
            checkBox.setPadding(0, 8, 0, 8);
            
            // 为分组中的每个复选框添加监听器
            checkBox.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
                @Override
                public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                    updateSelectAllState();
                }
            });
            
            layoutGroupItems.addView(checkBox);
            groupCheckBoxes.add(checkBox);
        }
        
        // 设置初始状态
        groupCheckBoxes.get(1).setChecked(true);
    }
    
    private void updateSelectAllState() {
        int checkedCount = 0;
        for (CheckBox cb : groupCheckBoxes) {
            if (cb.isChecked()) checkedCount++;
        }
        
        // 防止触发监听器的递归调用
        checkBoxSelectAll.setOnCheckedChangeListener(null);
        
        if (checkedCount == 0) {
            checkBoxSelectAll.setChecked(false);
        } else if (checkedCount == groupCheckBoxes.size()) {
            checkBoxSelectAll.setChecked(true);
        } else {
            // Android原生不支持indeterminate状态，这里只是演示
            checkBoxSelectAll.setChecked(false);
        }
        
        // 重新设置监听器
        checkBoxSelectAll.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                for (CheckBox cb : groupCheckBoxes) {
                    cb.setChecked(isChecked);
                }
            }
        });
    }
    
    private void applyCustomStyles() {
        // 自定义颜色
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
            checkBoxCustom1.setButtonTintList(ContextCompat.getColorStateList(this, R.color.checkbox_custom_color));
        }
        
        // 自定义文字样式
        checkBoxCustom2.setTextColor(Color.BLUE);
        checkBoxCustom2.setTextSize(18);
        
        // 自定义内边距
        checkBoxCustom3.setPadding(32, 16, 32, 16);
    }
    
    private void addEventLog(String event) {
        SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
        String timestamp = sdf.format(new Date());
        
        if (eventLog.length() > 0) {
            eventLog.insert(0, "\n");
        }
        eventLog.insert(0, "[" + timestamp + "] " + event);
        
        // 保持日志不要太长
        String[] lines = eventLog.toString().split("\n");
        if (lines.length > 5) {
            eventLog = new StringBuilder();
            for (int i = 0; i < 5; i++) {
                if (i > 0) eventLog.append("\n");
                eventLog.append(lines[i]);
            }
        }
        
        textViewEventLog.setText(eventLog.toString());
    }
}
```

## activity_main.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:fillViewport="true">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="16dp">

        <!-- 标题 -->
        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="Android CheckBox 功能演示"
            android:textSize="24sp"
            android:textStyle="bold"
            android:gravity="center"
            android:layout_marginBottom="24dp"
            android:textColor="@color/colorPrimary" />

        <!-- 1. 基本使用 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="1. 基本使用"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxBasic"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="基本复选框"
                    android:layout_marginBottom="8dp" />

                <TextView
                    android:id="@+id/textViewBasicStatus"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="状态: 未选中"
                    android:textColor="@android:color/darker_gray" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 2. 事件监听器 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="2. 事件监听器"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxListener"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="点击查看事件日志"
                    android:layout_marginBottom="8dp" />

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="事件日志:"
                    android:textStyle="bold"
                    android:layout_marginBottom="4dp" />

                <TextView
                    android:id="@+id/textViewEventLog"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:background="#f0f0f0"
                    android:padding="8dp"
                    android:textSize="12sp"
                    android:minHeight="80dp"
                    android:text="等待事件..."
                    android:fontFamily="monospace" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 3. 启用/禁用状态 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="3. 启用/禁用状态"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxDisabledChecked"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="禁用状态 (已选中)"
                    android:checked="true"
                    android:enabled="false"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxDisabledUnchecked"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="禁用状态 (未选中)"
                    android:checked="false"
                    android:enabled="false"
                    android:layout_marginBottom="8dp" />

                <Button
                    android:id="@+id/buttonToggleEnabled"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="启用" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 4. 自定义样式 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="4. 自定义样式"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxCustom1"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="自定义颜色"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxCustom2"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="自定义文字样式"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxCustom3"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="自定义内边距"
                    android:background="#e0e0e0" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 5. 分组使用 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="5. 分组使用"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxSelectAll"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="全选"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <View
                    android:layout_width="match_parent"
                    android:layout_height="1dp"
                    android:background="#cccccc"
                    android:layout_marginBottom="8dp" />

                <LinearLayout
                    android:id="@+id/layoutGroupItems"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="vertical"
                    android:paddingStart="24dp" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 6. 功能演示 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="6. 获取选中状态"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxFeature1"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="WiFi"
                    android:layout_marginBottom="4dp" />

                <CheckBox
                    android:id="@+id/checkBoxFeature2"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="蓝牙"
                    android:checked="true"
                    android:layout_marginBottom="4dp" />

                <CheckBox
                    android:id="@+id/checkBoxFeature3"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="GPS"
                    android:layout_marginBottom="8dp" />

                <Button
                    android:id="@+id/buttonGetSelected"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="获取选中项"
                    android:layout_marginBottom="8dp" />

                <TextView
                    android:id="@+id/textViewSelected"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:background="#f0f0f0"
                    android:padding="8dp"
                    android:text="点击按钮查看选中的项目" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 7. 编程控制 -->
        <androidx.cardview.widget.CardView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            app:cardElevation="4dp"
            app:cardCornerRadius="8dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:padding="16dp">

                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="7. 编程控制"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <CheckBox
                    android:id="@+id/checkBoxProgrammatic"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="通过代码控制的复选框"
                    android:layout_marginBottom="12dp" />

                <LinearLayout
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal">

                    <Button
                        android:id="@+id/buttonCheck"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="选中"
                        android:layout_marginEnd="4dp" />

                    <Button
                        android:id="@+id/buttonUncheck"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="取消"
                        android:layout_marginHorizontal="4dp" />

                    <Button
                        android:id="@+id/buttonToggle"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="切换"
                        android:layout_marginStart="4dp" />

                </LinearLayout>

            </LinearLayout>
        </androidx.cardview.widget.CardView>

    </LinearLayout>
</ScrollView>
```

## colors.xml (在res/values目录下)

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="colorPrimary">#6200EE</color>
    <color name="colorPrimaryDark">#3700B3</color>
    <color name="colorAccent">#03DAC5</color>
    
    <!-- CheckBox自定义颜色 -->
    <color name="checkbox_checked">#FF6B6B</color>
    <color name="checkbox_unchecked">#CCCCCC</color>
</resources>
```

## checkbox_custom_color.xml (在res/color目录下)

```xml
<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_checked="true" android:color="@color/checkbox_checked"/>
    <item android:state_checked="false" android:color="@color/checkbox_unchecked"/>
</selector>
```

## 功能说明

这个Demo应用展示了Android CheckBox的所有主要功能：

1. **基本使用** - 展示最简单的CheckBox使用方法和状态获取
2. **事件监听器** - 演示OnCheckedChangeListener和OnClickListener
3. **启用/禁用状态** - 展示如何动态控制CheckBox的启用状态
4. **自定义样式** - 包括自定义颜色、文字样式和内边距
5. **分组使用** - 实现全选功能和子项管理
6. **获取选中状态** - 展示如何获取多个CheckBox的选中状态
7. **编程控制** - 通过代码控制CheckBox的选中、取消和切换

## 使用说明

1. 将MainActivity.java放入你的项目主包中
2. 将activity_main.xml放入res/layout目录
3. 将colors.xml放入res/values目录
4. 创建res/color目录并放入checkbox_custom_color.xml
5. 确保在build.gradle中添加了CardView依赖：
   ```gradle
   implementation 'androidx.cardview:cardview:1.0.0'
   ```

这个Demo涵盖了CheckBox的所有常用功能，你可以运行并测试每个功能模块。 