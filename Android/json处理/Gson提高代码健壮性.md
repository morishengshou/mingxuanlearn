*Thinking...*

> 用户想了解更多关于处理Gson异常和提高代码健壮性的方法。我已经介绍了基本的异常处理，现在应该提供一些更高级、更全面的方法，包括：
> 
> 1. 防御性编程技巧
> 2. 使用注解和自定义策略
> 3. 数据验证框架
> 4. 容错机制
> 5. 监控和上报
> 6. 单元测试
> 7. 其他高级技巧
> 
> 我应该提供实用的代码示例和最佳实践。

当然！除了基本的异常处理，还有很多方法可以提高Gson解析的健壮性：

## 1. 防御性编程策略

### 使用@JsonAdapter注解进行字段级保护

```java
public class User {
    private String name;
    
    @JsonAdapter(SafeIntegerAdapter.class)
    private Integer age;
    
    @JsonAdapter(SafeDateAdapter.class)
    private Date birthDate;
    
    @JsonAdapter(SafeListAdapter.class)
    private List<String> hobbies;
}

// 安全的整数适配器
public class SafeIntegerAdapter extends TypeAdapter<Integer> {
    @Override
    public Integer read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        try {
            // 尝试直接读取整数
            return in.nextInt();
        } catch (NumberFormatException e) {
            // 尝试作为字符串读取并转换
            try {
                String value = in.nextString();
                return Integer.parseInt(value);
            } catch (NumberFormatException e2) {
                // 返回默认值
                return 0;
            }
        }
    }
    
    @Override
    public void write(JsonWriter out, Integer value) throws IOException {
        out.value(value);
    }
}

// 安全的列表适配器
public class SafeListAdapter extends TypeAdapter<List<String>> {
    @Override
    public List<String> read(JsonReader in) throws IOException {
        List<String> list = new ArrayList<>();
        
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return list;
        }
        
        // 处理可能是单个字符串的情况
        if (in.peek() == JsonToken.STRING) {
            list.add(in.nextString());
            return list;
        }
        
        // 正常的数组处理
        try {
            in.beginArray();
            while (in.hasNext()) {
                if (in.peek() == JsonToken.STRING) {
                    list.add(in.nextString());
                } else {
                    in.skipValue();  // 跳过非字符串元素
                }
            }
            in.endArray();
        } catch (IllegalStateException e) {
            // 如果不是数组，返回空列表
        }
        
        return list;
    }
    
    @Override
    public void write(JsonWriter out, List<String> value) throws IOException {
        if (value == null) {
            out.nullValue();
            return;
        }
        
        out.beginArray();
        for (String item : value) {
            out.value(item);
        }
        out.endArray();
    }
}
```

## 2. 使用ExclusionStrategy过滤策略

```java
public class RobustGsonBuilder {
    public static Gson create() {
        return new GsonBuilder()
            .addDeserializationExclusionStrategy(new ExclusionStrategy() {
                @Override
                public boolean shouldSkipField(FieldAttributes f) {
                    // 跳过标记为忽略的字段
                    return f.getAnnotation(GsonIgnore.class) != null;
                }
                
                @Override
                public boolean shouldSkipClass(Class<?> clazz) {
                    // 跳过特定的类
                    return clazz.equals(Thread.class);
                }
            })
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create();
    }
}

// 自定义注解
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface GsonIgnore {
}
```

## 3. 数据验证框架集成

```java
// 使用Bean Validation注解
public class ValidatedUser {
    @NotNull
    @Size(min = 1, max = 50)
    private String name;
    
    @Min(0)
    @Max(150)
    private Integer age;
    
    @Email
    private String email;
    
    @Pattern(regexp = "^1[3-9]\\d{9}$")
    private String phone;
}

// 验证工具类
public class GsonValidator {
    private static final Validator validator = 
        Validation.buildDefaultValidatorFactory().getValidator();
    
    public static <T> ParseResult<T> parseAndValidate(String json, Class<T> clazz) {
        ParseResult<T> result = new ParseResult<>();
        
        try {
            // 1. 解析JSON
            T object = new Gson().fromJson(json, clazz);
            result.setData(object);
            
            // 2. 验证数据
            Set<ConstraintViolation<T>> violations = validator.validate(object);
            if (!violations.isEmpty()) {
                for (ConstraintViolation<T> violation : violations) {
                    result.addError(violation.getPropertyPath() + ": " + 
                                  violation.getMessage());
                }
            }
            
            result.setSuccess(violations.isEmpty());
        } catch (Exception e) {
            result.setSuccess(false);
            result.addError("解析错误: " + e.getMessage());
        }
        
        return result;
    }
}

class ParseResult<T> {
    private boolean success;
    private T data;
    private List<String> errors = new ArrayList<>();
    // getter/setter...
}
```

