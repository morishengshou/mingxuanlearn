*Thinking...*

> 用户询问如何处理超过long范围的大整数，这是一个很实际的问题。在JSON解析中，JavaScript的Number类型可以表示非常大的数字，但Java的long类型有范围限制（-2^63 到 2^63-1）。需要提供多种解决方案：
> 
> 1. 使用BigInteger或BigDecimal
> 2. 自定义TypeAdapter
> 3. 使用字符串存储
> 4. 预检查和验证
> 5. 错误处理策略
> 
> 我需要提供详细的代码示例和最佳实践。

处理超过`long`范围的大整数是一个重要的安全问题。以下是多种解决方案：

## 1. 使用BigInteger/BigDecimal处理大数

### 基础方案：使用BigInteger

```java
public class Order {
    private String orderId;
    private BigInteger amount;  // 使用BigInteger代替long
    private BigDecimal price;   // 使用BigDecimal处理精确小数
    
    // getter/setter...
}

// 使用示例
String json = "{\"orderId\":\"123\",\"amount\":9223372036854775808}"; // 超过Long.MAX_VALUE
Gson gson = new Gson();
Order order = gson.fromJson(json, Order.class);
System.out.println(order.getAmount()); // 正确输出：9223372036854775808
```

### 自定义BigInteger适配器（带范围检查）

```java
public class SafeBigIntegerAdapter extends TypeAdapter<BigInteger> {
    private static final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);
    private static final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);
    
    @Override
    public void write(JsonWriter out, BigInteger value) throws IOException {
        if (value == null) {
            out.nullValue();
        } else {
            out.value(value);
        }
    }
    
    @Override
    public BigInteger read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        String numberStr = in.nextString();
        try {
            BigInteger value = new BigInteger(numberStr);
            
            // 可选：检查是否在安全范围内
            if (value.compareTo(LONG_MAX) > 0 || value.compareTo(LONG_MIN) < 0) {
                Log.w("SafeBigIntegerAdapter", 
                      "数值超出Long范围: " + value);
            }
            
            return value;
        } catch (NumberFormatException e) {
            throw new JsonParseException("无效的数字格式: " + numberStr, e);
        }
    }
}

// 注册使用
Gson gson = new GsonBuilder()
    .registerTypeAdapter(BigInteger.class, new SafeBigIntegerAdapter())
    .create();
```

## 2. 智能数字处理策略

### 自动选择合适的数字类型

```java
public class SmartNumberAdapter implements JsonDeserializer<Number> {
    @Override
    public Number deserialize(JsonElement json, Type typeOfT, 
                            JsonDeserializationContext context) 
                            throws JsonParseException {
        if (json.isJsonNull()) {
            return null;
        }
        
        if (!json.isJsonPrimitive()) {
            throw new JsonParseException("Expected a number but was " + json);
        }
        
        JsonPrimitive primitive = json.getAsJsonPrimitive();
        String numStr = primitive.getAsString();
        
        try {
            // 1. 尝试解析为Integer
            return Integer.parseInt(numStr);
        } catch (NumberFormatException e1) {
            try {
                // 2. 尝试解析为Long
                return Long.parseLong(numStr);
            } catch (NumberFormatException e2) {
                try {
                    // 3. 尝试解析为Double
                    Double d = Double.parseDouble(numStr);
                    if (!d.isInfinite() && !d.isNaN()) {
                        return d;
                    }
                } catch (NumberFormatException e3) {
                    // 继续下一步
                }
                
                // 4. 使用BigDecimal处理超大数字
                try {
                    return new BigDecimal(numStr);
                } catch (NumberFormatException e4) {
                    throw new JsonParseException("无法解析数字: " + numStr);
                }
            }
        }
    }
}
```

## 3. Long类型安全适配器

### 防止溢出的Long适配器

