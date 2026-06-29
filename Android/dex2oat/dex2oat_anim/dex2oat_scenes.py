# -*- coding: utf-8 -*-
"""
dex2oat 编译原理动画（Android 12 / ART）+ 中文离线旁白
基于 art/dex2oat 真实源码流程制作。

包含 4 个场景：
  Scene1_Overview   总览：输入/输出 + 触发场景
  Scene2_Phases     编译主流程各阶段（main -> Compile -> Write）
  Scene3_Parallel   并行编译模型（ThreadPool + 原子游标）与"挂死"
  Scene4_WatchDog   看门狗时间线与"被限速到超时"（华为场景）

旁白：离线 Windows SAPI（Microsoft Huihui，zh-CN），见 vo_service.py
渲染：见同目录 render.ps1（注意带旁白需用 VoiceoverScene）
依赖：manim 0.20.x + manim-voiceover；仅用 Text，不需要 LaTeX
"""

from manim import *
import numpy as np
from manim_voiceover import VoiceoverScene
from vo_service import make_zh_service

CN_FONT = "Microsoft YaHei"      # Windows 自带中文字体
MONO = "Consolas"

# 配色
C_DEX = "#4FC3F7"     # 输入 dex（蓝）
C_TOOL = "#FFB74D"    # dex2oat 工具（橙）
C_OAT = "#81C784"     # 产物（绿）
C_PHASE = "#64B5F6"   # 阶段框
C_HOT = "#E57373"     # 热路径/危险（红）
C_OK = "#81C784"      # 正常（绿）
C_DIM = "#90A4AE"     # 次要灰
C_HL = "#FFD54F"      # 高亮黄


def cn(text, size=32, color=WHITE, weight=NORMAL):
    return Text(text, font=CN_FONT, font_size=size, color=color, weight=weight)


def code(text, size=22, color=WHITE):
    return Text(text, font=MONO, font_size=size, color=color)


def box(label, w=2.6, h=1.1, fill=C_PHASE, fopacity=0.18, tsize=26, scolor=None):
    scolor = scolor or fill
    rect = RoundedRectangle(corner_radius=0.15, width=w, height=h,
                            stroke_color=scolor, stroke_width=3,
                            fill_color=fill, fill_opacity=fopacity)
    txt = cn(label, size=tsize)
    txt.move_to(rect.get_center())
    return VGroup(rect, txt)


def footnote(text):
    return cn(text, size=18, color=C_DIM).to_edge(DOWN, buff=0.25)


