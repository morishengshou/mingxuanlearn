*Thinking...*

> 用户要求我创建一个演示Android RadioButton和RadioGroup所有功能的Demo应用。我需要创建：
> 
> 1. MainActivity.java - 包含所有功能逻辑
> 2. activity_main.xml - 布局文件
> 3. 相关资源文件
> 
> 需要展示的功能包括：
> - RadioButton基本使用
> - RadioGroup分组功能
> - 单选功能
> - 事件监听
> - 获取选中项
> - 编程控制
> - 自定义样式
> - 横向/纵向布局
> - 动态添加RadioButton
> - 禁用状态
> - 清除选择
> 等等
> 
> 让我创建一个完整的Demo。

我将为您创建一个完整的Android原生应用Demo，展示RadioButton和RadioGroup的所有功能。

## MainActivity.java

```java
package com.example.radiobuttondemo;

import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    
    // 基本使用
    private RadioGroup radioGroupBasic;
    private RadioButton radioButton1, radioButton2, radioButton3;
    private TextView textViewBasicResult;
    
    // 事件监听
    private RadioGroup radioGroupListener;
    private TextView textViewEventLog;
    private StringBuilder eventLog = new StringBuilder();
    
    // 方向控制
    private RadioGroup radioGroupOrientation;
    private Button buttonToggleOrientation;
    private boolean isHorizontal = false;
    
    // 编程控制
    private RadioGroup radioGroupProgrammatic;
    private Button buttonSelect1, buttonSelect2, buttonSelect3, buttonClear;
    private TextView textViewProgrammaticResult;
    
    // 自定义样式
    private RadioGroup radioGroupCustom;
    
    // 动态添加
    private RadioGroup radioGroupDynamic;
    private Button buttonAddRadio, buttonRemoveRadio;
    private int dynamicRadioCount = 0;
    
    // 禁用状态
    private RadioGroup radioGroupDisabled;
    private Button buttonToggleEnabled;
    
    // 实际应用示例
    private RadioGroup radioGroupGender, radioGroupPayment, radioGroupSize;
    private Button buttonSubmit;
    private TextView textViewFormResult;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        setupListeners();
        setupCustomStyles();
        setupInitialStates();
    }
    
    private void initViews() {
        // 基本使用
        radioGroupBasic = findViewById(R.id.radioGroupBasic);
        radioButton1 = findViewById(R.id.radioButton1);
        radioButton2 = findViewById(R.id.radioButton2);
        radioButton3 = findViewById(R.id.radioButton3);
        textViewBasicResult = findViewById(R.id.textViewBasicResult);
        
        // 事件监听
        radioGroupListener = findViewById(R.id.radioGroupListener);
        textViewEventLog = findViewById(R.id.textViewEventLog);
        
        // 方向控制
        radioGroupOrientation = findViewById(R.id.radioGroupOrientation);
        buttonToggleOrientation = findViewById(R.id.buttonToggleOrientation);
        
        // 编程控制
        radioGroupProgrammatic = findViewById(R.id.radioGroupProgrammatic);
        buttonSelect1 = findViewById(R.id.buttonSelect1);
        buttonSelect2 = findViewById(R.id.buttonSelect2);
        buttonSelect3 = findViewById(R.id.buttonSelect3);
        buttonClear = findViewById(R.id.buttonClear);
        textViewProgrammaticResult = findViewById(R.id.textViewProgrammaticResult);
        
        // 自定义样式
        radioGroupCustom = findViewById(R.id.radioGroupCustom);
        
        // 动态添加
        radioGroupDynamic = findViewById(R.id.radioGroupDynamic);
        buttonAddRadio = findViewById(R.id.buttonAddRadio);
        buttonRemoveRadio = findViewById(R.id.buttonRemoveRadio);
        
        // 禁用状态
        radioGroupDisabled = findViewById(R.id.radioGroupDisabled);
        buttonToggleEnabled = findViewById(R.id.buttonToggleEnabled);
        
        // 实际应用示例
        radioGroupGender = findViewById(R.id.radioGroupGender);
        radioGroupPayment = findViewById(R.id.radioGroupPayment);
        radioGroupSize = findViewById(R.id.radioGroupSize);
        buttonSubmit = findViewById(R.id.buttonSubmit);
        textViewFormResult = findViewById(R.id.textViewFormResult);
    }
    
    private void setupListeners() {
        // 基本使用监听器
        radioGroupBasic.setOnCheckedChangeListener(new RadioGroup.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(RadioGroup group, int checkedId) {
                String selected = "";
                if (checkedId == R.id.radioButton1) {
                    selected = "选项 1";
                } else if (checkedId == R.id.radioButton2) {
                    selected = "选项 2";
                } else if (checkedId == R.id.radioButton3) {
                    selected = "选项 3";
                }
                textViewBasicResult.setText("当前选择: " + selected);
            }
        });
        
        // 详细事件监听器
        radioGroupListener.setOnCheckedChangeListener(new RadioGroup.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(RadioGroup group, int checkedId) {
                RadioButton radioButton = findViewById(checkedId);
                if (radioButton != null) {
                    addEventLog("onCheckedChanged: " + radioButton.getText());
                }
            }
        });
        
        // 为RadioGroup中的每个RadioButton添加点击监听器
        for (int i = 0; i < radioGroupListener.getChildCount(); i++) {
            View child = radioGroupListener.getChildAt(i);
            if (child instanceof RadioButton) {
                child.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        RadioButton rb = (RadioButton) v;
                        addEventLog("onClick: " + rb.getText());
                    }
                });
            }
        }
        
        // 方向切换
        buttonToggleOrientation.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                isHorizontal = !isHorizontal;
                radioGroupOrientation.setOrientation(
                    isHorizontal ? LinearLayout.HORIZONTAL : LinearLayout.VERTICAL
                );
                buttonToggleOrientation.setText(isHorizontal ? "切换为垂直" : "切换为水平");
                Toast.makeText(MainActivity.this, 
                    "已切换为" + (isHorizontal ? "水平" : "垂直") + "布局", 
                    Toast.LENGTH_SHORT).show();
            }
        });
        
        // 编程控制监听器
        radioGroupProgrammatic.setOnCheckedChangeListener(new RadioGroup.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(RadioGroup group, int checkedId) {
                updateProgrammaticResult();
            }
        });
        
        buttonSelect1.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                radioGroupProgrammatic.check(R.id.radioProg1);
            }
        });
        
        buttonSelect2.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                radioGroupProgrammatic.check(R.id.radioProg2);
            }
        });
        
        buttonSelect3.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                radioGroupProgrammatic.check(R.id.radioProg3);
            }
        });
        
        buttonClear.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                radioGroupProgrammatic.clearCheck();
                updateProgrammaticResult();
            }
        });
        
        // 动态添加/删除
        buttonAddRadio.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                dynamicRadioCount++;
                RadioButton newRadioButton = new RadioButton(MainActivity.this);
                newRadioButton.setText("动态选项 " + dynamicRadioCount);
                newRadioButton.setId(View.generateViewId());
                newRadioButton.setTextSize(16);
                newRadioButton.setPadding(0, 8, 0, 8);
                
                radioGroupDynamic.addView(newRadioButton);
                Toast.makeText(MainActivity.this, "已添加新选项", Toast.LENGTH_SHORT).show();
            }
        });
        
        buttonRemoveRadio.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                int childCount = radioGroupDynamic.getChildCount();
                if (childCount > 0) {
                    radioGroupDynamic.removeViewAt(childCount - 1);
                    dynamicRadioCount--;
                    Toast.makeText(MainActivity.this, "已删除最后一个选项", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(MainActivity.this, "没有可删除的选项", Toast.LENGTH_SHORT).show();
                }
            }
        });
        
        // 启用/禁用切换
        buttonToggleEnabled.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                boolean newEnabled = !radioGroupDisabled.getChildAt(0).isEnabled();
                for (int i = 0; i < radioGroupDisabled.getChildCount(); i++) {
                    radioGroupDisabled.getChildAt(i).setEnabled(newEnabled);
                }
                buttonToggleEnabled.setText(newEnabled ? "禁用" : "启用");
                Toast.makeText(MainActivity.this, 
                    newEnabled ? "RadioGroup已启用" : "RadioGroup已禁用", 
                    Toast.LENGTH_SHORT).show();
            }
        });
        
        // 表单提交
        buttonSubmit.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                StringBuilder result = new StringBuilder("表单结果:\n\n");
                
                // 获取性别选择
                int genderId = radioGroupGender.getCheckedRadioButtonId();
                if (genderId != -1) {
                    RadioButton genderButton = findViewById(genderId);
                    result.append("性别: ").append(genderButton.getText()).append("\n");
                } else {
                    result.append("性别: 未选择\n");
                }
                
                // 获取支付方式
                int paymentId = radioGroupPayment.getCheckedRadioButtonId();
                if (paymentId != -1) {
                    RadioButton paymentButton = findViewById(paymentId);
                    result.append("支付方式: ").append(paymentButton.getText()).append("\n");
                } else {
                    result.append("支付方式: 未选择\n");
                }
                
                // 获取尺寸选择
                int sizeId = radioGroupSize.getCheckedRadioButtonId();
                if (sizeId != -1) {
                    RadioButton sizeButton = findViewById(sizeId);
                    result.append("尺寸: ").append(sizeButton.getText()).append("\n");
                } else {
                    result.append("尺寸: 未选择\n");
                }
                
                textViewFormResult.setText(result.toString());
            }
        });
    }
    
    private void setupCustomStyles() {
        // 为自定义样式的RadioGroup中的RadioButton设置样式
        for (int i = 0; i < radioGroupCustom.getChildCount(); i++) {
            View child = radioGroupCustom.getChildAt(i);
            if (child instanceof RadioButton) {
                RadioButton rb = (RadioButton) child;
                
                // 设置不同的样式
                switch (i) {
                    case 0: // 自定义颜色
                        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                            rb.setButtonTintList(ContextCompat.getColorStateList(this, R.color.radio_custom_color));
                        }
                        break;
                    case 1: // 自定义文字
                        rb.setTextColor(Color.BLUE);
                        rb.setTextSize(18);
                        rb.setTypeface(null, android.graphics.Typeface.BOLD);
                        break;
                    case 2: // 自定义间距
                        rb.setPadding(50, 20, 50, 20);
                        rb.setBackgroundColor(Color.parseColor("#f0f0f0"));
                        break;
                }
            }
        }
    }
    
    private void setupInitialStates() {
        // 设置一些初始选中状态
        radioButton2.setChecked(true);
        radioGroupPayment.check(R.id.radioCredit);
        
        // 禁用某些选项
        for (int i = 0; i < radioGroupDisabled.getChildCount(); i++) {
            radioGroupDisabled.getChildAt(i).setEnabled(false);
        }
        
        // 添加一些初始的动态选项
        for (int i = 1; i <= 2; i++) {
            dynamicRadioCount++;
            RadioButton newRadioButton = new RadioButton(this);
            newRadioButton.setText("动态选项 " + dynamicRadioCount);
            newRadioButton.setId(View.generateViewId());
            newRadioButton.setTextSize(16);
            newRadioButton.setPadding(0, 8, 0, 8);
            radioGroupDynamic.addView(newRadioButton);
        }
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
    
    private void updateProgrammaticResult() {
        int checkedId = radioGroupProgrammatic.getCheckedRadioButtonId();
        if (checkedId != -1) {
            RadioButton checkedButton = findViewById(checkedId);
            textViewProgrammaticResult.setText("当前选择: " + checkedButton.getText());
        } else {
            textViewProgrammaticResult.setText("当前选择: 无");
        }
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
            android:text="Android RadioButton/RadioGroup 功能演示"
            android:textSize="22sp"
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

                <RadioGroup
                    android:id="@+id/radioGroupBasic"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="8dp">

                    <RadioButton
                        android:id="@+id/radioButton1"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 1" />

                    <RadioButton
                        android:id="@+id/radioButton2"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 2" />

                    <RadioButton
                        android:id="@+id/radioButton3"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 3" />

                </RadioGroup>

                <TextView
                    android:id="@+id/textViewBasicResult"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="当前选择: 选项 2"
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

                <RadioGroup
                    android:id="@+id/radioGroupListener"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="8dp">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="监听选项 A" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="监听选项 B" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="监听选项 C" />

                </RadioGroup>

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

        <!-- 3. 布局方向 -->
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
                    android:text="3. 布局方向控制"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <RadioGroup
                    android:id="@+id/radioGroupOrientation"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="vertical"
                    android:layout_marginBottom="8dp">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 A"
                        android:checked="true" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 B" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="选项 C" />

                </RadioGroup>

                <Button
                    android:id="@+id/buttonToggleOrientation"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="切换为水平" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 4. 编程控制 -->
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
                    android:text="4. 编程控制"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <RadioGroup
                    android:id="@+id/radioGroupProgrammatic"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="8dp">

                    <RadioButton
                        android:id="@+id/radioProg1"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="程序选项 1" />

                    <RadioButton
                        android:id="@+id/radioProg2"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="程序选项 2" />

                    <RadioButton
                        android:id="@+id/radioProg3"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="程序选项 3" />

                </RadioGroup>

                <LinearLayout
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal"
                    android:layout_marginBottom="8dp">

                    <Button
                        android:id="@+id/buttonSelect1"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="选择1"
                        android:textSize="12sp"
                        android:layout_marginEnd="2dp" />

                    <Button
                        android:id="@+id/buttonSelect2"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="选择2"
                        android:textSize="12sp"
                        android:layout_marginHorizontal="2dp" />

                    <Button
                        android:id="@+id/buttonSelect3"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="选择3"
                        android:textSize="12sp"
                        android:layout_marginHorizontal="2dp" />

                    <Button
                        android:id="@+id/buttonClear"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="清除"
                        android:textSize="12sp"
                        android:layout_marginStart="2dp" />

                </LinearLayout>

                <TextView
                    android:id="@+id/textViewProgrammaticResult"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="当前选择: 无"
                    android:textColor="@android:color/darker_gray" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 5. 自定义样式 -->
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
                    android:text="5. 自定义样式"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <RadioGroup
                    android:id="@+id/radioGroupCustom"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="自定义颜色" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="自定义文字样式" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="自定义间距和背景" />

                </RadioGroup>

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 6. 动态添加/删除 -->
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
                    android:text="6. 动态添加/删除"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <RadioGroup
                    android:id="@+id/radioGroupDynamic"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="8dp">

                </RadioGroup>

                <LinearLayout
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal">

                    <Button
                        android:id="@+id/buttonAddRadio"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="添加选项"
                        android:layout_marginEnd="8dp" />

                    <Button
                        android:id="@+id/buttonRemoveRadio"
                        android:layout_width="0dp"
                        android:layout_height="wrap_content"
                        android:layout_weight="1"
                        android:text="删除选项" />

                </LinearLayout>

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 7. 启用/禁用状态 -->
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
                    android:text="7. 启用/禁用状态"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="8dp" />

                <RadioGroup
                    android:id="@+id/radioGroupDisabled"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="8dp">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="禁用选项 1"
                        android:enabled="false" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="禁用选项 2"
                        android:enabled="false"
                        android:checked="true" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="禁用选项 3"
                        android:enabled="false" />

                </RadioGroup>

                <Button
                    android:id="@+id/buttonToggleEnabled"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="启用" />

            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <!-- 8. 实际应用示例 -->
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
                    android:text="8. 实际应用示例 - 表单"
                    android:textSize="18sp"
                    android:textStyle="bold"
                    android:layout_marginBottom="12dp" />

                <!-- 性别选择 -->
                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="性别:"
                    android:textStyle="bold"
                    android:layout_marginBottom="4dp" />

                <RadioGroup
                    android:id="@+id/radioGroupGender"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal"
                    android:layout_marginBottom="12dp">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="男"
                        android:layout_marginEnd="24dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="女"
                        android:layout_marginEnd="24dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="保密" />

                </RadioGroup>

                <!-- 支付方式 -->
                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="支付方式:"
                    android:textStyle="bold"
                    android:layout_marginBottom="4dp" />

                <RadioGroup
                    android:id="@+id/radioGroupPayment"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginBottom="12dp">

                    <RadioButton
                        android:id="@+id/radioCredit"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="信用卡" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="支付宝" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="微信支付" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="货到付款" />

                </RadioGroup>

                <!-- 尺寸选择 -->
                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="尺寸:"
                    android:textStyle="bold"
                    android:layout_marginBottom="4dp" />

                <RadioGroup
                    android:id="@+id/radioGroupSize"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal"
                    android:layout_marginBottom="12dp">

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="S"
                        android:layout_marginEnd="16dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="M"
                        android:layout_marginEnd="16dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="L"
                        android:layout_marginEnd="16dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="XL"
                        android:layout_marginEnd="16dp" />

                    <RadioButton
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="XXL" />

                </RadioGroup>

                <Button
                    android:id="@+id/buttonSubmit"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="提交表单"
                    android:layout_marginBottom="8dp" />

                <TextView
                    android:id="@+id/textViewFormResult"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:background="#f0f0f0"
                    android:padding="12dp"
                    android:text="点击提交按钮查看选择结果"
                    android:textColor="@android:color/darker_gray" />

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
    
    <!-- RadioButton自定义颜色 -->
    <color name="radio_checked">#FF6B6B</color>
    <color name="radio_unchecked">#CCCCCC</color>
</resources>
```

