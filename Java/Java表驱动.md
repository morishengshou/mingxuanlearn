*Thinking...*

> **提供Java字符串-函数哈希表示例**

当然可以。下面给你一个**可直接运行**的 Java Demo，核心思路就是：

1. 用 `Map<String, Function>`（或 `Consumer`）保存“字符串 -> 函数”映射  
2. 通过 `map.get(key)` 取出函数  
3. 调用函数执行逻辑，替代一长串 `if-else`

---

### Demo：字符串指令分发（替代 if-else）

```java
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

public class StringFunctionDispatchDemo {

    // 你可以把它理解为请求对象（函数执行时需要的参数）
    static class Request {
        String user;
        int amount;

        Request(String user, int amount) {
            this.user = user;
            this.amount = amount;
        }
    }

    // 字符串 -> 函数（输入Request，返回String结果）
    private final Map<String, Function<Request, String>> handlerMap = new HashMap<>();

    public StringFunctionDispatchDemo() {
        // 注册各种“命令”
        handlerMap.put("CREATE", req -> "创建用户成功: " + req.user);
        handlerMap.put("PAY", req -> "扣款成功: " + req.user + "，金额=" + req.amount);
        handlerMap.put("REFUND", req -> "退款成功: " + req.user + "，金额=" + req.amount);
    }

    // 分发执行：根据字符串找到函数并执行
    public String dispatch(String action, Request request) {
        Function<Request, String> handler = handlerMap.get(action);

        if (handler == null) {
            return "未知操作: " + action;
        }
        return handler.apply(request);
    }

    public static void main(String[] args) {
        StringFunctionDispatchDemo demo = new StringFunctionDispatchDemo();

        System.out.println(demo.dispatch("CREATE", new Request("Alice", 0)));
        System.out.println(demo.dispatch("PAY", new Request("Bob", 100)));
        System.out.println(demo.dispatch("REFUND", new Request("Cindy", 50)));
        System.out.println(demo.dispatch("DELETE", new Request("David", 0))); // 未注册操作
    }
}
```

---

### 你会得到的好处

- **可扩展**：新增操作只要 `handlerMap.put("NEW_ACTION", func)`，不用改原有分支结构  
- **更清晰**：避免几十行 `if-else if-else`  
- **更易维护**：每个操作逻辑都独立

---

如果你愿意，我还可以给你下一版：

- 用 `getOrDefault` 写法（更简洁）
- 用 `Runnable` / `Consumer` / `BiFunction` 的对比版本
- 结合 Spring（如 `@Component + Map` 自动注入）做企业项目常用实现。

# 优化版本

*Thinking...*

> **Providing optimized comparison code**

太好了 👍  
下面给你一个“**优化 + 对比**”版本：一次性演示 `if-else`、`Map + Function(getOrDefault)`、`Map + Consumer`、`Map + BiFunction` 四种写法。

你可以直接复制运行（一个文件就行）。