```java
public class SafeLongAdapter extends TypeAdapter<Long> {
    private static final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);
    private static final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);
    
    public enum OverflowStrategy {
        THROW_EXCEPTION,    // 抛出异常
        USE_MAX_VALUE,      // 使用最大/最小值
        RETURN_NULL,        // 返回null
        USE_BIGINTEGER      // 转换为BigInteger（需要改变字段类型）
    }
    
    private final OverflowStrategy strategy;
    
    public SafeLongAdapter(OverflowStrategy strategy) {
        this.strategy = strategy;
    }
    
    @Override
    public void write(JsonWriter out, Long value) throws IOException {
        if (value == null) {
            out.nullValue();
        } else {
            out.value(value);
        }
    }
    
    @Override
    public Long read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        String numStr = in.nextString();
        
        try {
            // 首先尝试直接解析
            return Long.parseLong(numStr);
        } catch (NumberFormatException e) {
            // 使用BigInteger检查是否溢出
            try {
                BigInteger bigInt = new BigInteger(numStr);
                
                if (bigInt.compareTo(LONG_MAX) > 0) {
                    return handleOverflow(true, numStr, bigInt);
                } else if (bigInt.compareTo(LONG_MIN) < 0) {
                    return handleOverflow(false, numStr, bigInt);
                } else {
                    // 理论上不应该到这里
                    return bigInt.longValue();
                }
            } catch (NumberFormatException ex) {
                throw new JsonParseException("无效的数字格式: " + numStr, ex);
            }
        }
    }
    
    private Long handleOverflow(boolean isPositive, String numStr, 
                               BigInteger value) {
        switch (strategy) {
            case THROW_EXCEPTION:
                throw new JsonParseException(
                    String.format("数值溢出: %s 超出Long范围 [%d, %d]", 
                                numStr, Long.MIN_VALUE, Long.MAX_VALUE));
                
            case USE_MAX_VALUE:
                Log.w("SafeLongAdapter", "数值溢出，使用边界值: " + numStr);
                return isPositive ? Long.MAX_VALUE : Long.MIN_VALUE;
                
            case RETURN_NULL:
                Log.w("SafeLongAdapter", "数值溢出，返回null: " + numStr);
                return null;
                
            default:
                throw new UnsupportedOperationException(
                    "不支持的溢出策略: " + strategy);
        }
    }
}

// 使用示例
Gson gson = new GsonBuilder()
    .registerTypeAdapter(Long.class, 
        new SafeLongAdapter(SafeLongAdapter.OverflowStrategy.USE_MAX_VALUE))
    .registerTypeAdapter(long.class, 
        new SafeLongAdapter(SafeLongAdapter.OverflowStrategy.THROW_EXCEPTION))
    .create();
```

## 4. 混合类型字段支持

### 使用包装类处理可能的大数

```java
public class FlexibleNumber {
    private final Number value;
    private final NumberType type;
    
    public enum NumberType {
        INTEGER, LONG, BIG_INTEGER, BIG_DECIMAL
    }
    
    public FlexibleNumber(Number value) {
        this.value = value;
        if (value instanceof Integer) {
            this.type = NumberType.INTEGER;
        } else if (value instanceof Long) {
            this.type = NumberType.LONG;
        } else if (value instanceof BigInteger) {
            this.type = NumberType.BIG_INTEGER;
        } else {
            this.type = NumberType.BIG_DECIMAL;
        }
    }
    
    public long longValue() {
        if (type == NumberType.BIG_INTEGER || type == NumberType.BIG_DECIMAL) {
            throw new ArithmeticException("数值超出long范围");
        }
        return value.longValue();
    }
    
    public BigInteger bigIntegerValue() {
        if (value instanceof BigInteger) {
            return (BigInteger) value;
        } else if (value instanceof BigDecimal) {
            return ((BigDecimal) value).toBigInteger();
        } else {
            return BigInteger.valueOf(value.longValue());
        }
    }
    
    // 其他转换方法...
}

// 适配器
public class FlexibleNumberAdapter extends TypeAdapter<FlexibleNumber> {
    @Override
    public FlexibleNumber read(JsonReader in) throws IOException {
        if (in.peek() == JsonToken.NULL) {
            in.nextNull();
            return null;
        }
        
        String numStr = in.nextString();
        
        try {
            // 尝试Integer
            return new FlexibleNumber(Integer.parseInt(numStr));
        } catch (NumberFormatException e1) {
            try {
                // 尝试Long
                return new FlexibleNumber(Long.parseLong(numStr));
            } catch (NumberFormatException e2) {
                // 使用BigInteger
                try {
                    return new FlexibleNumber(new BigInteger(numStr));
                } catch (NumberFormatException e3) {
                    // 使用BigDecimal作为最后手段
                    return new FlexibleNumber(new BigDecimal(numStr));
                }
            }
        }
    }
    
    @Override
    public void write(JsonWriter out, FlexibleNumber value) throws IOException {
        if (value == null) {
            out.nullValue();
        } else {
            out.value(value.getValue());
        }
    }
}
```

## 5. 预检查和验证

### JSON预处理器

