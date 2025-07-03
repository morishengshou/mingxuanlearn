*Thinking...*

> 用户询问关于Gson解析JSON时可能出现的异常以及如何处理。我需要：
> 
> 1. 列出Gson常见的异常类型
> 2. 说明每种异常的触发场景
> 3. 提供具体的异常处理代码示例
> 4. 给出最佳实践建议

在使用Gson解析JSON时，可能会遇到多种异常。以下是详细的异常类型和处理方法：

## 1. 常见异常类型

### JsonSyntaxException
最常见的异常，当JSON格式不正确时抛出：

```java
// 错误的JSON格式示例
String invalidJson1 = "{name:\"张三\"}";  // 缺少引号
String invalidJson2 = "{\"name\":\"张三\"";  // 缺少闭合括号
String invalidJson3 = "{\"name\":\"张三\",}";  // 多余的逗号

try {
    User user = gson.fromJson(invalidJson1, User.class);
} catch (JsonSyntaxException e) {
    // com.google.gson.JsonSyntaxException: 
    // com.google.gson.stream.MalformedJsonException: 
    // Expected name at line 1 column 2 path $.
    Log.e("GSON", "JSON语法错误: " + e.getMessage());
}
```

### JsonParseException
解析过程中的错误，通常是类型不匹配：

```java
public class User {
    private String name;
    private int age;  // 期望整数
}

String json = "{\"name\":\"张三\",\"age\":\"二十五\"}";  // age是字符串

try {
    User user = gson.fromJson(json, User.class);
} catch (JsonParseException e) {
    // NumberFormatException: For input string: "二十五"
    Log.e("GSON", "解析错误: " + e.getMessage());
}
```

### IllegalStateException
当JSON结构与预期不符时：

```java
String json = "[{\"name\":\"张三\"}]";  // JSON数组

try {
    User user = gson.fromJson(json, User.class);  // 期望对象，实际是数组
} catch (IllegalStateException e) {
    // Expected BEGIN_OBJECT but was BEGIN_ARRAY
    Log.e("GSON", "状态错误: " + e.getMessage());
}
```

### NumberFormatException
数字格式错误：

```java
String json = "{\"price\":\"abc\"}";  // price应该是数字

public class Product {
    private double price;
}

try {
    Product product = gson.fromJson(json, Product.class);
} catch (NumberFormatException e) {
    Log.e("GSON", "数字格式错误: " + e.getMessage());
}
```

## 2. 统一异常处理方案

### 基础处理模式

```java
public class JsonParser {
    private static final Gson gson = new Gson();
    
    public static <T> T parseJson(String json, Class<T> classOfT) {
        try {
            return gson.fromJson(json, classOfT);
        } catch (JsonSyntaxException e) {
            // JSON格式错误
            Log.e("JSON_PARSE", "JSON语法错误: " + e.getMessage());
            return null;
        } catch (JsonParseException e) {
            // 解析错误（类型不匹配等）
            Log.e("JSON_PARSE", "JSON解析错误: " + e.getMessage());
            return null;
        } catch (IllegalStateException e) {
            // JSON结构错误
            Log.e("JSON_PARSE", "JSON结构错误: " + e.getMessage());
            return null;
        } catch (NumberFormatException e) {
            // 数字格式错误
            Log.e("JSON_PARSE", "数字格式错误: " + e.getMessage());
            return null;
        } catch (Exception e) {
            // 其他未知错误
            Log.e("JSON_PARSE", "未知错误: " + e.getMessage());
            return null;
        }
    }
}
```

### 封装Result类处理

```java
public class Result<T> {
    private final T data;
    private final String error;
    private final boolean success;
    
    private Result(T data, String error, boolean success) {
        this.data = data;
        this.error = error;
        this.success = success;
    }
    
    public static <T> Result<T> success(T data) {
        return new Result<>(data, null, true);
    }
    
    public static <T> Result<T> error(String error) {
        return new Result<>(null, error, false);
    }
    
    // getter方法...
}

public class SafeJsonParser {
    private static final Gson gson = new GsonBuilder()
        .setLenient()  // 宽松模式，允许一些非标准JSON
        .create();
    
    public static <T> Result<T> parse(String json, Class<T> classOfT) {
        if (TextUtils.isEmpty(json)) {
            return Result.error("JSON字符串为空");
        }
        
        try {
            T data = gson.fromJson(json, classOfT);
            if (data == null) {
                return Result.error("解析结果为空");
            }
            return Result.success(data);
        } catch (JsonSyntaxException e) {
            return Result.error("JSON格式错误: " + getReadableError(e));
        } catch (JsonParseException e) {
            return Result.error("数据类型不匹配: " + getReadableError(e));
        } catch (IllegalStateException e) {
            return Result.error("JSON结构错误: " + getReadableError(e));
        } catch (NumberFormatException e) {
            return Result.error("数字格式错误: " + e.getMessage());
        } catch (Exception e) {
            return Result.error("解析失败: " + e.getClass().getSimpleName());
        }
    }
    
    private static String getReadableError(Exception e) {
        String message = e.getMessage();
        if (message == null) return "未知错误";
        
        // 提取更友好的错误信息
        if (message.contains("Expected BEGIN_OBJECT but was BEGIN_ARRAY")) {
            return "期望JSON对象，实际是数组";
        } else if (message.contains("Expected BEGIN_ARRAY but was BEGIN_OBJECT")) {
            return "期望JSON数组，实际是对象";
        } else if (message.contains("Unterminated string")) {
            return "字符串未正确闭合";
        } else if (message.contains("Expected name")) {
            return "JSON键名格式错误";
        }
        
        return message;
    }
}
```

## 3. 容错性处理

### 使用默认值

