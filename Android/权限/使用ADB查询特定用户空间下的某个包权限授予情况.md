下面给出用 adb 在“特定用户（userId）”下查询某个应用权限授予状态的常用方法与可复制命令。适用于 Android/AAOS 多用户（含 HSU）。

前置说明
- userId 是 Android 的多用户 ID（U0=0, U10=10 等）。
- 包名用 com.example.app 代指，请替换为你的实际包名。
- 某些命令需要 shell 权限即可；查看更底层状态可能需要 root。

方法一：cmd package + dumpsys package（推荐）
- 快速查看指定用户的权限授予概览
  - adb shell cmd package dump com.example.app | sed -n '/runtime permissions:/,/^\s*$/p'
  这会输出所有用户的运行时权限块。再配合 grep 筛选指定 userId：
  - adb shell "cmd package dump com.example.app | awk '/runtime permissions:/{flag=1} flag{print} /^\s*$/{flag=0}' | sed -n '/granted=false/!p'"
- 精确到某个 userId 的块：
  - adb shell "cmd package dump com.example.app | sed -n '/User 10:/,/User [0-9]\+:/p'"
  在该块中查 runtime permissions 与 app-op 状态。
- 只列出某用户的权限授予行（granted=true/false）
  - adb shell "cmd package dump com.example.app | sed -n '/User 10:/,/User [0-9]\+:/p' | sed -n '/runtime permissions:/,/^\s*$/p'"

方法二：cmd appops 查看 AppOps（有些权限通过 AppOps 体现）
- 列出指定用户的 AppOps：
  - adb shell cmd appops get --user 10 com.example.app
- 查询特定 op：
  - adb shell cmd appops get --user 10 com.example.app OP_NAME
  例：ACCESS_FINE_LOCATION 对应的 op 通常是 android:coarse_location / android:fine_location；可用:
  - adb shell cmd appops query-op --user 10 android:fine_location --packages com.example.app

方法三：pm 命令查看权限（部分系统版本有效）
- 列出某用户下应用信息（含 requested permissions 与 granted 标记）：
  - adb shell pm dump com.example.app | sed -n '/requested permissions:/,/install permissions:/p'
  这不分用户；运行时授予仍以 dumpsys/cmd package 为准。
- 列出用户安装状态（辅助确认用户隔离）：
  - adb shell cmd package list packages --user 10 -f com.example.app

方法四：dumpsys package 详细视图
- 全量详情（搜索 userId 和 permissions 段落）：
  - adb shell dumpsys package com.example.app
  找到诸如：
  - User 10: ceDataInode=... installed=true hidden=false suspended=false
  - runtime permissions:
      android.permission.ACCESS_FINE_LOCATION: granted=true, flags=[...]
  - install permissions:
      android.permission.INTERNET: granted=true, flags=[...]
- 全局过滤某权限在各用户上的状态：
  - adb shell "dumpsys package com.example.app | awk '/runtime permissions:/{r=1} r && /android.permission.ACCESS_FINE_LOCATION/ {print} /^\s*$/{r=0}'"

方法五：在应用运行态校验（可选，需 app 配合）
- adb shell run-as com.example.app sh -c 'cmd appops get --user 10 com.example.app'
- 或在应用内用 checkSelfPermission + UserHandle.myUserId() 记录，但纯 adb 查询优先用方法一/二。

常见权限到 AppOps 的对应提示
- ACCESS_FINE_LOCATION -> android:fine_location
- ACCESS_COARSE_LOCATION -> android:coarse_location
- POST_NOTIFICATIONS -> app-ops 不一定显示为授予，优先看 runtime permissions
- READ_MEDIA_* 可能以分区权限/范围体现，仍在 runtime permissions 中看 granted 标志
- BACKGROUND_LOCATION 可能体现在 fine_location 的 “mode=allow/allow_bg” 组合，留意 appops 输出

一键脚本示例（替换 PKG 与 USER）
- adb shell 'PKG=com.example.app; USER=10; echo "== $PKG (user $USER) runtime permissions =="; cmd package dump $PKG | sed -n "/User $USER:/,/User [0-9]\\+:/p" | sed -n "/runtime permissions:/,/^\\s*$/p"; echo; echo "== AppOps =="; cmd appops get --user $USER $PKG'

如需我帮你针对具体包名与 userId 生成精确命令或解读输出，告诉我 PKG 和 USER 即可。