```java
import java.util.HashMap;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Consumer;
import java.util.function.Function;

public class DispatchCompareDemo {

    // ===== 通用请求对象 =====
    static class Request {
        String user;
        int amount;

        Request(String user, int amount) {
            this.user = user;
            this.amount = amount;
        }

        @Override
        public String toString() {
            return "Request{user='" + user + "', amount=" + amount + "}";
        }
    }

    // ===== 1) 传统 if-else 写法 =====
    static class IfElseDispatcher {
        public String dispatch(String action, Request req) {
            String act = normalize(action);

            if ("CREATE".equals(act)) {
                return "IF_ELSE -> 创建用户成功: " + req.user;
            } else if ("PAY".equals(act)) {
                return "IF_ELSE -> 扣款成功: " + req.user + "，金额=" + req.amount;
            } else if ("REFUND".equals(act)) {
                return "IF_ELSE -> 退款成功: " + req.user + "，金额=" + req.amount;
            } else {
                return "IF_ELSE -> 未知操作: " + action;
            }
        }
    }

    // ===== 2) 推荐：Map + Function + getOrDefault（有返回值） =====
    static class FunctionDispatcher {
        private final Map<String, Function<Request, String>> handlers = new HashMap<>();

        // 默认处理器，避免 null 判断
        private final Function<Request, String> defaultHandler =
                req -> "FUNCTION -> 未知操作，入参: " + req;

        public FunctionDispatcher() {
            register("CREATE", req -> "FUNCTION -> 创建用户成功: " + req.user);
            register("PAY", req -> "FUNCTION -> 扣款成功: " + req.user + "，金额=" + req.amount);
            register("REFUND", req -> "FUNCTION -> 退款成功: " + req.user + "，金额=" + req.amount);
        }

        public void register(String action, Function<Request, String> handler) {
            handlers.put(normalize(action), handler);
        }

        public String dispatch(String action, Request req) {
            return handlers
                    .getOrDefault(normalize(action), defaultHandler)
                    .apply(req);
        }
    }

    // ===== 3) Map + Consumer（无返回值，偏“执行动作”） =====
    static class ConsumerDispatcher {
        private final Map<String, Consumer<Request>> handlers = new HashMap<>();

        private final Consumer<Request> defaultHandler =
                req -> System.out.println("CONSUMER -> 未知操作，入参: " + req);

        public ConsumerDispatcher() {
            register("CREATE", req -> System.out.println("CONSUMER -> 创建用户: " + req.user));
            register("PAY", req -> System.out.println("CONSUMER -> 扣款: " + req.user + ", " + req.amount));
            register("REFUND", req -> System.out.println("CONSUMER -> 退款: " + req.user + ", " + req.amount));
        }

        public void register(String action, Consumer<Request> handler) {
            handlers.put(normalize(action), handler);
        }

        public void dispatch(String action, Request req) {
            handlers.getOrDefault(normalize(action), defaultHandler).accept(req);
        }
    }

    // ===== 4) Map + BiFunction（需要多个输入参数时更灵活） =====
    static class BiFunctionDispatcher {
        // 例子：额外传一个 traceId 作为第二个参数
        private final Map<String, BiFunction<Request, String, String>> handlers = new HashMap<>();

        private final BiFunction<Request, String, String> defaultHandler =
                (req, traceId) -> "BIFUNCTION[" + traceId + "] -> 未知操作: " + req;

        public BiFunctionDispatcher() {
            register("CREATE", (req, traceId) ->
                    "BIFUNCTION[" + traceId + "] -> 创建用户成功: " + req.user);
            register("PAY", (req, traceId) ->
                    "BIFUNCTION[" + traceId + "] -> 扣款成功: " + req.user + ", " + req.amount);
            register("REFUND", (req, traceId) ->
                    "BIFUNCTION[" + traceId + "] -> 退款成功: " + req.user + ", " + req.amount);
        }

        public void register(String action, BiFunction<Request, String, String> handler) {
            handlers.put(normalize(action), handler);
        }

        public String dispatch(String action, Request req, String traceId) {
            return handlers.getOrDefault(normalize(action), defaultHandler).apply(req, traceId);
        }
    }

    // ===== 工具：统一处理大小写、空格 =====
    private static String normalize(String action) {
        return action == null ? "" : action.trim().toUpperCase();
    }

    // ===== 演示入口 =====
    public static void main(String[] args) {
        Request req1 = new Request("Alice", 0);
        Request req2 = new Request("Bob", 100);
        Request req3 = new Request("Cindy", 50);
        Request req4 = new Request("David", 20);

        System.out.println("=== 1) if-else ===");
        IfElseDispatcher ifElse = new IfElseDispatcher();
        System.out.println(ifElse.dispatch("create", req1));
        System.out.println(ifElse.dispatch("pay", req2));
        System.out.println(ifElse.dispatch("delete", req4));

        System.out.println("\n=== 2) Map + Function（推荐） ===");
        FunctionDispatcher functionDispatcher = new FunctionDispatcher();
        System.out.println(functionDispatcher.dispatch("CREATE", req1));
        System.out.println(functionDispatcher.dispatch("REFUND", req3));
        System.out.println(functionDispatcher.dispatch("DELETE", req4));

        System.out.println("\n=== 3) Map + Consumer（无返回值） ===");
        ConsumerDispatcher consumerDispatcher = new ConsumerDispatcher();
        consumerDispatcher.dispatch("pay", req2);
        consumerDispatcher.dispatch("delete", req4);

        System.out.println("\n=== 4) Map + BiFunction（多参数） ===");
        BiFunctionDispatcher biFunctionDispatcher = new BiFunctionDispatcher();
        System.out.println(biFunctionDispatcher.dispatch("REFUND", req3, "T-1001"));
        System.out.println(biFunctionDispatcher.dispatch("UNKNOWN", req4, "T-1002"));
    }
}
```

---

### 怎么选（实战建议）

- **有返回值**：优先 `Map<String, Function<Req, Resp>>`  
- **只执行动作，不关心返回**：`Map<String, Consumer<Req>>`  
- **需要多个输入参数**：`BiFunction` / 自定义函数式接口  
- **高并发动态注册**：把 `HashMap` 换成 `ConcurrentHashMap`