# ---------------------------------------------------------------------------
class Scene1_Overview(VoiceoverScene):
    def construct(self):
        self.set_speech_service(make_zh_service())

        title = cn("dex2oat 是什么：ART 的 AOT 提前编译器", size=40, color=C_HL).to_edge(UP, buff=0.4)

        with self.voiceover(text=(
            "dex2oat 是 ART 运行时的提前编译器，也就是 AOT 编译器，"
            "它把应用里的 dex 字节码，提前翻译成目标 CPU 的本地机器码。"
            "一个容易被忽略的点是：dex2oat 并不是常驻服务，而是一个独立的可执行程序，"
            "每次需要编译时由系统临时拉起，编译完就退出。"
        )):
            self.play(Write(title))

        # 输入
        apk_rect = RoundedRectangle(corner_radius=0.15, width=2.8, height=1.6,
                                    stroke_color=C_DEX, stroke_width=3,
                                    fill_color=C_DEX, fill_opacity=0.18)
        apk_label = cn("APK / jar", size=26).move_to(apk_rect.get_top() + DOWN * 0.4)
        dex = box(".dex 字节码", w=2.2, h=0.7, fill=C_DEX, fopacity=0.35, tsize=20)
        dex.move_to(apk_rect.get_center() + DOWN * 0.35)
        apk_grp = VGroup(apk_rect, apk_label, dex).to_edge(LEFT, buff=0.8)
        tool = box("dex2oat", w=3.0, h=1.8, fill=C_TOOL, fopacity=0.25, tsize=36)
        tool_sub = cn("AOT 编译器", size=18, color=C_DIM).next_to(tool, DOWN, buff=0.12)
        tool_grp = VGroup(tool, tool_sub).move_to(ORIGIN)
        a1 = Arrow(apk_grp.get_right(), tool.get_left(), buff=0.2, color=WHITE, stroke_width=5)

        with self.voiceover(text="输入是 APK 或 jar 包里的 dex 文件，它们被喂给 dex2oat。"):
            self.play(FadeIn(apk_grp, shift=RIGHT * 0.3))
            self.play(GrowFromCenter(tool_grp))
            self.play(GrowArrow(a1))

        oat = box(".oat / .odex", w=2.8, h=0.8, fill=C_OAT, tsize=22)
        vdex = box(".vdex", w=2.8, h=0.8, fill=C_OAT, tsize=22)
        art = box(".art (image)", w=2.8, h=0.8, fill=C_OAT, tsize=22)
        outs = VGroup(oat, vdex, art).arrange(DOWN, buff=0.35).to_edge(RIGHT, buff=0.8)
        a2 = Arrow(tool.get_right(), oat.get_left(), buff=0.2, color=C_OAT, stroke_width=4)
        a3 = Arrow(tool.get_right(), vdex.get_left(), buff=0.2, color=C_OAT, stroke_width=4)
        a4 = Arrow(tool.get_right(), art.get_left(), buff=0.2, color=C_OAT, stroke_width=4)
        notes = VGroup(
            cn("机器码（CPU 直接执行）", size=16, color=C_DIM).next_to(oat, DOWN, buff=0.18),
            cn("已校验的 dex + 校验结果", size=16, color=C_DIM).next_to(vdex, DOWN, buff=0.18),
            cn("预初始化对象堆，加速加载", size=16, color=C_DIM).next_to(art, DOWN, buff=0.18),
        )

        with self.voiceover(text=(
            "输出有三类。第一是 oat，编译后的机器码。这里有个常被忽略的细节："
            "oat 并不是裸文件，而是被封装在一个 ELF 动态库，也就是 so 文件里。"
            "第二是 vdex，它保存了校验过的 dex 和校验结果，"
            "这样下次编译可以跳过重复校验，是提速的关键。"
            "第三是 art 镜像，预先初始化好对象堆，加快加载。"
        )):
            self.play(GrowArrow(a2), GrowArrow(a3), GrowArrow(a4), FadeIn(outs))
            self.play(LaggedStartMap(FadeIn, notes, lag_ratio=0.3))

        why = cn("字节码 → 提前译成机器码 → 运行时不必每次解释/JIT，启动更快",
                 size=22, color=C_HL).to_edge(DOWN, buff=0.5)
        with self.voiceover(text=(
            "这样做的目的，是让应用运行时不必每次都解释执行或即时编译，从而启动更快、更省电。"
        )):
            self.play(Write(why))

        self.play(FadeOut(VGroup(apk_grp, tool_grp, outs, notes, a1, a2, a3, a4, why)))

        sub = cn("dex2oat 何时被触发？（由 installd 拉起，不是你直接调用）",
                 size=28, color=C_HL).next_to(title, DOWN, buff=0.55)
        trig = VGroup(
            box("应用安装/更新", w=3.0, h=0.95, fill=C_DEX, tsize=22),
            box("系统升级后首次开机\n（批量 dexopt，最显眼）", w=3.4, h=1.15, fill=C_HOT, fopacity=0.22, tsize=19),
            box("空闲充电时\n后台优化", w=2.8, h=1.0, fill=C_DEX, tsize=20),
        ).arrange(RIGHT, buff=0.7).next_to(sub, DOWN, buff=0.65)
        installd = box("installd", w=2.2, h=0.85, fill=C_TOOL, tsize=24)
        d2o = box("dex2oat", w=2.2, h=0.85, fill=C_TOOL, fopacity=0.3, tsize=24)
        chain = VGroup(installd, d2o).arrange(RIGHT, buff=1.2).next_to(trig, DOWN, buff=0.7)
        ca = Arrow(installd.get_right(), d2o.get_left(), buff=0.15, color=WHITE)
        arrows = VGroup(*[Arrow(t.get_bottom(), installd.get_top(), buff=0.15,
                                color=C_DIM, stroke_width=3) for t in trig])

        with self.voiceover(text=(
            "那么 dex2oat 什么时候被触发？它总是由 installd 拉起，而不是你直接调用。"
            "常见有三种时机：安装或更新应用、系统升级后首次开机的批量编译、以及空闲充电时的后台优化。"
            "其中，开机批量编译最容易出现卡死，也最显眼。"
            "还有一个容易忽略的细节：installd 会把 dex2oat 放进后台进程组，也就是 background 这个 cgroup，"
            "这直接关系到后面要讲的限速问题。"
        )):
            self.play(Write(sub))
            self.play(LaggedStartMap(FadeIn, trig, lag_ratio=0.3))
            self.play(*[GrowArrow(a) for a in arrows], FadeIn(installd))
            self.play(GrowArrow(ca), FadeIn(d2o))
            self.play(Indicate(trig[1], color=C_HOT, scale_factor=1.1))

        self.play(FadeIn(footnote("源码：main() dex2oat.cc:3182 ｜ 调用方 installd: frameworks/native/cmds/installd/dexopt.cpp")))
        self.wait(0.8)