## 4. 智能类型推断

```java
public class SmartParser {
    private static final Gson gson = new Gson();
    
    /**
     * 智能解析，自动处理类型不匹配
     */
    public static Object parseSmartValue(JsonElement element) {
        if (element.isJsonNull()) {
            return null;
        }
        
        if (element.isJsonPrimitive()) {
            JsonPrimitive primitive = element.getAsJsonPrimitive();
            
            // 尝试按优先级解析
            if (primitive.isBoolean()) {
                return primitive.getAsBoolean();
            }
            
            if (primitive.isNumber()) {
                Number number = primitive.getAsNumber();
                // 根据大小选择合适的类型
                if (number.doubleValue() == number.intValue()) {
                    return number.intValue();
                }
                return number.doubleValue();
            }
            
            if (primitive.isString()) {
                String str = primitive.getAsString();
                // 尝试解析为其他类型
                try {
                    return Integer.parseInt(str);
                } catch (NumberFormatException e1) {
                    try {
                        return Double.parseDouble(str);
                    } catch (NumberFormatException e2) {
                        // 检查是否是布尔值
                        if ("true".equalsIgnoreCase(str) || 
                            "false".equalsIgnoreCase(str)) {
                            return Boolean.parseBoolean(str);
                        }
                        return str;
                    }
                }
            }
        }
        
        if (element.isJsonArray()) {
            return parseArray(element.getAsJsonArray());
        }
        
        if (element.isJsonObject()) {
            return parseObject(element.getAsJsonObject());
        }
        
        return null;
    }
    
    private static List<Object> parseArray(JsonArray array) {
        List<Object> list = new ArrayList<>();
        for (JsonElement element : array) {
            list.add(parseSmartValue(element));
        }
        return list;
    }
    
    private static Map<String, Object> parseObject(JsonObject object) {
        Map<String, Object> map = new HashMap<>();
        for (Map.Entry<String, JsonElement> entry : object.entrySet()) {
            map.put(entry.getKey(), parseSmartValue(entry.getValue()));
        }
        return map;
    }
}
```

## 5. 降级处理策略

```java
public class FallbackParser {
    private static final List<JsonParser> parsers = Arrays.asList(
        new StrictJsonParser(),
        new LenientJsonParser(),
        new CustomFormatParser()
    );
    
    public static <T> T parseWithFallback(String json, Class<T> clazz) {
        List<Exception> errors = new ArrayList<>();
        
        // 尝试多种解析策略
        for (JsonParser parser : parsers) {
            try {
                return parser.parse(json, clazz);
            } catch (Exception e) {
                errors.add(e);
            }
        }
        
        // 所有策略都失败，记录错误并返回默认值
        logErrors(errors);
        return createDefaultInstance(clazz);
    }
    
    interface JsonParser {
        <T> T parse(String json, Class<T> clazz) throws Exception;
    }
    
    static class StrictJsonParser implements JsonParser {
        private final Gson gson = new Gson();
        
        @Override
        public <T> T parse(String json, Class<T> clazz) throws Exception {
            return gson.fromJson(json, clazz);
        }
    }
    
    static class LenientJsonParser implements JsonParser {
        private final Gson gson = new GsonBuilder()
            .setLenient()
            .create();
            
        @Override
        public <T> T parse(String json, Class<T> clazz) throws Exception {
            // 预处理JSON字符串
            json = json.replaceAll("'", "\"")  // 单引号转双引号
                      .replaceAll(",\\s*}", "}")  // 移除末尾逗号
                      .replaceAll(",\\s*]", "]");
            return gson.fromJson(json, clazz);
        }
    }
}
```

## 6. 监控和错误上报

