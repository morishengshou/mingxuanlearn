下面整理一份主流的 ABI（Application Binary Interface）兼容性检测/分析工具清单，并给出典型使用方法与适用场景。重点覆盖 Linux（ELF/.so）、macOS（Mach-O/.dylib）、Windows（PE/.dll），以及构建期/发布期的实践。

—  
一、Linux/ELF 动态库（.so）

1) ABI/API 对比工具
- abi-compliance-checker（通用、成熟，C/C++）
  - 作用：比较两个版本库在 ABI 和 API 层面的差异，输出 HTML/文本报告。常用于发布前回归。
  - 依赖：abi-dumper（生成 ABI 描述）、DWARF 符号信息（需要带调试信息或可从调试包获取）。
  - 安装：
    - Ubuntu/Debian: sudo apt-get install abi-compliance-checker abi-dumper
    - 或从源码安装 GitHub: lvc/abi-compliance-checker
  - 基本用法：
    1. 给两个版本库生成 ABI dump（需要对应的头文件和库）：
       - abi-dumper libfoo_old.so -o ABI-old.dump -lver OLD
       - abi-dumper libfoo_new.so -o ABI-new.dump -lver NEW
       - 注意：如果剥离了调试符号，需使用带 debuginfo 的 .so 或安装对应 -dbgsym 包。
    2. 对比：
       - abi-compliance-checker -l libfoo -old ABI-old.dump -new ABI-new.dump
    3. 输出：
       - 生成 compat_reports/libfoo/ 下的 HTML 报告，详细列出 ABI break（删除符号、变更布局、vtable 变更、内联影响等）与 API 变更。
  - 进阶：
    - 指定头文件根目录：-headers include/
    - 忽略特定符号/命名空间：--skip-headers, --list, --symbols-list
    - C++ 标准库差异可能引入噪声，建议固定同一工具链版本构建并加上 -fvisibility=hidden 限定导出集。

- libabigail 套件（abidiff/abipkgdiff/abidw）
  - 作用：基于 DWARF 的二进制接口语义差异分析，精度高，可做包级别比较（.rpm/.deb）。
  - 安装：
    - Fedora/CentOS/RHEL: dnf/yum install libabigail abigail-tools
    - Ubuntu: apt-get install libabigail
  - 用法：
    - 单库对比：abidiff --headers-dir1 include_old --headers-dir2 include_new libfoo_old.so libfoo_new.so
    - 仅二进制（无头文件）：abidiff libfoo_old.so libfoo_new.so
    - 导出内部表示：abidw libfoo.so > foo.abi
    - 包级比较（含依赖）：abipkgdiff --d1 libfoo-old.rpm --d2 libfoo-new.rpm
  - 优点：对 C++ 类型变更、内联、模板实例化更敏感；报告可机读（--report-kind full/json）。

- dwarfdump/readelf/nm/objdump（手动分析）
  - 用法：
    - readelf -Ws libfoo.so | c++filt 观察导出符号表
    - nm -D --defined-only libfoo.so 查看导出定义
    - objdump -T libfoo.so 审核动态符号、版本脚本效果
  - 适合快速检查导出集合、符号版本（.symver）等。

2) 运行期/链接期兼容性检测
- ldconfig/ldd
  - ldd ./app 检查依赖解析是否成功、版本是否匹配（注意不要对不可信二进制运行 ldd）。
- GLIBC 版本检查
  - readelf -Ws libfoo.so | grep GLIBC_ 可看对 GLIBC 符号版本的依赖，帮助评估向后兼容。
- ELF 版本脚本（version script）
  - 在链接时用 -Wl,--version-script=exports.map 锁定导出符号和版本，减少 ABI 漂移。
- elfutils + CI 断言
  - 在 CI 中运行 readelf/nm + diff，对导出符号白名单进行回归校验。

3) 构建期策略
- 控制可见性：编译加 -fvisibility=hidden，导出通过 __attribute__((visibility("default")))，或使用符号版本脚本，保证稳定 ABI 面。
- C++ 稳定 ABI 实践：避免在 ABI 面暴露 STL/模板/inline，使用 pImpl；对齐/布局变更时 bump SONAME。
- SONAME 管理：链接参数 -Wl,-soname,libfoo.so.Maj，ABI 破坏时提升主版本。

—  
二、macOS（Mach-O/.dylib/.framework）

- otool/otx/nm
  - otool -L libfoo.dylib 查看依赖与 install_name
  - nm -gU libfoo.dylib 查看导出符号（C++ 可配合 c++filt）
- vtool（Xcode 工具）
  - vtool -show-build libfoo.dylib 查看 LC_ID_DYLIB、LC_LOAD_DYLIB
- dyldinfo
  - dyldinfo -export libfoo.dylib 列出导出符号；-rebase/-bind 看绑定信息