# ---------------------------------------------------------------------------
class Scene2_Phases(VoiceoverScene):
    def construct(self):
        self.set_speech_service(make_zh_service())

        title = cn("dex2oat 主流程（DoCompilation 各阶段）", size=38, color=C_HL).to_edge(UP, buff=0.35)
        top = VGroup(
            box("main()", w=2.0, h=0.7, fill=C_DIM, tsize=22),
            box("Dex2oat()", w=2.2, h=0.7, fill=C_DIM, tsize=22),
            box("DoCompilation()", w=2.8, h=0.7, fill=C_DIM, tsize=22),
        ).arrange(RIGHT, buff=0.5).next_to(title, DOWN, buff=0.4)
        ta = VGroup(Arrow(top[0].get_right(), top[1].get_left(), buff=0.1, color=C_DIM),
                    Arrow(top[1].get_right(), top[2].get_left(), buff=0.1, color=C_DIM))

        with self.voiceover(text=(
            "我们来看 dex2oat 的主流程。从 main 函数进入，到 Dex2oat 这个总函数，再到 DoCompilation。"
        )):
            self.play(Write(title))
            self.play(FadeIn(top), *[GrowArrow(a) for a in ta])

        stages = [
            ("ParseArgs：解析参数 + 启动看门狗", C_PHASE, "dex2oat.cc:843"),
            ("Setup：建 Runtime，打开输入 dex", C_PHASE, "dex2oat.cc:1415"),
            ("Compile：编译（CPU 密集核心）", C_HOT, "dex2oat.cc:1831"),
            ("WriteOutputFiles：写 oat/ELF（I/O 密集）", C_HOT, "dex2oat.cc:2052"),
            ("HandleImage：生成 boot.art / app image", C_PHASE, "dex2oat.cc:2207"),
        ]
        rows = VGroup()
        for label, col, ref in stages:
            r = box(label, w=6.2, h=0.78, fill=col, fopacity=0.18, tsize=21)
            ref_t = code(ref, size=13, color=C_DIM).next_to(r, RIGHT, buff=0.12)
            rows.add(VGroup(r, ref_t))
        rows.arrange(DOWN, buff=0.30).next_to(top, DOWN, buff=0.5).align_to(top, LEFT).shift(LEFT * 1.3)

        with self.voiceover(text=(
            "整个过程分成几个阶段。第一步 ParseArgs 解析命令行参数。"
            "这里有个容易忽略的细节：看门狗线程其实在解析参数阶段就已经启动了，早于真正的编译。"
            "第二步 Setup 创建运行时——注意，dex2oat 内部会启动一个完整的小型 ART 运行时，然后打开输入的 dex。"
        )):
            self.play(FadeIn(rows[0][0], shift=DOWN * 0.15), FadeIn(rows[0][1]))
            self.play(FadeIn(rows[1][0], shift=DOWN * 0.15), FadeIn(rows[1][1]),
                      GrowArrow(Arrow(rows[0][0].get_bottom(), rows[1][0].get_top(), buff=0.05, color=WHITE, stroke_width=3)))

        with self.voiceover(text=(
            "第三步 Compile 是核心，CPU 密集。之后 WriteOutputFiles 把结果序列化成 oat 和 ELF，这是 I/O 密集阶段。"
            "最后 HandleImage 生成镜像文件。"
        )):
            prev = rows[1][0]
            for grp in rows[2:]:
                self.play(FadeIn(grp[0], shift=DOWN * 0.15), FadeIn(grp[1]),
                          GrowArrow(Arrow(prev.get_bottom(), grp[0].get_top(), buff=0.05, color=WHITE, stroke_width=3)),
                          run_time=0.7)
                prev = grp[0]

        inner_title = cn("Compile 内部：PreCompile → CompileAll", size=22, color=C_HL)
        inner = [
            "LoadImageClasses",
            "Resolve（解析符号，并行）",
            "Verify（字节码校验，并行）",
            "InitializeClasses",
            "CompileAll（逐方法生成机器码，并行）",
        ]
        chips = VGroup(*[box(t, w=3.8, h=0.6,
                             fill=C_HOT if ("CompileAll" in t or "Verify" in t) else C_PHASE,
                             fopacity=0.16, tsize=17) for t in inner])
        chips.arrange(DOWN, buff=0.18)
        panel = VGroup(inner_title, chips).arrange(DOWN, buff=0.28).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)

        with self.voiceover(text=(
            "我们展开 Compile 内部。它先做 PreCompile：加载镜像类、解析符号、校验字节码、初始化类；"
            "再做 CompileAll，逐个方法生成机器码。"
            "一个容易忽略的关键点是：解析、校验、编译这三步都是多线程并行执行的，这正是卡死的高发区。"
            "还有个细节：全部完成后，main 函数会直接调用 FastExit 退出进程，故意跳过运行时析构来省时间。"
        )):
            self.play(Indicate(rows[2][0], color=C_HOT))
            self.play(Write(inner_title))
            self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.2) for m in chips], lag_ratio=0.25))

        self.play(FadeIn(footnote("PreCompile: compiler_driver.cc:762 ｜ CompileAll: compiler_driver.cc:335 ｜ FastExit: dex2oat.cc:3187")))
        self.wait(0.8)