---

如果你要，我下一步可以给你一个**Spring Boot 项目版**：  
自动扫描每个 handler（按注解注册），启动时组装成 `Map`，业务层直接 `dispatch(action, req)`。这样最接近企业实际项目。

下面给一个**不使用反射**、**统一入参对象**的“表驱动”可运行示例：用 `Map<String, Function<Request, Response>>` 来替代 `if-else/switch`。  

把代码保存为 `TableDrivenNoReflectionDemo.java`，直接运行。

```java
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

public class TableDrivenNoReflectionDemo {

    // 统一入参
    public static class Request {
        private final String command;
        private final Map<String, Object> params;

        public Request(String command, Map<String, Object> params) {
            this.command = command;
            this.params = params == null ? new HashMap<>() : params;
        }

        public String command() { return command; }

        public String getString(String key) {
            Object v = params.get(key);
            if (v == null) return null;
            return String.valueOf(v);
        }

        public int getInt(String key) {
            Object v = params.get(key);
            if (v instanceof Integer) return (Integer) v;
            if (v instanceof Number) return ((Number) v).intValue();
            if (v instanceof String) return Integer.parseInt((String) v);
            throw new IllegalArgumentException("Param '" + key + "' is not an int: " + v);
        }

        public Object get(String key) { return params.get(key); }

        public static Request of(String command, Object... kv) {
            if (kv.length % 2 != 0) {
                throw new IllegalArgumentException("kv must be even length: key,value,key,value...");
            }
            Map<String, Object> p = new HashMap<>();
            for (int i = 0; i < kv.length; i += 2) {
                String k = String.valueOf(kv[i]);
                Object v = kv[i + 1];
                p.put(k, v);
            }
            return new Request(command, p);
        }
    }

    // 统一返回
    public static class Response {
        public final boolean ok;
        public final String message;
        public final Object data;

        private Response(boolean ok, String message, Object data) {
            this.ok = ok;
            this.message = message;
            this.data = data;
        }

        public static Response ok(Object data) {
            return new Response(true, "OK", data);
        }

        public static Response fail(String message) {
            return new Response(false, message, null);
        }

        @Override
        public String toString() {
            return "Response{ok=" + ok + ", message='" + message + "', data=" + data + "}";
        }
    }

    // 表驱动分发器：String -> Handler(Request)->Response
    public static class Dispatcher {
        private final Map<String, Function<Request, Response>> table = new HashMap<>();

        public Dispatcher register(String command, Function<Request, Response> handler) {
            table.put(command, handler);
            return this;
        }

        public Response dispatch(Request req) {
            Function<Request, Response> handler = table.get(req.command());
            if (handler == null) return Response.fail("Unknown command: " + req.command());
            try {
                return handler.apply(req);
            } catch (Exception e) {
                return Response.fail("Handler error: " + e.getMessage());
            }
        }
    }

    // 业务逻辑（可以是 service / usecase / handler 类）
    public static class Service {
        public Response hello(Request req) {
            return Response.ok("hello");
        }

        public Response echo(Request req) {
            String msg = req.getString("msg");
            if (msg == null) return Response.fail("missing param: msg");
            return Response.ok("echo: " + msg);
        }

        public Response add(Request req) {
            int a = req.getInt("a");
            int b = req.getInt("b");
            return Response.ok(a + b);
        }
    }

    public static void main(String[] args) {
        Service service = new Service();

        // 建表：命令字符串 -> 处理函数
        Dispatcher dispatcher = new Dispatcher()
                .register("HELLO", service::hello)
                .register("ECHO",  service::echo)
                .register("ADD",   service::add);

        // 统一入参 Request
        System.out.println(dispatcher.dispatch(Request.of("HELLO")));
        System.out.println(dispatcher.dispatch(Request.of("ECHO", "msg", "表驱动，无反射")));
        System.out.println(dispatcher.dispatch(Request.of("ADD", "a", 10, "b", 20)));

        // 错误示例
        System.out.println(dispatcher.dispatch(Request.of("UNKNOWN")));
        System.out.println(dispatcher.dispatch(Request.of("ADD", "a", "x", "b", 2))); // 参数类型不对
    }
}
```

### 这个方案的优点
- **无反射**：类型安全更好、性能更稳、可重构。
- **统一入参**：所有 handler 都是 `Function<Request, Response>`，扩展新命令只需 `register` 一行。
- **便于做通用能力**：鉴权、日志、限流、异常统一处理等可以放到 `dispatch` 或加“拦截器链”。

