*Thinking...*

> 用户提到@SerializedName注解不能处理整数和枚举值的转换，这是对的。@SerializedName只能处理字符串到枚举的映射，而JSON中的数字类型（整数）无法直接通过@SerializedName转换。我需要提供几种解决方案来处理整数到枚举的转换。

你说得对，`@SerializedName`注解只能处理字符串到枚举的映射，无法直接处理整数到枚举的转换。以下是几种解决方案：

## 1. 自定义TypeAdapter（推荐）

这是最灵活和类型安全的方法：

```java
// 枚举定义
public enum OrderStatus {
    UNPAID(0, "未支付"),
    PAID(1, "已支付"),
    SHIPPED(2, "已发货"),
    COMPLETED(3, "已完成");
    
    private final int code;
    private final String desc;
    
    OrderStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }
    
    public int getCode() {
        return code;
    }
    
    public static OrderStatus fromCode(int code) {
        for (OrderStatus status : values()) {
            if (status.code == code) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown status code: " + code);
    }
}

// TypeAdapter实现
public class OrderStatusTypeAdapter extends TypeAdapter<OrderStatus> {
    @Override
    public void write(JsonWriter out, OrderStatus value) throws IOException {
        if (value == null) {
            out.nullValue();
        } else {
            out.value(value.getCode());
        }
    }

    @Override
    public OrderStatus read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        int code = in.nextInt();
        return OrderStatus.fromCode(code);
    }
}

// 使用
Gson gson = new GsonBuilder()
    .registerTypeAdapter(OrderStatus.class, new OrderStatusTypeAdapter())
    .create();

// JSON: {"orderId":"12345","status":1}
// 会正确转换为 OrderStatus.PAID
```

## 2. 使用JsonDeserializer

更简单但功能略少的方法：

```java
public class OrderStatusDeserializer implements JsonDeserializer<OrderStatus> {
    @Override
    public OrderStatus deserialize(JsonElement json, Type typeOfT, 
                                 JsonDeserializationContext context) 
                                 throws JsonParseException {
        if (json.isJsonNull()) {
            return null;
        }
        
        int code = json.getAsInt();
        try {
            return OrderStatus.fromCode(code);
        } catch (IllegalArgumentException e) {
            // 返回默认值或抛出异常
            return OrderStatus.UNPAID;
        }
    }
}

// 如果也需要序列化，还需要实现JsonSerializer
public class OrderStatusSerializer implements JsonSerializer<OrderStatus> {
    @Override
    public JsonElement serialize(OrderStatus src, Type typeOfSrc, 
                               JsonSerializationContext context) {
        if (src == null) {
            return JsonNull.INSTANCE;
        }
        return new JsonPrimitive(src.getCode());
    }
}

// 使用
Gson gson = new GsonBuilder()
    .registerTypeAdapter(OrderStatus.class, new OrderStatusDeserializer())
    .registerTypeAdapter(OrderStatus.class, new OrderStatusSerializer())
    .create();
```

## 3. 通用枚举TypeAdapter

创建一个可复用的通用适配器：

```java
// 定义接口
public interface IntegerEnum {
    int getCode();
}

// 枚举实现接口
public enum PaymentStatus implements IntegerEnum {
    PENDING(0),
    SUCCESS(1),
    FAILED(2);
    
    private final int code;
    
    PaymentStatus(int code) {
        this.code = code;
    }
    
    @Override
    public int getCode() {
        return code;
    }
    
    public static PaymentStatus fromCode(int code) {
        for (PaymentStatus status : values()) {
            if (status.code == code) {
                return status;
            }
        }
        return null;
    }
}

// 通用TypeAdapter
public class IntegerEnumTypeAdapter<T extends Enum<T> & IntegerEnum> 
        extends TypeAdapter<T> {
    
    private final Class<T> enumClass;
    private final Function<Integer, T> fromCode;
    
    public IntegerEnumTypeAdapter(Class<T> enumClass, 
                                 Function<Integer, T> fromCode) {
        this.enumClass = enumClass;
        this.fromCode = fromCode;
    }
    
    @Override
    public void write(JsonWriter out, T value) throws IOException {
        if (value == null) {
            out.nullValue();
        } else {
            out.value(value.getCode());
        }
    }
    
    @Override
    public T read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        int code = in.nextInt();
        T result = fromCode.apply(code);
        if (result == null) {
            throw new JsonParseException("Unknown enum code: " + code + 
                                       " for " + enumClass.getSimpleName());
        }
        return result;
    }
}

// 使用
Gson gson = new GsonBuilder()
    .registerTypeAdapter(PaymentStatus.class, 
        new IntegerEnumTypeAdapter<>(PaymentStatus.class, PaymentStatus::fromCode))
    .create();
```

