下面给你一个“**本地保留全量代码** + “**每次容器启动得到一份干净工作区**” + “**只把你要改的模块以挂载方式覆盖进去**” + “**构建产物不污染源码**”的方案。核心思路是：**黄金源码只读**，每次运行创建一个**快速快照工作区**（复制/写时拷贝），再把模块目录 bind mount 覆盖到工作区对应子目录；构建一律 **out-of-source** 到单独 build 目录（tmpfs/临时目录/卷）。

---

## 目标拆解

1. **不再 repo 拉全量**：在宿主机保留一个“黄金全量代码目录”，只在需要时更新一次。
2. **每次编译都是干净环境**：容器看到的是“工作区快照”，不是黄金目录本体。
3. **只改一个模块**：把模块目录直接挂载进去覆盖工作区的对应子目录。
4. **中间产物不污染代码**：源码在容器里尽量只读；所有生成物进 `/ws/build`（可 tmpfs）。

---

## 方案 A（通用推荐）：宿主机“快速快照目录” + Docker 子目录覆盖挂载

### 1) 宿主机准备一个“黄金全量目录”
例如：

```bash
export GOLDEN=/data/project_golden   # 这里是你repo同步后的完整源码
# 需要更新时手动执行一次：
cd "$GOLDEN" && repo sync -j8
```

> 黄金目录只负责“存档/更新”，不在容器里直接编译。

---

### 2) 每次编译：创建一个“工作区快照”
快照的关键是“快”，有三种实现方式（按优先级选）：

#### 优先 1：文件系统 reflink（最快，写时拷贝）
如果宿主机是 **btrfs/xfs(reflink)/zfs** 等，或 coreutils 支持：

```bash
cp -a --reflink=auto "$GOLDEN/." "$WS/src"
```

#### 备选 2：硬链接快照（也很快，但必须配合“容器内只读挂载”）
```bash
cp -al "$GOLDEN/." "$WS/src"
```

> 硬链接意味着修改会影响黄金目录，所以必须确保容器里对该 src 挂载为 `:ro`，并且构建系统不要往源码树写文件。

#### 备选 3：rsync 增量到工作区（比全拷贝快，兼容性最好）
```bash
rsync -a --delete "$GOLDEN/" "$WS/src/"
```

---

### 3) Docker 运行：黄金快照只读 + 模块目录覆盖 + 构建目录独立

假设你要改的模块在仓库路径：`path/to/my_module`，你本地正在编辑的模块目录是：`$PWD/my_module`

**关键点：Docker 支持“后面的挂载覆盖前面的子路径”**，所以可以先挂载整个 src，再用模块挂载覆盖子目录。

下面给一个可直接用的脚本（推荐）：

```bash
#!/usr/bin/env bash
set -euo pipefail

IMAGE="mytoolchain:latest"
GOLDEN="/data/project_golden"

# 你正在改的模块（宿主机目录）
MODULE_HOST="$(pwd)/my_module"
# 模块在仓库里的路径（容器内路径相对 /ws/src）
MODULE_IN_REPO="path/to/my_module"

# 工作区位置：用内存盘更快（没有就用 /tmp）
TMPBASE="/dev/shm"
WS="$(mktemp -d "${TMPBASE}/buildws.XXXXXX")"
trap 'rm -rf "$WS"' EXIT

mkdir -p "$WS/src" "$WS/build"

# 生成快照（优先 reflink，其次可改成 cp -al 或 rsync）
cp -a --reflink=auto "$GOLDEN/." "$WS/src"

docker run --rm -it \
  -v "$WS/src:/ws/src:ro" \
  -v "$MODULE_HOST:/ws/src/${MODULE_IN_REPO}:rw" \
  --tmpfs /ws/build:exec,size=16g \
  -v "$HOME/.ccache:/root/.ccache" \
  -w /ws \
  "$IMAGE" \
  bash -lc '
    set -e
    # 强制 out-of-source 构建，避免污染源码
    cmake -S /ws/src -B /ws/build -G Ninja \
      -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
      -DCMAKE_C_COMPILER_LAUNCHER=ccache
    cmake --build /ws/build -j
  '
```

#### 这样做你得到什么效果？
- **不再 repo 拉取**：全量在 `$GOLDEN`，仅偶尔更新。
- **每次都是干净工作区**：`$WS` 临时目录，容器退出自动清理。
- **你改的模块实时生效**：模块目录直接挂载覆盖 `/ws/src/path/to/my_module`。
- **源码不被污染**：`/ws/src` 只读；生成物都在 `/ws/build`（tmpfs，退出即没）。

---

## 方案 B（更“极致”，零拷贝）：OverlayFS 写时拷贝工作区（需要 root/特权）

如果你希望连“快照拷贝”都不要，而是对黄金目录做真正的 **COW 合并视图**，可以在宿主机用 overlayfs：

- `lowerdir = GOLDEN(只读)`
- `upperdir = 本次运行的临时写层`
- `merged = 容器看到的工作区`

但 overlayfs 通常需要 root（或特定配置），而且清理要 `umount`。

如果你能接受这一点，我可以再给你一份 overlayfs + docker 的完整脚本模板。

---

## 重要注意事项（避免踩坑）

1. **务必 out-of-source 构建**  
   你的构建系统如果会在源码树里生成文件（如生成头文件、版本号文件），会被 `:ro` 拦住导致失败。解决：
   - 改为全部生成到 `/ws/build`；或
   - 对必须生成的少量目录单独做可写覆盖挂载（例如 `-v "$WS/gen:/ws/src/generated:rw"`）。

2. **缓存加速建议（强烈推荐）**
   - `ccache` 或 `sccache`：把缓存目录挂载成一个持久目录/卷（上面示例已做）。
   - CMake/Ninja：配合 `-G Ninja` 通常更快。

3. **模块覆盖挂载要确保路径一致**
   - `MODULE_IN_REPO` 必须精确对应仓库中的模块路径，否则你会改了但编译用的还是快照里的旧模块。

---

如果你告诉我：  
1) 你用的是 **CMake / Bazel / Make / Buck** 哪种；  
2) 模块在仓库中的真实路径；  
3) 宿主机文件系统（ext4/btrfs/xfs/zfs）；  
我可以把脚本进一步定制成“增量编译最快 + 最不容易出错”的版本（例如对 Bazel 的 output_base、对 CMake 的生成文件位置等做专门隔离）。