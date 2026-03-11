# config_policy 移植版 4+1 架构视图

本目录包含移植后项目的完整 4+1 架构视图，使用 PlantUML 编写。

---

## 视图文件列表

| 文件 | 视图 | 内容 |
|------|------|------|
| `01_逻辑视图.puml` | 逻辑视图 | 组件职责与接口关系（4层结构） |
| `02_进程视图_启动时序.puml` | 进程视图 | 系统启动时序：Init→cust_init→参数文件就绪→业务进程 |
| `03_进程视图_运行时序.puml` | 进程视图 | 运行时配置查询时序：GetCfgDirList 完整调用链 |
| `04_开发视图.puml` | 开发视图 | 包结构、文件职责、编译依赖（含改动标注） |
| `05_物理视图.puml` | 物理视图 | 部署结构：rootfs/tmpfs/进程 映射关系 |
| `06_场景视图_用例图.puml` | 场景视图(+1) | 用例图：9个用例与参与者关系 |
| `07_场景视图_场景1_系统初始化.puml` | 场景视图(+1) | 场景1：cust_init 开机写入参数文件 |
| `08_场景视图_场景2_配置层查询.puml` | 场景视图(+1) | 场景2：GetCfgDirList/GetOneCfgFile/GetCfgFiles |
| `09_场景视图_场景3_FollowX查询.puml` | 场景视图(+1) | 场景3：Follow-X 运营商路径查询（3种模式） |

---

## 如何渲染 PlantUML 图

### 方法1：VS Code 插件（推荐）

1. 安装插件 **PlantUML**（作者：jebbs）
2. 打开任意 `.puml` 文件
3. 按 `Alt+D` 预览，或右键 → `Preview Current Diagram`
4. 需要本地安装 Java（JRE 8+）和 Graphviz

### 方法2：在线渲染（无需安装）

访问 [https://www.plantuml.com/plantuml](https://www.plantuml.com/plantuml)，
将 `.puml` 文件内容粘贴到编辑框即可。

### 方法3：命令行批量导出

```bash
# 安装 plantuml.jar（从 https://plantuml.com/download 下载）
java -jar plantuml.jar -tsvg "*.puml"   # 导出 SVG
java -jar plantuml.jar -tpng "*.puml"   # 导出 PNG
```

### 方法4：IntelliJ IDEA / CLion

安装 PlantUML Integration 插件，直接在 IDE 内预览。

---

## 4+1 视图模型说明

| 视图 | 关注角度 | 主要受众 |
|------|----------|----------|
| **逻辑视图** | 软件功能分解，关键抽象与接口 | 开发人员、架构师 |
| **进程视图** | 运行时行为，进程/线程，时序 | 系统集成人员、开发人员 |
| **开发视图** | 代码组织，模块划分，编译依赖 | 开发人员、构建工程师 |
| **物理视图** | 软件到硬件/文件系统的映射 | 系统工程师、运维人员 |
| **场景视图(+1)** | 关键用例，驱动并验证其他四个视图 | 所有相关人员 |

---

## 移植后项目结构速览

```
my_project/
├── CMakeLists.txt                           顶层构建（生成 .so + cust_init）
├── port/                                    平台适配层（新增）
│   ├── config_policy_param_adapter.h        替代 init_param.h，读 tmpfs 文件
│   ├── compat_securec.h                     替代 securec.h（安全函数兼容）
│   └── config_policy_log.h                  替代 HiLog（日志宏桥接）
├── customization_config_policy/             移植子模块
│   ├── frameworks/config_policy/src/
│   │   └── config_policy_utils.c            仅改 2 处 #include
│   ├── frameworks/dfx/hisysevent_adapter/
│   │   ├── hisysevent_adapter.h             不变
│   │   └── hisysevent_adapter.cpp           替换实现（使用 config_policy_log.h）
│   └── interfaces/inner_api/include/
│       ├── config_policy_utils.h            不变（公共 API）
│       └── config_policy_impl.h             不变（内部常量）
└── cust_init/                               开机参数写入程序（新增）
    ├── CMakeLists.txt
    └── main.c                               写入 /run/config_policy/params

构建产物：
  libconfig_policy_util.so   核心共享库
  cust_init                  开机可执行文件
```

---

## 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 参数系统替代 | tmpfs 文件 + config_policy_param_adapter.h | 无需修改 init 进程，系统级共享 |
| 安全函数替代 | compat_securec.h 兼容层 | strtok_s 参数顺序不同，需统一用 strtok_r |
| DFX 替代 | config_policy_log.h 宏桥接 | 仅替换 .cpp 实现，接口头文件和调用方零改动 |
| 只读保护 | chmod 444 + 原子写入(mv) | 防止运行期篡改，防止半写读取 |
| 参数文件位置 | /run/config_policy/params | /run 通常是 tmpfs，重启自动清理 |
