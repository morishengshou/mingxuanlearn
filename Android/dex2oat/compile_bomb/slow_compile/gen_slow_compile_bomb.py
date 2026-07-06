#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢编译炸弹 — 构造"超重"字节码,迫使 ART 优化编译器花费 15+ 分钟。

策略(不追求死锁,追求编译极慢):
  每个方法堆积以下优化器杀手:
  1. 极高虚拟寄存器数(400~500个) → 寄存器分配压力极大
  2. 大量基本块(150~300个) → 复杂 CFG → SSA/支配树昂贵
  3. 密集的 alu 运算(加/减/乘/除/位/浮点) → GVN 迭代至不动点极慢
  4. 大量数组访问(各类型) → BCE 对每个访问做界分析
  5. 大量字段访问(static+instance) → LSE 尝试消冗余
  6. 嵌套循环 → LICM 反复尝试外提
  7. Try/catch 包裹大段代码 → 异常边增加 CFG 支配复杂度
  8. invoke-virtual/static → 内联分析
  9. 多种类型混用(int/long/float/double/Object) → 类型传播复杂

生成规模:
  N_CLASSES = 12, METHODS_PER = 4 → 48 个超重方法
  每方法 ~15000 条指令 + ~200 个基本块 + ~450 个虚拟寄存器
  估计编译时间: 15~60 秒/方法 → 12~48 分钟总时长