如果你希望更规范一点（比如强类型参数 DTO、参数校验、返回码/错误码体系、或支持“中间件/拦截器”），我也可以在这个基础上再升级一版。你命令参数来源是 HTTP（Spring MVC）、消息队列，还是命令行？

# String类型表驱动

下面是**参数全部是 `String`**、**不使用反射**、仍然“表驱动替代 if-else”的可运行示例。思路是用：

- `Map<String, Function<Request, Response>>`（统一入参/返回）
- `Request` 里只存 `Map<String, String>`

保存为 `StringOnlyTableDrivenDemo.java` 运行即可。

```java
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

public class StringOnlyTableDrivenDemo {

    // 统一入参：全部 String
    public static class Request {
        private final String command;
        private final Map<String, String> params;

        public Request(String command, Map<String, String> params) {
            this.command = command;
            this.params = (params == null) ? new HashMap<>() : params;
        }

        public String command() { return command; }

        public String get(String key) { return params.get(key); }

        public String require(String key) {
            String v = params.get(key);
            if (v == null || v.isBlank()) {
                throw new IllegalArgumentException("missing param: " + key);
            }
            return v;
        }

        public int requireInt(String key) {
            String v = require(key);
            try {
                return Integer.parseInt(v.trim());
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("param '" + key + "' is not int: " + v);
            }
        }

        // 便捷构造：Request.of("ECHO", "msg", "hi", "x", "1")
        public static Request of(String command, String... kv) {
            if (kv.length % 2 != 0) {
                throw new IllegalArgumentException("kv must be even length: key,value,...");
            }
            Map<String, String> p = new HashMap<>();
            for (int i = 0; i < kv.length; i += 2) {
                p.put(kv[i], kv[i + 1]);
            }
            return new Request(command, p);
        }
    }

    // 统一返回
    public static class Response {
        public final boolean ok;
        public final String message;
        public final String data; // 这里也用 String，方便演示

        private Response(boolean ok, String message, String data) {
            this.ok = ok;
            this.message = message;
            this.data = data;
        }

        public static Response ok(String data) { return new Response(true, "OK", data); }
        public static Response fail(String msg) { return new Response(false, msg, null); }

        @Override
        public String toString() {
            return "Response{ok=" + ok + ", message='" + message + "', data='" + data + "'}";
        }
    }

    // 表驱动分发器
    public static class Dispatcher {
        private final Map<String, Function<Request, Response>> table = new HashMap<>();

        public Dispatcher register(String cmd, Function<Request, Response> handler) {
            table.put(cmd, handler);
            return this;
        }

        public Response dispatch(Request req) {
            Function<Request, Response> h = table.get(req.command());
            if (h == null) return Response.fail("Unknown command: " + req.command());
            try {
                return h.apply(req);
            } catch (Exception e) {
                return Response.fail("Bad request: " + e.getMessage());
            }
        }
    }

    // 业务处理（全部参数从 Request 取 String）
    public static class Service {
        public Response hello(Request req) {
            return Response.ok("hello");
        }

        public Response echo(Request req) {
            String msg = req.require("msg");
            return Response.ok("echo: " + msg);
        }

        public Response add(Request req) {
            int a = req.requireInt("a");
            int b = req.requireInt("b");
            return Response.ok(String.valueOf(a + b));
        }
    }

    public static void main(String[] args) {
        Service service = new Service();

        Dispatcher dispatcher = new Dispatcher()
                .register("HELLO", service::hello)
                .register("ECHO",  service::echo)
                .register("ADD",   service::add);

        System.out.println(dispatcher.dispatch(Request.of("HELLO")));
        System.out.println(dispatcher.dispatch(Request.of("ECHO", "msg", "only string params")));
        System.out.println(dispatcher.dispatch(Request.of("ADD", "a", "10", "b", "20")));

        // 错误示例：缺参/格式不对/未知命令
        System.out.println(dispatcher.dispatch(Request.of("ADD", "a", "x", "b", "2")));
        System.out.println(dispatcher.dispatch(Request.of("ECHO"))); // msg 缺失
        System.out.println(dispatcher.dispatch(Request.of("UNKNOWN")));
    }
}
```

如果你的“参数只是 String”其实是**只有一个 String 入参**（比如 `command` + `payload`），也可以简化成 `Map<String, Function<String, String>>`。你更倾向哪种：`key-value` 参数表，还是单一 payload 字符串？