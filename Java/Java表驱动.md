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