# ---------------------------------------------------------------------------
class Scene3_Parallel(VoiceoverScene):
    def construct(self):
        self.set_speech_service(make_zh_service())

        title = cn("并行编译模型与「挂死」 (ParallelCompilationManager)", size=32, color=C_HL).to_edge(UP, buff=0.35)
        n = 8
        cells = VGroup(*[Square(side_length=0.62, stroke_color=C_DIM, stroke_width=2,
                               fill_color=C_DEX, fill_opacity=0.25) for _ in range(n)])
        cells.arrange(RIGHT, buff=0.12).shift(UP * 1.7)
        labels = VGroup(*[code(f"m{i}", size=16) for i in range(n)])
        for c, l in zip(cells, labels):
            l.move_to(c.get_center())
        queue_t = cn("任务队列：待编译方法 m0..mN", size=20, color=C_DIM).next_to(cells, UP, buff=0.2)

        with self.voiceover(text=(
            "这一节讲并行编译模型，以及它为什么会挂死。"
            "所有待编译的方法被放进一个任务队列。"
        )):
            self.play(Write(title))
            self.play(FadeIn(queue_t), LaggedStartMap(FadeIn, cells, lag_ratio=0.1), FadeIn(labels))

        idx_t = code("index_ (原子)", size=18, color=C_HL)
        pointer = Triangle(color=C_HL, fill_color=C_HL, fill_opacity=1).scale(0.18).rotate(PI)
        pointer.next_to(cells[0], UP, buff=0.05)
        idx_t.next_to(pointer, UP, buff=0.1)
        workers = VGroup(*[box(f"worker {i}", w=2.2, h=0.8, fill=C_OK, fopacity=0.2, tsize=20)
                           for i in range(4)])
        workers.arrange(RIGHT, buff=0.5).shift(DOWN * 0.3)

        with self.voiceover(text=(
            "有一个原子计数器 index，指向下一个待处理的任务。"
            "容易忽略的细节是：worker 线程通过原子的 fetch_add 来抢任务，这是一种无锁的任务分发。"
            "多个 worker 线程并行地从队列里取方法来编译。"
        )):
            self.play(FadeIn(idx_t), FadeIn(pointer))
            self.play(LaggedStartMap(FadeIn, workers, lag_ratio=0.15))

        main_box = box("主线程: thread_pool_->Wait()  ←阻塞等所有任务完成",
                       w=9.5, h=0.8, fill=C_PHASE, fopacity=0.18, tsize=20).shift(DOWN * 1.9)

        with self.voiceover(text=(
            "主线程则停在 Wait 这一步，阻塞等待所有任务完成。"
            "这里有个关键细节：主线程在等待时必须处于挂起状态，而不是可运行状态，否则会挡住垃圾回收。"
        )):
            self.play(FadeIn(main_box))

        def assign(wi, ci):
            self.play(pointer.animate.next_to(cells[min(ci + 1, n - 1)], UP, buff=0.05),
                      cells[ci].animate.set_fill(C_OK, opacity=0.5),
                      Indicate(workers[wi], color=C_OK, scale_factor=1.05),
                      run_time=0.45)

        with self.voiceover(text=(
            "正常情况下，每个 worker 循环调用 NextIndex 抢下一个任务，全部做完，主线程才返回。"
        )):
            for wi, ci in [(0, 0), (1, 1), (2, 2), (3, 3), (0, 4), (1, 5)]:
                assign(wi, ci)

        stuck = cells[6]
        # 齿轮放在 worker2 上方而非覆盖其上
        gear = cn("⟳", size=40, color=C_HOT).next_to(workers[2], UP, buff=0.25)
        link = DashedLine(workers[2].get_top(), stuck.get_bottom(), color=C_HOT, stroke_width=3)
        stuck_label = cn("worker2 卡在 m6\n(死锁/死循环/等锁/等GC)", size=18, color=C_HOT)
        stuck_label.next_to(workers[2], DOWN, buff=0.25)

        with self.voiceover(text=(
            "但是，只要有一个 worker 卡住——比如死锁、死循环、等一个永远不来的锁，"
            "或者在等垃圾回收——那么这个任务就永远不会完成。"
        )):
            self.play(stuck.animate.set_fill(C_HOT, opacity=0.6).set_stroke(C_HOT, 4),
                      workers[2][0].animate.set_fill(C_HOT, opacity=0.35).set_stroke(C_HOT, 4),
                      workers[2][1].animate.set_color(C_HOT))
            self.play(Create(link), FadeIn(stuck_label))
            self.play(Rotate(gear, angle=4 * PI), run_time=2.0)

        forever = cn("→ 只要一个 worker 不返回，主线程 Wait() 永远阻塞 = 挂死",
                     size=22, color=C_HOT).to_edge(DOWN, buff=0.3)

        with self.voiceover(text=(
            "而主线程的 Wait 没有超时，它会一直等下去，结果就是整个 dex2oat 挂死。"
            "容易忽略的排查要点是：抓栈时你会看到主线程停在线程池的 Wait，"
            "但真正的元凶在某个 worker 线程，必须去看 worker 的栈。"
        )):
            self.play(main_box[0].animate.set_fill(C_HOT, opacity=0.22).set_stroke(C_HOT, 4),
                      main_box[1].animate.set_color(C_HOT))
            self.play(Write(forever))
            self.play(Rotate(gear, angle=4 * PI), run_time=2.0)

        # 展示脚注前先移走 forever，避免重叠
        self.play(FadeOut(forever))
        self.play(FadeIn(footnote("ForAllLambda: compiler_driver.cc:1397 ｜ Wait(): compiler_driver.cc:1414")))
        self.wait(0.8)