## 4. 使用TypeAdapterFactory（批量处理）

如果有多个枚举需要处理：

```java
public class IntegerEnumTypeAdapterFactory implements TypeAdapterFactory {
    @Override
    public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type) {
        Class<T> rawType = (Class<T>) type.getRawType();
        
        if (!rawType.isEnum() || !IntegerEnum.class.isAssignableFrom(rawType)) {
            return null;
        }
        
        return new TypeAdapter<T>() {
            @Override
            public void write(JsonWriter out, T value) throws IOException {
                if (value == null) {
                    out.nullValue();
                } else {
                    out.value(((IntegerEnum) value).getCode());
                }
            }
            
            @Override
            public T read(JsonReader in) throws IOException {
                if (in.peek() == JsonToken.NULL) {
                    in.nextNull();
                    return null;
                }
                
                int code = in.nextInt();
                // 使用反射查找fromCode方法
                try {
                    Method method = rawType.getMethod("fromCode", int.class);
                    return (T) method.invoke(null, code);
                } catch (Exception e) {
                    throw new JsonParseException("Cannot deserialize " + 
                                               rawType.getName(), e);
                }
            }
        };
    }
}

// 使用
Gson gson = new GsonBuilder()
    .registerTypeAdapterFactory(new IntegerEnumTypeAdapterFactory())
    .create();
```

## 5. 实用工具类

创建一个工具类简化使用：

```java
public class GsonUtil {
    private static final Gson GSON;
    
    static {
        GsonBuilder builder = new GsonBuilder();
        
        // 注册所有需要整数转换的枚举
        builder.registerTypeAdapter(OrderStatus.class, 
            createIntEnumAdapter(OrderStatus.class, OrderStatus::fromCode));
        builder.registerTypeAdapter(PaymentStatus.class, 
            createIntEnumAdapter(PaymentStatus.class, PaymentStatus::fromCode));
        
        GSON = builder.create();
    }
    
    private static <T extends Enum<T>> TypeAdapter<T> createIntEnumAdapter(
            Class<T> enumClass, Function<Integer, T> fromCode) {
        return new TypeAdapter<T>() {
            @Override
            public void write(JsonWriter out, T value) throws IOException {
                if (value == null) {
                    out.nullValue();
                } else {
                    out.value(((IntegerEnum) value).getCode());
                }
            }
            
            @Override
            public T read(JsonReader in) throws IOException {
                if (in.peek() == JsonToken.NULL) {
                    in.nextNull();
                    return null;
                }
                return fromCode.apply(in.nextInt());
            }
        };
    }
    
    public static <T> T fromJson(String json, Class<T> classOfT) {
        return GSON.fromJson(json, classOfT);
    }
    
    public static String toJson(Object src) {
        return GSON.toJson(src);
    }
}
```

## 使用建议

1. **优先使用TypeAdapter**：性能更好，双向转换支持。
2. **统一处理方式**：在项目中保持一致的枚举处理方式。
3. **添加容错机制**：处理未知的整数值，返回默认值或抛出明确的异常。
4. **考虑使用Moshi**：如果枚举转换需求很多，可以考虑使用Moshi库，它对枚举的支持更灵活。

这些方法可以完美解决整数到枚举的转换问题，选择哪种方案取决于你的具体需求和项目规模。