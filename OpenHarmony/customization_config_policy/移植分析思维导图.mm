<?xml version="1.0" encoding="UTF-8"?>
<!-- 由 生成思维导图eddx.py 生成 -->
<!-- 可导入 EdrawMind: 文件 → 导入 → FreeMind(.mm) -->
<!-- 或直接用 XMind / FreeMind / 幕布 打开 -->
<map version="1.0.1">
  <node ID="2876ac1f0c1d4ecb" TEXT="config_policy C/C++ 移植分析">
    <node ID="695a0143546e41df" TEXT="1. 移植范围" POSITION="right">
      <node ID="25e48604d43542bb" TEXT="需要移植">
        <node ID="0d712f53e6534c2a" TEXT="config_policy_utils.c   核心业务逻辑"/>
        <node ID="ebb85b91947f4edd" TEXT="config_policy_utils.h   公共 API 头文件"/>
        <node ID="c2e0f3b7fab7423c" TEXT="config_policy_impl.h    内部常量与默认值"/>
      </node>
      <node ID="fa639ff24a814ef0" TEXT="不需要移植">
        <node ID="ecc9492a4ba44524" TEXT="ArkTS / NAPI 层  config_policy_napi.cpp"/>
        <node ID="ad579df9eeb34746" TEXT="CJ 语言 FFI 层   config_policy_ffi.cpp"/>
        <node ID="840e5142cc0c4161" TEXT="customConfig 模块 custom_config_napi.cpp"/>
        <node ID="7d73498342d14ecb" TEXT="单元测试用例      config_policy_utils_test.cpp"/>
        <node ID="54244884e0fa44d2" TEXT="GN / Ninja 构建  BUILD.gn"/>
      </node>
    </node>
    <node ID="3fbfc97288544bb6" TEXT="2. 依赖分析" POSITION="right">
      <node ID="3a9641a1053143e9" TEXT="标准 C / POSIX — 完全可复用">
        <node ID="9288172db8274ae9" TEXT="stdio.h  stdlib.h  string.h"/>
        <node ID="bd6139de610d4a36" TEXT="stdbool.h  ctype.h  errno.h"/>
        <node ID="c531d68ee3694584" TEXT="unistd.h — access()  F_OK"/>
      </node>
      <node ID="a666de8659c64957" TEXT="OpenHarmony 专有 — 必须适配">
        <node ID="72cb1a3e6733494d" TEXT="init_param.h → SystemGetParameter / SystemSetParameter"/>
        <node ID="b2c13bdae9474a87" TEXT="securec.h    → bounds_checking_function 安全函数库"/>
        <node ID="ea6b6c92384b4de7" TEXT="PARAM_CONST_VALUE_LEN_MAX = 96  来自 init_param.h"/>
      </node>
      <node ID="af99d56c588047b7" TEXT="平台宏选择">
        <node ID="2302a5469e1449d2" TEXT="__LITEOS_M__  MCU 极简场景，静态缓冲 gConfigPolicy"/>
        <node ID="5bb255f3a5284bef" TEXT="__LITEOS__    LiteOS 轻量场景，不支持 Follow-X"/>
        <node ID="bb01e3a51f1c4496" TEXT="#else         标准 Linux / Harmony，完整功能"/>
        <node ID="7dc38f79403e405a" TEXT="移植目标：使用 #else 分支（有完整 libc）"/>
      </node>
    </node>
    <node ID="974be41c9c664baa" TEXT="3. 核心适配点" POSITION="right">
      <node ID="8a7a5494b8c14470" TEXT="init_param.h 适配">
        <node ID="70716482f91d4abe" TEXT="方案 A  同名头文件包装，接口与 OH 完全一致（推荐）"/>
        <node ID="016d1261f5ff478c" TEXT="方案 B  宏重映射  #define SystemGetParameter myGetParam"/>
        <node ID="584acaceb72648f2" TEXT="方案 C  封装函数  wrapper 转接自有参数系统"/>
        <node ID="4016000eab354d8f" TEXT="关键：必须支持先传 NULL 获取长度、再分配内存取值"/>
      </node>
      <node ID="4f53601e209446c2" TEXT="securec.h 兼容层">
        <node ID="d632d1c7e4f248b0" TEXT="strcpy_s   → 标准 strcpy_s 或自实现"/>
        <node ID="87a916a1838645a7" TEXT="sprintf_s  → snprintf  (截断返回 -1 而非正数)"/>
        <node ID="d1a9b0d3b79345e3" TEXT="snprintf_s → snprintf  (同上，影响 &gt; 0 判断)"/>
        <node ID="7352252b02374393" TEXT="memmove_s  → memmove + 长度检查"/>
        <node ID="48387d7db36a47ca" TEXT="memcpy_s   → memcpy  + 长度检查"/>
        <node ID="32bbe427ee1a47ac" TEXT="strcat_s   → strncat"/>
        <node ID="1ac3b440234e457f" TEXT="memset_s   → memset"/>
        <node ID="974b8d12b1454f42" TEXT="strtok_s   → strtok_r  (参数顺序完全不同！高危)"/>
        <node ID="78b406dfb03b4e2c" TEXT="EOK        → 0"/>
      </node>
    </node>
    <node ID="ce8e50c9f70a4615" TEXT="4. 可复用代码" POSITION="left">
      <node ID="a9eb79e563a440f8" TEXT="完全可复用（零修改）">
        <node ID="cc2c3868e6c64048" TEXT="GetCfgDirList()          层列表查询入口"/>
        <node ID="4d75a784f66c40f6" TEXT="GetCfgFiles() / GetCfgFilesEx()    多层文件搜索"/>
        <node ID="cfe78aa0cba74471" TEXT="GetOneCfgFile() / GetOneCfgFileEx() 最高优先级文件"/>
        <node ID="36e1b0b597b54b81" TEXT="Follow-X 机制   SIM 运营商 / USER_DEFINED 自定义"/>
        <node ID="30ba1ed2df3a48fa" TEXT="ExpandStr()     字符串变量展开  ${key:-default}"/>
        <node ID="164e5a8f3ab04d32" TEXT="TrimInplace()   字符串首尾裁剪"/>
        <node ID="969ac32ab60342b8" TEXT="SplitStr()      字符串分割（依赖 strtok_s→strtok_r）"/>
        <node ID="a78135a254be4858" TEXT="FreeCfgFiles() / FreeCfgDirList()  内存释放"/>
        <node ID="128edb10019641d8" TEXT="EnsureHolderSpace() / AppendStr()  动态缓冲增长"/>
      </node>
      <node ID="26e90fcb68794eb4" TEXT="少量修改即可复用">
        <node ID="2385eccfbe8547c4" TEXT="GetCfgDirRealPolicyValue()  替换 CustGetSystemParam 调用"/>
        <node ID="00140cf284cf4c6c" TEXT="GetFollowXRule()             替换 CustGetSystemParam 调用"/>
        <node ID="eb164fd501794ad5" TEXT="GetOpkeyPath()               替换 CustGetSystemParam 调用"/>
        <node ID="f3d3a9439dfb415f" TEXT="CustGetSystemParam()         替换为自有参数系统 wrapper"/>
      </node>
    </node>
    <node ID="d48fec2716a24e2d" TEXT="5. 关键陷阱" POSITION="left">
      <node ID="1c15dd9e30fa4863" TEXT="strtok_s 签名差异 ★高危★">
        <node ID="47ae409c527d4de2" TEXT="securec / MSVC: strtok_s(str, delim, &amp;next)         3 参数"/>
        <node ID="13e235707f7a4058" TEXT="C11 标准:        strtok_s(str, &amp;maxLen, delim, &amp;next) 4 参数"/>
        <node ID="f4a781044c434cc8" TEXT="解决方案: 统一使用 POSIX strtok_r(str, delim, &amp;next)"/>
      </node>
      <node ID="a84d0bab941341bd" TEXT="CfgDir 内存模型 ★高危★">
        <node ID="182282c577784b96" TEXT="paths[] 指针指向 realPolicyValue 字符串内部，非独立分配"/>
        <node ID="d67dd031d8f849bc" TEXT="严禁单独 free(paths[i])！"/>
        <node ID="302d820a91ba475b" TEXT="FreeCfgDirList() 会 free 整块 realPolicyValue"/>
        <node ID="f04ec5a957d6414f" TEXT="对比：CfgFiles-&gt;paths[] 是各自独立 strdup() 分配，可单独 free"/>
      </node>
      <node ID="7d374ffc610e4a8e" TEXT="snprintf_s 返回值语义差异">
        <node ID="5d4b5c2cdd0a4f33" TEXT="标准 snprintf: 截断时返回应写入字节数（正数）"/>
        <node ID="7cc45faecc8d4e31" TEXT="snprintf_s:    截断时返回 -1"/>
        <node ID="3fc8ceb2ca904a2e" TEXT="源码所有 &gt; 0 判断逻辑均依赖 snprintf_s 的 -1 截断语义"/>
      </node>
      <node ID="465e475e27f54ddd" TEXT="参数获取两步模式">
        <node ID="57faf60c6d394d2f" TEXT="第 1 步: SystemGetParameter(name, NULL, &amp;len) 获取所需长度"/>
        <node ID="ebd9e2eed6ca4310" TEXT="第 2 步: calloc(len, 1) 后再次调用取值"/>
        <node ID="88101b57eb9f42bb" TEXT="适配层接口必须同时支持 buffer=NULL 的调用方式"/>
      </node>
    </node>
    <node ID="220d3243ef224e6d" TEXT="6. 改动清单" POSITION="left">
      <node ID="6ff7a7d38ac14539" TEXT="修改文件（仅 2 处 #include）">
        <node ID="cdc63f464be24e18" TEXT="config_policy_utils.c 第 19 行: &lt;securec.h&gt;    → &quot;compat_securec.h&quot;"/>
        <node ID="6d2b37f0dad84855" TEXT="config_policy_utils.c 第 25 行: &quot;init_param.h&quot; → &quot;config_policy_param_adapter.h&quot;"/>
        <node ID="549b9e9e8567451e" TEXT="业务逻辑零改动"/>
      </node>
      <node ID="681ad6b94fe94716" TEXT="新增文件">
        <node ID="a6553335475d4111" TEXT="config_policy_param_adapter.h  适配自有参数系统"/>
        <node ID="51b0913b2ef747cb" TEXT="compat_securec.h               securec 安全函数兼容实现"/>
        <node ID="b0b00e79789649e2" TEXT="CMakeLists.txt                 替代 BUILD.gn 的构建脚本"/>
        <node ID="e86dc35938c24223" TEXT="verify_port.c                  移植功能验证程序"/>
      </node>
    </node>
    <node ID="3bb0369d473643cc" TEXT="7. 验证方案" POSITION="left">
      <node ID="5e094207efe54d30" TEXT="编译验证">
        <node ID="267a402ab0b74eb6" TEXT="cmake -DCMAKE_BUILD_TYPE=Debug .. &amp;&amp; make -j4"/>
        <node ID="ab24ef5623f24023" TEXT="目标: 零编译错误，零警告"/>
      </node>
      <node ID="e4af3db28be2493e" TEXT="功能验证">
        <node ID="28ae8ab1f1e9479f" TEXT="GetCfgDirList()   返回非空路径列表"/>
        <node ID="e1a2f429d541482c" TEXT="GetOneCfgFile()   找到已存在的文件"/>
        <node ID="d7e52dbb43b74441" TEXT="GetCfgFiles()     返回全部层级匹配文件"/>
        <node ID="413eda816f414ac1" TEXT="Follow-X SIM_1 / USER_DEFINED 路径拼接正确"/>
      </node>
      <node ID="5db1dbde476b47aa" TEXT="边界条件验证">
        <node ID="e0e68ab00fb74812" TEXT="NULL 参数          返回 NULL，不崩溃"/>
        <node ID="98ac75289cab4243" TEXT="不存在的文件        返回空结果"/>
        <node ID="976c9536662c41dc" TEXT="超长路径 &gt; 256 字节  安全截断，不溢出"/>
      </node>
    </node>
    <node ID="00714d8c56c84564" TEXT="8. 构建集成" POSITION="left">
      <node ID="f93941b1f2824227" TEXT="CMake 配置（推荐）">
        <node ID="acd7a775c25d4b36" TEXT="add_library(config_policy_util SHARED config_policy_utils.c)"/>
        <node ID="a64c3397ce7a465f" TEXT="target_include_directories() 指定适配头文件目录"/>
        <node ID="722166a787f24654" TEXT="target_compile_options(-std=c++14 或以上)"/>
      </node>
      <node ID="942daa7c7cd64e6e" TEXT="编译注意事项">
        <node ID="bf87e8b60e254023" TEXT="C++14 或以上标准"/>
        <node ID="47bac75d24f94e86" TEXT="需要 POSIX 兼容环境: access() F_OK strtok_r"/>
        <node ID="d59bdcd7196b4a8f" TEXT="-D_POSIX_C_SOURCE=200809L 启用 strtok_r"/>
        <node ID="81bb8659c9284149" TEXT="多线程场景: strtok_r 线程安全，strtok 非线程安全"/>
      </node>
    </node>
  </node>
</map>