```java
public class JsonNumberValidator {
    private static final Pattern NUMBER_PATTERN = 
        Pattern.compile("-?\\d+(\\.\\d+)?([eE][+-]?\\d+)?");
    
    public static class ValidationResult {
        public final boolean hasOversizedNumbers;
        public final List<String> oversizedNumbers;
        public final String processedJson;
        
        ValidationResult(boolean hasOversizedNumbers, 
                        List<String> oversizedNumbers, 
                        String processedJson) {
            this.hasOversizedNumbers = hasOversizedNumbers;
            this.oversizedNumbers = oversizedNumbers;
            this.processedJson = processedJson;
        }
    }
    
    public static ValidationResult checkAndProcess(String json) {
        List<String> oversizedNumbers = new ArrayList<>();
        StringBuffer result = new StringBuffer();
        
        Matcher matcher = NUMBER_PATTERN.matcher(json);
        
        while (matcher.find()) {
            String numStr = matcher.group();
            
            // 跳过小数
            if (numStr.contains(".") || numStr.contains("e") || 
                numStr.contains("E")) {
                continue;
            }
            
            try {
                Long.parseLong(numStr);
            } catch (NumberFormatException e) {
                // 发现超大整数
                oversizedNumbers.add(numStr);
                
                // 将数字用引号包裹，转为字符串
                matcher.appendReplacement(result, "\"" + numStr + "\"");
                continue;
            }
            
            matcher.appendReplacement(result, numStr);
        }
        matcher.appendTail(result);
        
        return new ValidationResult(
            !oversizedNumbers.isEmpty(), 
            oversizedNumbers, 
            result.toString()
        );
    }
}

// 使用示例
public class SafeJsonParser {
    public static <T> T parseWithValidation(String json, Class<T> clazz) {
        // 1. 预检查
        JsonNumberValidator.ValidationResult validation = 
            JsonNumberValidator.checkAndProcess(json);
        
        if (validation.hasOversizedNumbers) {
            Log.w("SafeJsonParser", "发现超大数字: " + 
                  validation.oversizedNumbers);
            
            // 可以选择：
            // - 使用处理后的JSON（数字转为字符串）
            // - 抛出异常
            // - 使用特殊的Gson配置
        }
        
        // 2. 使用安全的Gson配置解析
        Gson gson = createSafeGson();
        return gson.fromJson(json, clazz);
    }
    
    private static Gson createSafeGson() {
        return new GsonBuilder()
            .registerTypeAdapter(Long.class, 
                new SafeLongAdapter(SafeLongAdapter.OverflowStrategy.USE_MAX_VALUE))
            .registerTypeAdapter(long.class, 
                new SafeLongAdapter(SafeLongAdapter.OverflowStrategy.USE_MAX_VALUE))
            .setLenient()
            .create();
    }
}
```

## 6. 实际应用示例

### 金融场景的安全处理

```java
public class FinancialTransaction {
    private String transactionId;
    
    @JsonAdapter(BigDecimalAdapter.class)
    private BigDecimal amount;  // 金额必须精确
    
    @JsonAdapter(SafeLongAdapter.class)
    private Long timestamp;
    
    private String currency;
    
    // 自定义BigDecimal适配器，确保精度
    static class BigDecimalAdapter extends TypeAdapter<BigDecimal> {
        @Override
        public BigDecimal read(JsonReader in) throws IOException {
            if (in.peek() == JsonToken.NULL) {
                in.nextNull();
                return null;
            }
            
            String value = in.nextString();
            try {
                BigDecimal decimal = new BigDecimal(value);
                
                // 检查范围（可选）
                BigDecimal maxAmount = new BigDecimal("999999999999999999.99");
                if (decimal.abs().compareTo(maxAmount) > 0) {
                    throw new JsonParseException("金额超出允许范围: " + value);
                }
                
                // 检查小数位数
                if (decimal.scale() > 2) {
                    // 四舍五入到2位小数
                    decimal = decimal.setScale(2, RoundingMode.HALF_UP);
                }
                
                return decimal;
            } catch (NumberFormatException e) {
                throw new JsonParseException("无效的金额格式: " + value, e);
            }
        }
        
        @Override
        public void write(JsonWriter out, BigDecimal value) throws IOException {
            if (value == null) {
                out.nullValue();
            } else {
                // 确保输出格式一致
                out.value(value.toPlainString());
            }
        }
    }
}
```

## 最佳实践建议

1. **明确数据范围**：在设计API时就明确数字的范围限制
2. **使用合适的类型**：
   - 金额：使用`BigDecimal`
   - 大整数ID：使用`String`或`BigInteger`
   - 普通计数：使用`Long`并做溢出检查
3. **文档说明**：在API文档中明确说明数字范围限制
4. **客户端验证**：在发送请求前验证数字范围
5. **服务端双重验证**：即使客户端验证了，服务端也要再次验证
6. **监控告警**：记录所有溢出情况，及时发现问题

这样可以有效防止因大数字导致的数据错误或安全问题。