# ---------------------------------------------------------------------------
class Scene4_WatchDog(VoiceoverScene):
    def construct(self):
        self.set_speech_service(make_zh_service())

        title = cn("WatchDog 看门狗：9.5 分钟超时自杀，避免拖垮系统", size=32, color=C_HL).to_edge(UP, buff=0.35)

        x0, x1, vmax = -5.3, 5.3, 11.0

        def v2p(v):
            return np.array([x0 + (x1 - x0) * (v / vmax), -0.2, 0])

        axis_line = Line(v2p(0), v2p(vmax), color=C_DIM, stroke_width=3)
        ticks = VGroup()
        for v in range(0, 11, 2):
            tk = Line(v2p(v) + UP * 0.1, v2p(v) + DOWN * 0.1, color=C_DIM, stroke_width=2)
            lbl = code(str(v), size=18, color=C_DIM).next_to(tk, DOWN, buff=0.1)
            ticks.add(VGroup(tk, lbl))
        axis_label = cn("时间（分钟）", size=18, color=C_DIM).next_to(axis_line, DOWN, buff=0.45).to_edge(RIGHT, buff=1.0)

        with self.voiceover(text=(
            "最后讲看门狗。dex2oat 自带一个看门狗线程，超时就让自己退出，避免拖垮整个系统。"
        )):
            self.play(Write(title))
            self.play(Create(axis_line), FadeIn(ticks), FadeIn(axis_label))

        # 缩短看门狗虚线，不压到顶部内容
        wd95 = DashedLine(v2p(9.5) + UP * 1.8, v2p(9.5) + DOWN * 0.3, color=C_HOT, stroke_width=4)
        wd95_t = cn("dex2oat 看门狗 9.5min", size=16, color=C_HOT).next_to(wd95, UP, buff=0.1).shift(LEFT * 0.3)
        wd10 = DashedLine(v2p(10) + UP * 1.1, v2p(10) + DOWN * 0.3, color=ORANGE, stroke_width=3)
        wd10_t = cn("PMS 看门狗 10min", size=14, color=ORANGE).next_to(wd10, RIGHT, buff=0.05).shift(UP * 0.4)
        reason = cn("设计：dex2oat 比 PMS 略早自杀，免得连累 system_server", size=17, color=C_DIM).next_to(title, DOWN, buff=0.28)

        with self.voiceover(text=(
            "默认超时是九分半钟。这个值是精心设计的：它比 PackageManager 的十分钟看门狗略短，"
            "目的是让 dex2oat 先自杀，免得连累 system_server 被它的看门狗打死。"
            "这里有两个容易忽略的细节：调试版本的超时会再乘以五倍；"
            "而且看门狗用的是单调时钟，不受系统时间被调整的影响。"
        )):
            self.play(Create(wd95), FadeIn(wd95_t), Create(wd10), FadeIn(wd10_t))
            self.play(FadeIn(reason))

        barA_bg = Rectangle(width=v2p(9.5)[0] - v2p(0)[0], height=0.5,
                            stroke_color=C_DIM, fill_color=C_DIM, fill_opacity=0.12)
        barA_bg.move_to(v2p(0), aligned_edge=LEFT).shift(UP * 1.4)
        labelA = cn("正常：编译 2min 完成 → 看门狗被取消", size=20, color=C_OK).next_to(barA_bg, UP, buff=0.15).align_to(barA_bg, LEFT)
        tA = ValueTracker(0)
        barA = always_redraw(lambda: Rectangle(
            width=max(0.001, v2p(tA.get_value())[0] - v2p(0)[0]), height=0.5,
            stroke_width=0, fill_color=C_OK, fill_opacity=0.7
        ).move_to(barA_bg.get_left(), aligned_edge=LEFT))
        checkA = cn("✓ 完成", size=22, color=C_OK).next_to(v2p(2.0), UP, buff=0.5)

        with self.voiceover(text=(
            "正常情况下，编译两分钟就完成了，看门狗会被提前唤醒并取消，不会误杀。"
        )):
            self.play(FadeIn(barA_bg), FadeIn(labelA), FadeIn(barA))
            self.play(tA.animate.set_value(2.0), run_time=1.6, rate_func=linear)
            self.play(FadeIn(checkA, scale=1.3))

        barB_bg = barA_bg.copy().shift(DOWN * 1.0)
        labelB = cn("华为热控/小核限速：编译被拖慢…", size=20, color=C_HOT).next_to(barB_bg, DOWN, buff=0.15).align_to(barB_bg, LEFT)
        tB = ValueTracker(0)
        barB = always_redraw(lambda: Rectangle(
            width=max(0.001, v2p(min(tB.get_value(), 9.5))[0] - v2p(0)[0]), height=0.5,
            stroke_width=0, fill_color=C_HOT, fill_opacity=0.7
        ).move_to(barB_bg.get_left(), aligned_edge=LEFT))

        with self.voiceover(text=(
            "但在华为这类设备上，常见的是另一种情况：热控或调度把 dex2oat 限制到小核、压低频率，"
            "编译被严重拖慢，进度条慢慢地往前爬。"
        )) as tracker:
            self.play(FadeIn(barB_bg), FadeIn(labelB), FadeIn(barB))
            self.play(tB.animate.set_value(9.5), run_time=max(2.0, tracker.duration - 1.0), rate_func=linear)

        # boom / log 略微左移避开右侧拥挤
        boom = cn("✗ Fatal: exit(1)", size=26, color=C_HOT).next_to(v2p(9.5), UP, buff=1.2).shift(LEFT * 0.3)
        log_msg = code('"dex2oat did not finish after 570 seconds"', size=17, color=C_HOT).next_to(boom, DOWN, buff=0.15)

        with self.voiceover(text=(
            "一旦越过九分半，看门狗超时，直接 exit 1，日志里会打印 did not finish after 570 seconds。"
        )):
            self.play(Flash(v2p(9.5), color=C_HOT, flash_radius=0.8), FadeIn(boom, scale=1.3))
            self.play(Write(log_msg))

        tip = cn("关键：进程没真卡死，只是被限速到超时。先查 CPU/核/温度/cgroup，别只调大看门狗",
                 size=19, color=C_HL).to_edge(DOWN, buff=0.2)
        with self.voiceover(text=(
            "这里最关键、也最容易误判的一点是：进程其实没有真的卡死，只是被限速到超时。"
            "所以排查时要先看 CPU 占用、它运行在哪个核、温度，以及它所在的 cgroup，"
            "而不是简单地把看门狗时间调大——那只是治标。"
        )):
            self.play(Write(tip))

        self.play(FadeIn(footnote("WatchDog: dex2oat.cc:280 ｜ 9.5min: dex2oat.cc:344 ｜ Fatal->exit(1): dex2oat.cc:357")))
        self.wait(0.8)
