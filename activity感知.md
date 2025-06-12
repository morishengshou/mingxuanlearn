*Thinking...*

> 用户想了解MainActivity如何感知AnotherActivity的启动状态和生命周期状态。这涉及到Android中Activity之间的通信和状态监控。我需要介绍几种常见的方法：
> 
> 1. startActivityForResult() - 传统方法
> 2. Activity Result API - 新方法
> 3. 使用广播
> 4. 使用EventBus或LiveData
> 5. Application类共享状态
> 6. 使用Service
> 
> 我应该给出具体的代码示例来展示这些方法。

在Android中，MainActivity感知AnotherActivity的启动状态和生命周期状态有多种方法。我来介绍几种常用的方式：

## 方法1：使用Activity Result API（推荐）

这是Google推荐的新方式，用于替代已废弃的startActivityForResult。

### MainActivity.java
```java
package com.example.myapplication;

import androidx.activity.result.ActivityResult;
import androidx.activity.result.ActivityResultCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

public class MainActivity extends AppCompatActivity {
    
    private EditText editText;
    private Button button;
    private TextView statusTextView;
    
    // 声明Activity Result Launcher
    private ActivityResultLauncher<Intent> activityResultLauncher;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        editText = findViewById(R.id.editText);
        button = findViewById(R.id.button);
        statusTextView = findViewById(R.id.statusTextView);
        
        // 注册Activity Result
        activityResultLauncher = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(),
            new ActivityResultCallback<ActivityResult>() {
                @Override
                public void onActivityResult(ActivityResult result) {
                    if (result.getResultCode() == RESULT_OK) {
                        Intent data = result.getData();
                        if (data != null) {
                            String status = data.getStringExtra("status");
                            String returnMessage = data.getStringExtra("returnMessage");
                            statusTextView.setText("AnotherActivity已关闭\n状态: " + status + 
                                                 "\n返回消息: " + returnMessage);
                        }
                    } else if (result.getResultCode() == RESULT_CANCELED) {
                        statusTextView.setText("AnotherActivity被取消");
                    }
                }
            }
        );
        
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String inputText = editText.getText().toString();
                Intent intent = new Intent(MainActivity.this, AnotherActivity.class);
                intent.putExtra("message", inputText);
                
                // 使用launcher启动Activity
                activityResultLauncher.launch(intent);
                statusTextView.setText("AnotherActivity已启动...");
            }
        });
    }
}
```

### AnotherActivity.java
```java
package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

public class AnotherActivity extends AppCompatActivity {
    
    private TextView textView;
    private Button backButton;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_another);
        
        textView = findViewById(R.id.textView);
        backButton = findViewById(R.id.backButton);
        
        String message = getIntent().getStringExtra("message");
        if (message != null) {
            textView.setText(message);
        }
        
        backButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // 设置返回数据
                Intent resultIntent = new Intent();
                resultIntent.putExtra("status", "正常完成");
                resultIntent.putExtra("returnMessage", "用户点击了返回按钮");
                setResult(RESULT_OK, resultIntent);
                finish();
            }
        });
    }
    
    @Override
    public void onBackPressed() {
        // 监听返回键
        Intent resultIntent = new Intent();
        resultIntent.putExtra("status", "返回键退出");
        resultIntent.putExtra("returnMessage", "用户按了返回键");
        setResult(RESULT_OK, resultIntent);
        super.onBackPressed();
    }
}
```

## 方法2：使用广播（BroadcastReceiver）

### MainActivity.java
```java
package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

public class MainActivity extends AppCompatActivity {
    
    private EditText editText;
    private Button button;
    private TextView statusTextView;
    private BroadcastReceiver statusReceiver;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        editText = findViewById(R.id.editText);
        button = findViewById(R.id.button);
        statusTextView = findViewById(R.id.statusTextView);
        
        // 创建广播接收器
        statusReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String status = intent.getStringExtra("status");
                statusTextView.setText("收到状态更新: " + status);
            }
        };
        
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String inputText = editText.getText().toString();
                Intent intent = new Intent(MainActivity.this, AnotherActivity.class);
                intent.putExtra("message", inputText);
                startActivity(intent);
            }
        });
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        // 注册广播接收器
        LocalBroadcastManager.getInstance(this).registerReceiver(
            statusReceiver, 
            new IntentFilter("ANOTHER_ACTIVITY_STATUS")
        );
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        // 注销广播接收器
        LocalBroadcastManager.getInstance(this).unregisterReceiver(statusReceiver);
    }
}
```