## radio_custom_color.xml (在res/color目录下)

```xml
<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_checked="true" android:color="@color/radio_checked"/>
    <item android:state_checked="false" android:color="@color/radio_unchecked"/>
</selector>
```

## 功能说明

这个Demo应用展示了Android RadioButton和RadioGroup的所有主要功能：

1. **基本使用** - 展示RadioGroup的基本单选功能
2. **事件监听器** - 演示OnCheckedChangeListener和OnClickListener
3. **布局方向控制** - 动态切换水平/垂直布局
4. **编程控制** - 通过代码选择、清除选项
5. **自定义样式** - 包括颜色、文字样式、间距等
6. **动态添加/删除** - 运行时添加或删除RadioButton
7. **启用/禁用状态** - 控制RadioButton的可用性
8. **实际应用示例** - 展示在表单中的实际使用场景

## 关键特性演示

- **单选功能**: RadioGroup确保同一时间只能选中一个RadioButton
- **状态获取**: 通过getCheckedRadioButtonId()获取选中项
- **清除选择**: 使用clearCheck()方法清除所有选择
- **事件处理**: 监听选择变化并做出响应
- **动态操作**: 运行时添加、删除、修改RadioButton
- **样式定制**: 自定义颜色、大小、间距等视觉效果

## 使用说明

1. 将MainActivity.java放入项目主包中
2. 将activity_main.xml放入res/layout目录
3. 将colors.xml放入res/values目录
4. 创建res/color目录并放入radio_custom_color.xml
5. 确保在build.gradle中添加了CardView依赖：
   ```gradle
   implementation 'androidx.cardview:cardview:1.0.0'
   ```

这个Demo完整展示了RadioButton和RadioGroup的所有常用功能，帮助开发者快速了解和使用这些组件。