```java
public class RobustParser {
    private static final Gson gson = new GsonBuilder()
        .registerTypeAdapter(Integer.class, new IntegerTypeAdapter())
        .registerTypeAdapter(int.class, new IntegerTypeAdapter())
        .create();
    
    // 自定义整数适配器，处理异常情况
    static class IntegerTypeAdapter extends TypeAdapter<Integer> {
        @Override
        public void write(JsonWriter out, Integer value) throws IOException {
            out.value(value);
        }
        
        @Override
        public Integer read(JsonReader in) throws IOException {
            if (in.peek() == JsonToken.NULL) {
                in.nextNull();
                return 0;  // 默认值
            }
            
            try {
                return in.nextInt();
            } catch (NumberFormatException e) {
                in.skipValue();  // 跳过无效值
                return 0;  // 返回默认值
            }
        }
    }
}
```

### 部分解析策略

```java
public class PartialParser {
    // 当部分字段解析失败时，保留能解析的部分
    public static <T> T parsePartial(String json, Class<T> classOfT) {
        try {
            JsonElement element = JsonParser.parseString(json);
            return parseElement(element, classOfT);
        } catch (Exception e) {
            // 创建一个空对象
            try {
                return classOfT.newInstance();
            } catch (Exception ex) {
                return null;
            }
        }
    }
    
    private static <T> T parseElement(JsonElement element, Class<T> classOfT) {
        Gson gson = new GsonBuilder()
            .registerTypeAdapter(String.class, (JsonDeserializer<String>) 
                (json, typeOfT, context) -> {
                    try {
                        return json.getAsString();
                    } catch (Exception e) {
                        return "";  // 字符串解析失败返回空字符串
                    }
                })
            .create();
        
        return gson.fromJson(element, classOfT);
    }
}
```

## 4. 预验证JSON

```java
public class JsonValidator {
    public static boolean isValidJson(String json) {
        if (TextUtils.isEmpty(json)) {
            return false;
        }
        
        try {
            JsonElement element = JsonParser.parseString(json);
            return element != null;
        } catch (JsonSyntaxException e) {
            return false;
        }
    }
    
    public static ValidationResult validateAndParse(String json, Class<?> targetClass) {
        ValidationResult result = new ValidationResult();
        
        // 1. 检查是否为空
        if (TextUtils.isEmpty(json)) {
            result.addError("JSON字符串为空");
            return result;
        }
        
        // 2. 检查基本格式
        json = json.trim();
        if (!json.startsWith("{") && !json.startsWith("[")) {
            result.addError("JSON必须以{或[开头");
            return result;
        }
        
        // 3. 尝试解析
        try {
            JsonElement element = JsonParser.parseString(json);
            
            // 4. 检查结构匹配
            if (element.isJsonArray() && !targetClass.isArray() && 
                !List.class.isAssignableFrom(targetClass)) {
                result.addError("JSON是数组，但目标类型不是");
            }
            
            if (element.isJsonObject() && 
                (targetClass.isArray() || List.class.isAssignableFrom(targetClass))) {
                result.addError("JSON是对象，但目标类型是数组/列表");
            }
            
            result.setValid(result.getErrors().isEmpty());
        } catch (JsonSyntaxException e) {
            result.addError("JSON格式错误: " + e.getMessage());
        }
        
        return result;
    }
}

class ValidationResult {
    private boolean valid;
    private List<String> errors = new ArrayList<>();
    
    // getter/setter和辅助方法
}
```

## 5. 最佳实践示例

```java
public class GsonHelper {
    private static final String TAG = "GsonHelper";
    private static final Gson gson = createGson();
    
    private static Gson createGson() {
        return new GsonBuilder()
            .setLenient()  // 宽松模式
            .serializeNulls()  // 序列化null值
            .disableHtmlEscaping()  // 禁用HTML转义
            .create();
    }
    
    /**
     * 安全的JSON解析方法
     * @param json JSON字符串
     * @param classOfT 目标类型
     * @param defaultValue 解析失败时的默认值
     * @return 解析结果或默认值
     */
    public static <T> T fromJsonSafe(String json, Class<T> classOfT, T defaultValue) {
        if (TextUtils.isEmpty(json)) {
            Log.w(TAG, "JSON string is empty");
            return defaultValue;
        }
        
        try {
            T result = gson.fromJson(json, classOfT);
            return result != null ? result : defaultValue;
        } catch (JsonSyntaxException e) {
            Log.e(TAG, "JSON syntax error: " + json.substring(0, Math.min(json.length(), 100)));
            return defaultValue;
        } catch (JsonParseException e) {
            Log.e(TAG, "JSON parse error for " + classOfT.getSimpleName());
            return defaultValue;
        } catch (Exception e) {
            Log.e(TAG, "Unexpected error: " + e.getClass().getSimpleName());
            return defaultValue;
        }
    }
    
    /**
     * 带回调的JSON解析
     */
    public static <T> void fromJsonAsync(String json, Class<T> classOfT, 
                                       ParseCallback<T> callback) {
        new Thread(() -> {
            try {
                T result = gson.fromJson(json, classOfT);
                callback.onSuccess(result);
            } catch (Exception e) {
                callback.onError(e);
            }
        }).start();
    }
    
    public interface ParseCallback<T> {
        void onSuccess(T result);
        void onError(Exception e);
    }
}
```

## 使用建议

1. **始终进行异常处理**：永远不要假设JSON是正确的
2. **提供默认值**：对于重要数据，提供合理的默认值
3. **记录错误日志**：方便调试和问题追踪
4. **友好的错误提示**：将技术错误转换为用户能理解的信息
5. **考虑使用验证**：在解析前进行基本验证
6. **使用宽松模式**：`setLenient()`可以处理一些非标准JSON

这样的异常处理机制可以让你的应用更加健壮，避免因JSON解析错误导致的崩溃。