### AnotherActivity.java（发送广播）
```java
package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;

public class AnotherActivity extends AppCompatActivity {
    
    private TextView textView;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_another);
        
        textView = findViewById(R.id.textView);
        String message = getIntent().getStringExtra("message");
        if (message != null) {
            textView.setText(message);
        }
        
        // 发送onCreate状态
        sendStatusBroadcast("onCreate - Activity已创建");
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        sendStatusBroadcast("onResume - Activity已恢复");
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        sendStatusBroadcast("onPause - Activity已暂停");
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        sendStatusBroadcast("onDestroy - Activity已销毁");
    }
    
    private void sendStatusBroadcast(String status) {
        Intent intent = new Intent("ANOTHER_ACTIVITY_STATUS");
        intent.putExtra("status", status);
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent);
    }
}
```

## 方法3：使用Application类共享状态

### MyApplication.java
```java
package com.example.myapplication;

import android.app.Application;

public class MyApplication extends Application {
    
    private boolean isAnotherActivityRunning = false;
    private String anotherActivityStatus = "";
    
    public boolean isAnotherActivityRunning() {
        return isAnotherActivityRunning;
    }
    
    public void setAnotherActivityRunning(boolean running) {
        isAnotherActivityRunning = running;
    }
    
    public String getAnotherActivityStatus() {
        return anotherActivityStatus;
    }
    
    public void setAnotherActivityStatus(String status) {
        anotherActivityStatus = status;
    }
}
```

### 在AndroidManifest.xml中声明Application
```xml
<application
    android:name=".MyApplication"
    android:allowBackup="true"
    ...>
```

### 在AnotherActivity中更新状态
```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    MyApplication app = (MyApplication) getApplication();
    app.setAnotherActivityRunning(true);
    app.setAnotherActivityStatus("运行中");
}

@Override
protected void onDestroy() {
    super.onDestroy();
    MyApplication app = (MyApplication) getApplication();
    app.setAnotherActivityRunning(false);
    app.setAnotherActivityStatus("已销毁");
}
```

## 方法4：使用EventBus（需要添加依赖）

### build.gradle (Module: app)
```gradle
dependencies {
    implementation 'org.greenrobot:eventbus:3.3.1'
}
```

### StatusEvent.java
```java
public class StatusEvent {
    public final String status;
    
    public StatusEvent(String status) {
        this.status = status;
    }
}
```

### 在MainActivity中订阅事件
```java
@Override
protected void onStart() {
    super.onStart();
    EventBus.getDefault().register(this);
}

@Override
protected void onStop() {
    super.onStop();
    EventBus.getDefault().unregister(this);
}

@Subscribe(threadMode = ThreadMode.MAIN)
public void onStatusEvent(StatusEvent event) {
    statusTextView.setText("状态: " + event.status);
}
```

### 在AnotherActivity中发送事件
```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    EventBus.getDefault().post(new StatusEvent("AnotherActivity已创建"));
}
```

## 更新的布局文件

### activity_main.xml（添加状态显示）
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:gravity="center">

    <EditText
        android:id="@+id/editText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="请输入文字"
        android:inputType="text"
        android:layout_marginBottom="20dp"/>

    <Button
        android:id="@+id/button"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="发送"
        android:textSize="16sp"
        android:layout_marginBottom="20dp"/>
    
    <TextView
        android:id="@+id/statusTextView"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="等待状态..."
        android:textSize="14sp"
        android:textColor="#666666"/>

</LinearLayout>
```

### activity_another.xml（添加返回按钮）
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:gravity="center">

    <TextView
        android:id="@+id/textView"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="等待接收消息..."
        android:textSize="18sp"
        android:textColor="#333333"
        android:layout_marginBottom="20dp"/>
    
    <Button
        android:id="@+id/backButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="返回"
        android:textSize="16sp"/>

</LinearLayout>
```

## 总结

1. **Activity Result API** - 最适合需要获取Activity返回结果的场景
2. **广播** - 适合实时监听Activity状态变化
3. **Application类** - 适合全局状态管理
4. **EventBus** - 适合复杂的事件通信场景

选择哪种方法取决于你的具体需求。如果只需要知道Activity是否完成并获取结果，使用Activity Result API最简单；如果需要实时监控Activity的生命周期状态，使用广播或EventBus更合适。