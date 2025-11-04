要在 Java 中实现 ASCII 码值与字符的互相转换，核心是使用 char 和 int 之间的强制类型转换。下面给出常见场景与示例。

一、字符转 ASCII 码值
- 对单个字符，直接强转为 int 即可。
- 对字符串，逐字符取 ASCII 值。

示例：
```java
public class CharToAscii {
    public static void main(String[] args) {
        char c = 'A';
        int ascii = (int) c; // 或直接: int ascii = c;
        System.out.println("字符: " + c + " -> ASCII: " + ascii); // 65

        String s = "Hello!";
        for (char ch : s.toCharArray()) {
            System.out.println(ch + " -> " + (int) ch);
        }
    }
}
```

二、ASCII 码值转字符
- 将 int 强制转换为 char。
- 注意码值范围：标准 ASCII 为 0–127，扩展 ASCII 常用到 0–255；Java 的 char 为 16 位 Unicode（0–65535），转换时请确保在期望范围内。

示例：
```java
public class AsciiToChar {
    public static void main(String[] args) {
        int code = 65;
        char c = (char) code;
        System.out.println("ASCII: " + code + " -> 字符: " + c); // A

        // 批量转换
        int[] codes = {72, 101, 108, 108, 111, 33}; // Hello!
        StringBuilder sb = new StringBuilder();
        for (int value : codes) {
            if (value < 0 || value > 127) {
                throw new IllegalArgumentException("非标准ASCII码值: " + value);
            }
            sb.append((char) value);
        }
        System.out.println(sb.toString());
    }
}
```

三、字符串与字节数组的编码转换
如果你处理的是“ASCII 编码的字节”，建议显式使用 Charset，避免平台默认编码差异：

- 字符串转 ASCII 字节：
```java
import java.nio.charset.StandardCharsets;

String s = "Hello!";
byte[] asciiBytes = s.getBytes(StandardCharsets.US_ASCII);
```

- ASCII 字节转字符串：
```java
String s2 = new String(asciiBytes, StandardCharsets.US_ASCII);
```

注意：
- 非 ASCII 字符（码点 > 127）在 US_ASCII 中会被替换为问号 '?'（0x3F）。如果你需要完整 Unicode，请使用 UTF-8：
```java
byte[] utf8 = s.getBytes(StandardCharsets.UTF_8);
String s3 = new String(utf8, StandardCharsets.UTF_8);
```

四、常见陷阱与建议
- Java 的 char 是 Unicode 码元，不是“ASCII 专用”。只要字符在 ASCII 范围内，char 到 int 的转换结果与 ASCII 码值一致。
- 对于中文或 emoji 等非 ASCII 字符，(int) ch 得到的是 Unicode 码点（BMP 内为 U+0000～U+FFFF）。对于代理对字符（如部分 emoji），需要按码点遍历：
```java
String s = "A😊";
s.codePoints().forEach(cp -> System.out.println(cp)); // 打印 Unicode 码点
```
- 若你只关心 0–127 的 ASCII，转换前可检查范围。

五、简易工具方法
```java
public final class AsciiUtil {
    private AsciiUtil() {}

    public static int charToAscii(char ch) {
        if (ch > 127) throw new IllegalArgumentException("非ASCII字符: " + ch);
        return ch;
    }

    public static char asciiToChar(int code) {
        if (code < 0 || code > 127) throw new IllegalArgumentException("非ASCII码值: " + code);
        return (char) code;
    }

    public static int[] stringToAscii(String s) {
        int[] arr = new int[s.length()];
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch > 127) throw new IllegalArgumentException("包含非ASCII字符: " + ch);
            arr[i] = ch;
        }
        return arr;
    }

    public static String asciiArrayToString(int[] codes) {
        StringBuilder sb = new StringBuilder(codes.length);
        for (int code : codes) {
            if (code < 0 || code > 127)
                throw new IllegalArgumentException("非ASCII码值: " + code);
            sb.append((char) code);
        }
        return sb.toString();
    }
}
```

如果你有具体输入输出格式或需要处理扩展 ASCII/GBK/UTF-8 等编码，告诉我你的场景，我可以给出更精确的实现。