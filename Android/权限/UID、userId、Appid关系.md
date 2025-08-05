*Thinking...*

> 用户问的是Android系统中userid、uid和appid的概念，以及它们之间的关系。这是一个技术性问题，我需要准确清晰地解释这些概念。
> 
> 在Android系统中：
> 1. UID (User ID) - 这是Linux系统中的用户ID概念，Android基于Linux，所以也有这个概念
> 2. appId - 这是Android应用的ID，通常是从10000开始的一个数字
> 3. userId - 在Android多用户系统中，代表不同的用户账户
> 
> 让我详细解释一下这些概念和它们的关系。

在Android系统中，userid、uid和appid是用于标识和隔离应用程序的重要概念。让我详细解释它们的含义和关系：

## UID (User ID)

UID是Linux系统中的用户标识符，Android基于Linux内核，继承了这个概念。在Android中，每个应用程序运行时都会被分配一个唯一的UID，用于进程和文件权限管理。

## AppId (Application ID)

AppId是Android为每个应用分配的基础ID。当你安装一个应用时，系统会为它分配一个AppId，通常从10000开始递增。例如，第一个安装的第三方应用可能获得AppId 10000，第二个是10001，以此类推。

## UserId

UserId是Android多用户系统中的概念，代表不同的用户账户。Android支持多用户（从Android 4.2开始），每个用户都有一个UserId：
- 主用户（设备所有者）的UserId是0
- 其他用户的UserId从10开始递增（10、11、12...）

## 三者之间的关系

这三个概念通过以下公式相互关联：

```
UID = UserId * 100000 + AppId
```

举例说明：
- 如果一个应用的AppId是10050
- 在主用户（UserId=0）下运行时，其UID = 0 * 100000 + 10050 = 10050
- 在第二个用户（UserId=10）下运行时，其UID = 10 * 100000 + 10050 = 1010050

## 实际应用

这种设计使得Android能够：

1. **应用隔离**：每个应用都有独立的UID，无法访问其他应用的私有数据
2. **多用户隔离**：同一应用在不同用户下运行时有不同的UID，实现用户间的数据隔离
3. **权限管理**：基于UID进行文件访问权限控制
4. **共享UID**：具有相同签名的应用可以通过在AndroidManifest.xml中声明相同的sharedUserId来共享UID

通过查看应用信息可以验证这些概念：
```bash
# 通过adb查看应用的UID
adb shell ps | grep <package_name>

# 查看应用的详细信息
adb shell dumpsys package <package_name>
```

这种多层次的ID体系是Android安全模型的核心组成部分，确保了应用之间的隔离和多用户环境下的数据安全。