```java
public class MonitoredGsonParser {
    private static final Gson gson = new Gson();
    private static final ErrorReporter reporter = new ErrorReporter();
    
    public static <T> T parseWithMonitoring(String json, Class<T> clazz, 
                                          String source) {
        long startTime = System.currentTimeMillis();
        ParseMetrics metrics = new ParseMetrics(source, clazz.getSimpleName());
        
        try {
            T result = gson.fromJson(json, clazz);
            metrics.setSuccess(true);
            metrics.setDuration(System.currentTimeMillis() - startTime);
            
            // 检查解析质量
            checkParseQuality(json, result, metrics);
            
            return result;
        } catch (Exception e) {
            metrics.setSuccess(false);
            metrics.setError(e);
            metrics.setDuration(System.currentTimeMillis() - startTime);
            
            // 上报错误
            reporter.report(metrics, json);
            
            throw new ParseException("解析失败: " + e.getMessage(), e);
        } finally {
            // 记录指标
            MetricsCollector.record(metrics);
        }
    }
    
    private static void checkParseQuality(String json, Object result, 
                                        ParseMetrics metrics) {
        // 检查是否有大量null值
        int nullCount = countNulls(result);
        int totalFields = countTotalFields(result);
        
        if (totalFields > 0 && nullCount > totalFields * 0.5) {
            metrics.addWarning("超过50%的字段为null");
        }
        
        // 检查JSON大小
        if (json.length() > 1024 * 1024) {  // 1MB
            metrics.addWarning("JSON大小超过1MB");
        }
    }
}
```

## 7. 单元测试增强

```java
@RunWith(JUnit4.class)
public class GsonRobustnessTest {
    private Gson gson = new Gson();
    
    @Test
    public void testMalformedJson() {
        String[] malformedJsons = {
            "{name:value}",  // 缺少引号
            "{'name':'value'}",  // 单引号
            "{\"name\":\"value\",}",  // 尾部逗号
            "{\"name\":}",  // 缺少值
            "{\"name\":undefined}",  // undefined值
            "NaN",  // 非JSON
            "",  // 空字符串
            null  // null
        };
        
        for (String json : malformedJsons) {
            try {
                TestObject obj = SafeParser.parse(json, TestObject.class);
                assertNotNull("应该返回对象而不是null", obj);
            } catch (Exception e) {
                fail("不应该抛出异常: " + e.getMessage());
            }
        }
    }
    
    @Test
    public void testTypeMismatch() {
        class TestData {
            Integer number;
            Boolean flag;
            List<String> list;
        }
        
        // 各种类型不匹配的情况
        String[] testCases = {
            "{\"number\":\"123\"}",  // 字符串转数字
            "{\"number\":12.5}",  // 浮点转整数
            "{\"flag\":\"true\"}",  // 字符串转布尔
            "{\"flag\":1}",  // 数字转布尔
            "{\"list\":\"item\"}",  // 字符串转列表
            "{\"list\":null}"  // null列表
        };
        
        for (String json : testCases) {
            TestData data = RobustParser.parse(json, TestData.class);
            assertNotNull("解析结果不应为null", data);
        }
    }
}
```

## 8. 配置化处理

```java
public class GsonConfig {
    private boolean lenient = true;
    private boolean serializeNulls = false;
    private boolean escapeHtml = true;
    private int maxDepth = 100;
    private long maxJsonLength = 10 * 1024 * 1024;  // 10MB
    
    public Gson build() {
        GsonBuilder builder = new GsonBuilder();
        
        if (lenient) builder.setLenient();
        if (serializeNulls) builder.serializeNulls();
        if (!escapeHtml) builder.disableHtmlEscaping();
        
        // 添加深度限制
        builder.registerTypeAdapterFactory(new DepthLimitFactory(maxDepth));
        
        return builder.create();
    }
}

// 深度限制适配器
public class DepthLimitFactory implements TypeAdapterFactory {
    private final int maxDepth;
    private final ThreadLocal<Integer> currentDepth = 
        ThreadLocal.withInitial(() -> 0);
    
    public DepthLimitFactory(int maxDepth) {
        this.maxDepth = maxDepth;
    }
    
    @Override
    public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type) {
        TypeAdapter<T> delegate = gson.getDelegateAdapter(this, type);
        
        return new TypeAdapter<T>() {
            @Override
            public void write(JsonWriter out, T value) throws IOException {
                delegate.write(out, value);
            }
            
            @Override
            public T read(JsonReader in) throws IOException {
                int depth = currentDepth.get();
                if (depth > maxDepth) {
                    throw new JsonParseException("超过最大深度限制: " + maxDepth);
                }
                
                currentDepth.set(depth + 1);
                try {
                    return delegate.read(in);
                } finally {
                    currentDepth.set(depth);
                }
            }
        };
    }
}
```

## 最佳实践总结

1. **分层防御**：在多个层面进行保护，不要依赖单一机制
2. **优雅降级**：提供多种解析策略，逐级降级
3. **监控告警**：记录解析错误，及时发现问题
4. **性能考虑**：避免过度防御影响性能
5. **测试覆盖**：编写全面的异常测试用例
6. **文档完善**：记录已知的限制和处理策略

这些方法可以根据项目需求选择性使用，构建一个健壮的JSON解析系统。