- 比较方法
  - 导出符号对比：nm/llvm-nm 输出排序后做 diff
  - ABI 语义层工具较少，建议采用 Linux 同构建策略（隐藏符号、pImpl），并通过单元/集成测试验证运行兼容性
- 版本与兼容字段
  - install_name、compatibility_version、current_version 管理：install_name_tool -id/-change；破坏 ABI 时提高 compatibility_version

—  
三、Windows（PE/.dll）

- dumpbin/Dependencies
  - dumpbin /EXPORTS foo.dll 查看导出；/DEPENDENTS 查看依赖
- link.exe /DEF 或 module-definition (.def) 文件控制导出集；或 __declspec(dllexport)/linker map 控制
- ABI 对比思路
  - 导出函数签名变化会破坏 ABI（名称修饰、调用约定、结构体布局）
  - 用 dumpbin /HEADERS 与 /SYMBOLS 辅助检查；用 abi-dumper/abidiff 对 PE 支持有限，更多依赖导出符号文本 diff + 测试
- 稳定 ABI 实践
  - C 接口导出（extern "C"）+ 不暴露 STL/例外抛出；使用 COM 风格接口或 C API + 句柄

—  
四、跨平台通用策略与工具链集成

- 符号白名单/黑名单
  - 生成基线：nm -D libfoo.so | awk 筛出导出 -> 存入 allowlist
  - CI 对比：新构建导出集合与基线 diff，出现新增/删除/重命名即阻断
- 头文件 API 稳定性
  - 结合 clang-abi-compat（Clang 插件类工具，社区项目）或 clang-tidy 检测易致 ABI 变化的写法（如加虚函数、非尾成员变更、枚举底层类型变化）
- 单元与二进制兼容回归
  - 使用旧版应用加载新版库进行运行时测试（LD_LIBRARY_PATH/dyld 环境隔离），覆盖：对象创建/销毁、异常跨边界、结构体大小与对齐、回调 ABI、线程局部存储
- 容器与编译器钉固
  - 固定编译器版本、标准库实现、编译选项（-O、-fno-exceptions 等）和目标平台（GLIBC、MACOSX_DEPLOYMENT_TARGET、Windows SDK）
- SONAME/版本策略
  - 任何破坏性变更必须 bump 主版本；兼容新增可以 bump 次版本；维护变更日志和导出符号变更记录

—  
五、简要操作示例（Linux/C++）

- 生成与对比（libabigail）
  - 构建 old/new 两版 libfoo.so（带 -g，不 strip，或安装 debuginfo）
  - abidiff --hd1 include/old --hd2 include/new build/old/libfoo.so build/new/libfoo.so
  - 结果非 0 退出码可作为 CI 失败信号；加 --leaf-changes-only 降噪

- 生成与对比（abi-compliance-checker）
  - abi-dumper build/old/libfoo.so -o old.dump -lver OLD -public-headers include/old
  - abi-dumper build/new/libfoo.so -o new.dump -lver NEW -public-headers include/new
  - abi-compliance-checker -l foo -old old.dump -new new.dump -report-path report/
  - 在 CI 保存 HTML 报告为制品

- 导出符号白名单
  - nm -D --defined-only libfoo.so | c++filt | awk '{print $3}' | sort > exports.txt
  - 与上游基线 diff -u exports.baseline exports.txt

—  
六、常见坑与建议

- 去符号导致分析失败：确保 .so 提供 DWARF（-g）或安装 debuginfo 包；strip 可保留 .gnu_debuglink 指向外部调试文件
- C++ 内联/模板/constexpr 在编译器版本变更时可能产生 ABI 漂移，尽量把实现藏在 .cpp，不在头文件暴露布局
- 不要把 STL/异常跨边界暴露到 ABI 面；异常 ABI 常因运行库不一致导致崩溃
- 符号版本化（GNU）能在一定程度上缓解升级兼容问题，但需要严格维护版本脚本
- 不同发行版 glibc 版本差异：构建时尽量在较旧基线 glibc 上编译以获得更低的 GLIBC_x.y 依赖（或使用工具如 c++filt + readelf 检查）
- macOS 的 SDK/部署目标变动会改变可用符号集，要固定 MACOSX_DEPLOYMENT_TARGET
- Windows 名称修饰和调用约定（__cdecl/__stdcall）变更会直接破坏 ABI，导出 C 接口最稳妥

—  
七、快速清单

- Linux：abidiff/libabigail、abi-compliance-checker + abi-dumper、readelf/nm/objdump、ldd/soname/version script
- macOS：otool/dyldinfo/nm、install_name_tool、符号 diff
- Windows：dumpbin/Dependencies、.def 文件、符号 diff
- CI 集成：基线导出 diff + abidiff/abi-compliance-checker 报告 + 运行期加载测试

如果你提供目标平台、语言（C/C++/Rust 等）、工具链版本和一个示例库，我可以给出更贴合的命令脚本或 CI 配置片段（GitHub Actions/GitLab CI）。