"""

import os, random

N_CLASSES  = 12
METHODS    = 4       # 每类方法数
BLOCKS     = 180     # 每方法基本块数
INSNS      = 70      # 每块约多少条指令(实际随机 40~100)
VREGS      = 420     # 虚拟寄存器数
ARRAY_REGS = 30      # 数组引用用的寄存器数
LOOP_NEST  = 3       # 循环嵌套深度
OUT_DIR    = "slow_smali"
PACKAGE    = "Lslow"

random.seed(42)
os.makedirs(OUT_DIR, exist_ok=True)

INSN_POOL = [
    # (模板函数, 权重)
    # int 运算
    ("add_int",        8),
    ("sub_int",        8),
    ("mul_int",        6),
    ("div_int",        3),
    ("rem_int",        3),
    ("and_int",        4),
    ("or_int",         4),
    ("xor_int",        4),
    ("shl_int",        3),
    ("shr_int",        3),
    ("ushr_int",       3),
    # long 运算
    ("add_long",       5),
    ("sub_long",       5),
    ("mul_long",       3),
    ("div_long",       2),
    ("rem_long",       2),
    ("and_long",       3),
    ("or_long",        3),
    ("xor_long",       3),
    # float/double
    ("add_float",      4),
    ("sub_float",      4),
    ("mul_float",      4),
    ("div_float",      4),
    ("add_double",     3),
    ("sub_double",     3),
    ("mul_double",     3),
    ("div_double",     3),
    # 类型转换
    ("int_to_long",    2),
    ("int_to_float",   2),
    ("int_to_double",  2),
    ("long_to_int",    2),
    ("long_to_float",  2),
    ("long_to_double", 2),
    ("float_to_int",   2),
    ("float_to_long",  2),
    ("float_to_double",2),
    ("double_to_int",  2),
    ("double_to_long", 2),
    ("double_to_float",2),
    # 数组访问
    ("aget_int",       5),
    ("aput_int",       5),
    ("aget_wide",      4),
    ("aput_wide",      4),
    ("aget_object",    4),
    ("aput_object",    4),
    ("aget_byte",      4),
    ("aput_byte",      4),
    ("array_length",   3),
    # 字段访问
    ("iget_int",       4),
    ("iput_int",       4),
    ("iget_object",    3),
    ("iput_object",    3),
    ("sget_int",       3),
    ("sput_int",       3),
    # 对象操作
    ("new_instance",   2),
    ("new_array",      2),
    ("fill_array",     2),
    ("check_cast",     2),
    ("instance_of",    2),
    # 方法调用
    ("invoke_virtual", 3),
    ("invoke_static",  3),
    ("invoke_direct",  2),
    # 比较+移动
    ("cmp_int",        4),
    ("cmp_float",      2),
    ("cmp_double",     2),
    ("move",           6),
    ("move_result",    4),
    ("const",          6),
    ("const_wide",     4),
    ("const_string",   2),
]

# 预先算好累积权重作轮盘选择
total_w = sum(w for _, w in INSN_POOL)
cum_weights = []
cw = 0
for _, w in INSN_POOL:
    cw += w
    cum_weights.append(cw)


def pick_insn():
    """按权重随机选指令类型。"""
    r = random.randint(1, total_w)
    for i, c in enumerate(cum_weights):
        if r <= c:
            return INSN_POOL[i][0]
    return INSN_POOL[-1][0]


def insn_to_smali(kind, cls_name):
    """将指令类型转为具体 smali 行列表。cls_name 用于字段/方法引用。"""
    rd = random.randint(0, VREGS - 1)
    rs1 = random.randint(0, VREGS - 1)
    rs2 = random.randint(0, VREGS - 1)
    arr_r = random.randint(0, ARRAY_REGS - 1)
    idx_r = random.randint(0, VREGS - 1)

    if kind == "add_int":
        return [f"    add-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "sub_int":
        return [f"    sub-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "mul_int":
        return [f"    mul-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "div_int":
        # 除零会在运行时抛异常但编译无妨
        return [f"    div-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "rem_int":
        return [f"    rem-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "and_int":
        return [f"    and-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "or_int":
        return [f"    or-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "xor_int":
        return [f"    xor-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "shl_int":
        return [f"    shl-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "shr_int":
        return [f"    shr-int v{rd}, v{rs1}, v{rs2}"]
    elif kind == "ushr_int":
        return [f"    ushr-int v{rd}, v{rs1}, v{rs2}"]

    elif kind == "add_long":
        return [f"    add-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "sub_long":
        return [f"    sub-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "mul_long":
        return [f"    mul-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "div_long":
        return [f"    div-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "rem_long":
        return [f"    rem-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "and_long":
        return [f"    and-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "or_long":
        return [f"    or-long v{rd}, v{rs1}, v{rs2}"]
    elif kind == "xor_long":
        return [f"    xor-long v{rd}, v{rs1}, v{rs2}"]

    elif kind == "add_float":
        return [f"    add-float v{rd}, v{rs1}, v{rs2}"]
    elif kind == "sub_float":
        return [f"    sub-float v{rd}, v{rs1}, v{rs2}"]
    elif kind == "mul_float":
        return [f"    mul-float v{rd}, v{rs1}, v{rs2}"]
    elif kind == "div_float":
        return [f"    div-float v{rd}, v{rs1}, v{rs2}"]
    elif kind == "add_double":
        return [f"    add-double v{rd}, v{rs1}, v{rs2}"]
    elif kind == "sub_double":
        return [f"    sub-double v{rd}, v{rs1}, v{rs2}"]
    elif kind == "mul_double":
        return [f"    mul-double v{rd}, v{rs1}, v{rs2}"]
    elif kind == "div_double":
        return [f"    div-double v{rd}, v{rs1}, v{rs2}"]

    elif kind == "int_to_long":
        return [f"    int-to-long v{rd}, v{rs1}"]
    elif kind == "int_to_float":
        return [f"    int-to-float v{rd}, v{rs1}"]
    elif kind == "int_to_double":
        return [f"    int-to-double v{rd}, v{rs1}"]
    elif kind == "long_to_int":
        return [f"    long-to-int v{rd}, v{rs1}"]
    elif kind == "long_to_float":
        return [f"    long-to-float v{rd}, v{rs1}"]
    elif kind == "long_to_double":
        return [f"    long-to-double v{rd}, v{rs1}"]
    elif kind == "float_to_int":
        return [f"    float-to-int v{rd}, v{rs1}"]
    elif kind == "float_to_long":
        return [f"    float-to-long v{rd}, v{rs1}"]
    elif kind == "float_to_double":
        return [f"    float-to-double v{rd}, v{rs1}"]
    elif kind == "double_to_int":
        return [f"    double-to-int v{rd}, v{rs1}"]
    elif kind == "double_to_long":
        return [f"    double-to-long v{rd}, v{rs1}"]
    elif kind == "double_to_float":
        return [f"    double-to-float v{rd}, v{rs1}"]

    elif kind == "aget_int":
        return [f"    aget v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aput_int":
        return [f"    aput v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aget_wide":
        return [f"    aget-wide v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aput_wide":
        return [f"    aput-wide v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aget_object":
        return [f"    aget-object v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aput_object":
        return [f"    aput-object v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aget_byte":
        return [f"    aget-byte v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "aput_byte":
        return [f"    aput-byte v{rd}, v{arr_r}, v{idx_r}"]
    elif kind == "array_length":
        return [f"    array-length v{rd}, v{arr_r}"]

    elif kind == "iget_int":
        fi = random.randint(0, 7)
        return [f"    iget v{rd}, v{arr_r}, L{cls_name};->f{fi}:I"]
    elif kind == "iput_int":
        fi = random.randint(0, 7)
        return [f"    iput v{rd}, v{arr_r}, L{cls_name};->f{fi}:I"]
    elif kind == "iget_object":
        fi = random.randint(0, 7)
        return [f"    iget-object v{rd}, v{arr_r}, L{cls_name};->f{fi}:Ljava/lang/Object;"]
    elif kind == "iput_object":
        fi = random.randint(0, 7)
        return [f"    iput-object v{rd}, v{arr_r}, L{cls_name};->f{fi}:Ljava/lang/Object;"]
    elif kind == "sget_int":
        return [f"    sget v{rd}, L{cls_name};->sf0:I"]
    elif kind == "sput_int":
        return [f"    sput v{rd}, L{cls_name};->sf0:I"]

    elif kind == "new_instance":
        return [f"    new-instance v{rd}, L{cls_name};",
                f"    invoke-direct {{v{rd}}}, L{cls_name};-><init>()V"]
    elif kind == "new_array":
        return [f"    new-array v{rd}, v{idx_r}, [I"]
    elif kind == "fill_array":
        return [f"    fill-array-data v{rd}, :array_data_{random.randint(0,9)}"]
    elif kind == "check_cast":
        return [f"    check-cast v{rd}, L{cls_name};"]
    elif kind == "instance_of":
        return [f"    instance-of v{rd}, v{rs1}, L{cls_name};"]

    elif kind == "invoke_virtual":
        mi = random.randint(0, 9)
        return [f"    invoke-virtual {{v{rd}}}, L{cls_name};->helper{mi}()I",
                f"    move-result v{rs1}"]
    elif kind == "invoke_static":
        mi = random.randint(0, 9)
        return [f"    invoke-static {{v{rd}, v{rs1}}}, L{cls_name};->helper{mi}(I)I",
                f"    move-result v{rs2}"]
    elif kind == "invoke_direct":
        return [f"    invoke-direct {{v{rd}}}, L{cls_name};-><init>()V"]

    elif kind == "cmp_int":
        return [f"    if-eq v{rd}, v{rs1}, :block_{random.randint(0, BLOCKS-1)}"]
    elif kind == "cmp_float":
        return [f"    cmpg-float v{rd}, v{rs1}, v{rs2}",
                f"    if-ltz v{rd}, :block_{random.randint(0, BLOCKS-1)}"]
    elif kind == "cmp_double":
        return [f"    cmpg-double v{rd}, v{rs1}, v{rs2}",
                f"    if-ltz v{rd}, :block_{random.randint(0, BLOCKS-1)}"]
    elif kind == "move":
        return [f"    move v{rd}, v{rs1}"]
    elif kind == "move_result":
        return [f"    move-result v{rd}"]
    elif kind == "const":
        return [f"    const/4 v{rd}, 0x{random.randint(1,15):x}"]
    elif kind == "const_wide":
        return [f"    const-wide/16 v{rd}, 0x{random.randint(1,0x7fff):x}"]
    elif kind == "const_string":
        return [f"    const-string v{rd}, \"s{random.randint(0,99)}\""]

    return [f"    # nop"]


def generate_cfg():
    """
    生成 CFG 邻接表和循环结构。
    返回: successors[i] = [后继块索引列表], back_edges, loop_headers
    每个块有 1~3 个后继(部分形成回边→循环)。
    """
    succs = {i: [] for i in range(BLOCKS)}

    # 前向边: 块 i 有 1-2 个后继(前向)
    for i in range(BLOCKS - 1):
        n_fwd = random.choices([1, 2], weights=[3, 7])[0]  # 70% 有前向分支
        targets = [i + 1]
        if n_fwd > 1 and i + random.randint(3, 10) < BLOCKS:
            targets.append(i + random.randint(3, 10))
        targets = list(set(targets))
        succs[i].extend(targets)

    # 最后一个块或许回到某个早期块
    last = BLOCKS - 1
    if random.random() < 0.6:
        succs[last].append(random.randint(BLOCKS//3, BLOCKS-2))

    # 回边: LOOP_NEST 层嵌套循环
    loop_headers = []
    back_edges = []
    for depth in range(LOOP_NEST):
        # 外层循环包住内层
        lo = random.randint(BLOCKS//5 + depth*BLOCKS//6, BLOCKS//5 + (depth+1)*BLOCKS//6 - 4)
        hi = lo + random.randint(5, 15)
        if hi >= BLOCKS - 1:
            hi = BLOCKS - 2
        loop_headers.append(lo)
        # 从 hi 回到 lo(回边)
        back_edges.append((hi, lo))
        if lo not in succs.get(hi, []):
            succs.setdefault(hi, []).append(lo)

    return succs, back_edges, loop_headers


def generate_method(cls_name, method_idx):
    """生成一个超重方法。"""
    succs, back_edges, loop_headers = generate_cfg()

    lines = []
    lines.append(f".method public heavy{method_idx}()V")
    lines.append(f"    .registers {VREGS + 20}")
    lines.append("")

    # 序言: 初始化寄存器 + 创建数组(给 BCE 喂数据)
    lines.append("    # === 初始化: 创建数组 + 填充常量 ===")
    for i in range(ARRAY_REGS):
        sz = random.choice([0x40, 0x80, 0x100, 0x200, 0x400])
        arr_type = random.choice(["[I", "[B", "[J", "[F", "[D",
                                   "[Ljava/lang/Object;", "[Ljava/lang/String;"])
        lines.append(f"    const/16 v{i+1}, {hex(sz)}")
        lines.append(f"    new-array v{i}, v{i+1}, {arr_type}")
        if random.random() < 0.3:
            # 偶尔填一些元素
            lines.append(f"    const/4 v{i+2}, 0x0")
            lines.append(f"    const/4 v{i+3}, 0x2a")
            lines.append(f"    aput v{i+3}, v{i}, v{i+2}")

    # 初始化更多常量寄存器(GVN 有料可啃)
    for i in range(ARRAY_REGS, VREGS):
        if random.random() < 0.15:
            lines.append(f"    const/4 v{i}, 0x{random.randint(1,15):x}")
        elif random.random() < 0.05:
            lines.append(f"    const/16 v{i}, 0x{random.randint(0x10,0xFF):x}")

    lines.append("")

    # Try/catch 包裹段
    try_ranges = []
    for tc in range(4):
        a = random.randint(0, BLOCKS - 30)
        b = random.randint(a + 1, min(a + 40, BLOCKS - 10))
        hi_start = max(b + 1, BLOCKS - 20)
        if hi_start >= BLOCKS - 1:
            hi_start = BLOCKS - 3
        h = random.randint(hi_start, BLOCKS - 2)
        try_ranges.append((a, b, h))
        lines.append(f"    .catch Ljava/lang/Exception; {{:try_start_{tc} .. :try_end_{tc}}} :catch_{tc}")
    if try_ranges:
        lines.append("")

    # === 基本块 ===
    for bi in range(BLOCKS):
        is_loop_hdr = bi in loop_headers
        is_back_src = bi in [be[0] for be in back_edges]

        # Try/catch 标记
        for tc, (a, b, h) in enumerate(try_ranges):
            if bi == a:
                lines.append(f"    :try_start_{tc}")
            if bi == b:
                lines.append(f"    :try_end_{tc}")

        if is_loop_hdr:
            depth = loop_headers.index(bi)
            lines.append(f"    # ═══ 循环深度{depth+1}: 入口 block_{bi} ═══")

        lines.append(f"    :block_{bi}")

        # 块体指令(随机 40~100 条)
        n_insn = random.randint(INSNS - 30, INSNS + 30)
        for _ in range(n_insn):
            kind = pick_insn()
            lines.extend(insn_to_smali(kind, cls_name))

        # 块结尾: 分支到后继
        my_succ = succs.get(bi, [])
        if not my_succ:
            # 无后继 → goto 出口块
            lines.append(f"    goto/32 :block_{BLOCKS - 2}")
        elif len(my_succ) == 1:
            target = my_succ[0]
            if target != bi + 1 or random.random() < 0.3:
                # 显式 goto 也增加 CFG 边
                lines.append(f"    goto/32 :block_{target}")
            # else: fallthrough(implicit)
        else:
            # 条件分支: if-eq 去 my_succ[1], goto 去 my_succ[0]
            cmp_r1 = random.randint(0, VREGS - 1)
            cmp_r2 = random.randint(0, VREGS - 1)
            t0, t1 = my_succ[0], my_succ[1]
            cond = random.choice(["if-eq", "if-ne", "if-lt", "if-ge", "if-gt", "if-le"])
            lines.append(f"    {cond} v{cmp_r1}, v{cmp_r2}, :block_{t1}")
            if random.random() < 0.4:
                lines.append(f"    goto/32 :block_{t0}")

        # 增加跨块数据流: 向几个随机寄存器写值(产生 phi 节点)
        for _ in range(random.randint(1, 4)):
            vr = random.randint(0, VREGS - 1)
            vs = random.randint(0, VREGS - 1)
            lines.append(f"    add-int v{vr}, v{vs}, v{vs}")

        lines.append("")

    # === Catch handler 块 ===
    for tc, (a, b, h) in enumerate(try_ranges):
        lines.append(f"    :catch_{tc}")
        lines.append("    move-exception v400")
        for _ in range(random.randint(20, 40)):
            kind = pick_insn()
            lines.extend(insn_to_smali(kind, cls_name))
        lines.append(f"    goto/32 :block_{h}")
        lines.append("")

    # 出口 + 返回
    lines.append(f"    :block_{BLOCKS-1}")
    lines.append("    return-void")
    lines.append(".end method")
    return lines


def generate_class(cls_idx):
    """生成一个包含多个超重方法的类。"""
    cls_name = f"C{cls_idx}"
    lines = [f".class public {PACKAGE}/{cls_name};",
             ".super Ljava/lang/Object;", ""]

    # 字段(供 LSE 优化)
    for fi in range(8):
        t = random.choice(["I", "J", "F", "D", "Ljava/lang/Object;"])
        lines.append(f".field public f{fi}:{t}")
    lines.append(f".field public static sf0:I")
    lines.append("")

    # 构造
    lines.append(".method public constructor <init>()V")
    lines.append("    .registers 1")
    lines.append("    invoke-direct {p0}, Ljava/lang/Object;-><init>()V")
    lines.append("    return-void")
    lines.append(".end method\n")

    # Helper 方法(供 invoke → 内联分析)
    for mi in range(10):
        lines.append(f".method public helper{mi}()I")
        lines.append("    .registers 3")
        lines.append("    const/4 v0, 0x0")
        lines.append("    const/16 v1, 0x100")
        lines.append(f"    :helper_loop_{cls_idx}_{mi}")
        lines.append("    add-int/lit8 v0, v0, 0x1")
        lines.append("    if-lt v0, v1, :helper_loop_" + f"{cls_idx}_{mi}")
        lines.append("    return v0")
        lines.append(".end method\n")

    # 含参 helper
    for mi in range(10):
        lines.append(f".method public static helper{mi}(I)I")
        lines.append("    .registers 4")
        lines.append("    mul-int/lit8 v1, v0, 0x3")
        lines.append("    add-int/lit8 v2, v1, 0x7")
        lines.append("    rem-int/lit8 v3, v2, 0xd")
        lines.append("    return v3")
        lines.append(".end method\n")

    # 超重方法
    for mi in range(METHODS):
        lines.extend(generate_method(cls_name, mi))
        lines.append("")

    path = os.path.join(OUT_DIR, f"Bomb_{cls_name}.smali")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return cls_name


# --- main ---
for ci in range(N_CLASSES):
    cn = generate_class(ci)
    if ci % 2 == 0:
        print(f"  生成 Bomb_{cn}.smali...")

total = len(os.listdir(OUT_DIR))
# approx stats
approx_insn_per_m = (BLOCKS * INSNS)
approx_total_insn = N_CLASSES * METHODS * approx_insn_per_m
approx_size_kb = sum(os.path.getsize(os.path.join(OUT_DIR, f))
                     for f in os.listdir(OUT_DIR)) / 1024

print(f"\n{total} 个 smali 文件 ({N_CLASSES} 个类 × {METHODS} 超重方法)")
print(f"  每方法: ~{BLOCKS} 基本块 × ~{INSNS} 指令 ≈ ~{approx_insn_per_m:,} 条")
print(f"  总指令: ~{approx_total_insn:,} 条")
print(f"  虚拟寄存器: {VREGS} 个/方法(物理 ARM64 仅 32 个→分配压力极大)")
print(f"  类型混用: int/long/float/double/Object/array 六种")
print(f"  优化器杀手: GVN/LICM/BCE/LSE/寄存器分配/内联")
print(f"  总 smali 大小: ~{approx_size_kb/1024:.1f} MB")
print(f"\n估计编译时间: 15~60 分钟(取决于设备和 -j 线程数)")
print(f"\n编译: java -jar smali.jar assemble {OUT_DIR}/ -o slow_bomb.dex")
print(f"触发: dex2oat --dex-file=slow_bomb.dex --oat-file=/tmp/s.oat \\")
print(f"         --compiler-filter=speed -j4 --watchdog-timeout=3600000")
print(f"\n(单线程 -j1 可最大化单方法感知耗时;多线程 -j8 给总耗时更多并行机会)")
