*Thinking...*

> 用户想要创建一个简单的Android应用demo，需要：
> 1. MainActivity - 包含输入框和按钮
> 2. AnotherActivity - 包含TextView显示传入的内容
> 3. 使用Intent在两个Activity之间传递数据
> 
> 我需要提供：
> 1. MainActivity.java
> 2. AnotherActivity.java
> 3. activity_main.xml
> 4. activity_another.xml
> 5. AndroidManifest.xml中的配置
> 
> 这是一个基础的Android开发任务，我应该提供完整的代码示例。

我来帮你创建这个简单的Android应用demo。你需要创建以下文件：

## 1. MainActivity.java

```java
package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;

public class MainActivity extends AppCompatActivity {
    
    private EditText editText;
    private Button button;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // 获取控件引用
        editText = findViewById(R.id.editText);
        button = findViewById(R.id.button);
        
        // 设置按钮点击事件
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // 获取输入框的文字
                String inputText = editText.getText().toString();
                
                // 创建Intent并传递数据
                Intent intent = new Intent(MainActivity.this, AnotherActivity.class);
                intent.putExtra("message", inputText);
                
                // 启动AnotherActivity
                startActivity(intent);
            }
        });
    }
}
```

## 2. AnotherActivity.java

```java
package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;
import android.os.Bundle;
import android.widget.TextView;

public class AnotherActivity extends AppCompatActivity {
    
    private TextView textView;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_another);
        
        // 获取TextView引用
        textView = findViewById(R.id.textView);
        
        // 从Intent中获取传递的数据
        String message = getIntent().getStringExtra("message");
        
        // 在TextView中显示数据
        if (message != null) {
            textView.setText(message);
        } else {
            textView.setText("没有收到消息");
        }
    }
}
```

## 3. activity_main.xml

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
        android:textSize="16sp"/>

</LinearLayout>
```

## 4. activity_another.xml

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
        android:textColor="#333333"/>

</LinearLayout>
```

## 5. AndroidManifest.xml 配置

在AndroidManifest.xml中，确保声明了AnotherActivity：

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.myapplication">

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.MyApplication">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <!-- 声明AnotherActivity -->
        <activity android:name=".AnotherActivity" />
        
    </application>

</manifest>
```

## 使用说明

1. 将以上代码复制到对应的文件中
2. 确保包名与你的项目包名一致
3. 运行应用后，在输入框中输入文字
4. 点击"发送"按钮
5. 应用会跳转到AnotherActivity，并显示你输入的文字

这个demo展示了Android开发中最基本的Activity间通信方式，使用Intent的putExtra()方法传递数据，在目标Activity中使用getStringExtra()方法接收数据。