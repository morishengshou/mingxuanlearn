"""
config_policy 典型内存场景动画：CfgDir 原地切割单块缓冲区

逐字节复现 GetCfgDirList() 的核心循环（config_policy_utils.c:533-546）：

    char *next = res->realPolicyValue;
    for (i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        res->paths[i] = next;        // ① 记录段首
        next = strchr(next, ':');    // ② 找下一个 ':'
        if (next == NULL) break;     // ③ 没有分隔符则结束
        *next = 0;                   // ④ 把 ':' 原地改写成 '\\0'
        next += 1;                   // ⑤ 跳过分隔符
    }

强调两件事：
  1. ':' 被**原地**改写为 '\\0'  —— 不另外分配内存
  2. 每个 paths[i] 是指向**同一块** realPolicyValue 缓冲区内部的指针

渲染：
  manim -pql scenario_cfgdir_memory.py CfgDirMemoryScenario   # 调试预览
  manim -qh  scenario_cfgdir_memory.py CfgDirMemoryScenario   # 交付
"""

from manim import *

FONT = "Microsoft YaHei"
MONO = "Consolas"

POLICY = "/system:/chipset:/sys_prod:/chip_prod"
COLON_IDX = [7, 16, 26]            # ':' 所在下标
SEG_START = [0, 8, 17, 27]         # 各段段首下标
SEG_OFF = ["buf+0", "buf+8", "buf+17", "buf+27"]   # 段首相对偏移（指针值示意）
PCOL = [GREY_B, TEAL_C, BLUE_C, GREEN_C]

CW = 0.315                         # 单字节单元宽度（37 字节需横向收窄以留出左侧标注）


class CfgDirMemoryScenario(Scene):
    def construct(self):
        title = Text("典型内存场景：CfgDir 原地切割同一块缓冲区", font=FONT, font_size=30)
        title.to_edge(UP, buff=0.28)
        self.add(title)
        self.title = title

        # 当前 C 语句（逐步更新）；含中文注释，故用 CJK 字体避免缺字方块
        self.stmt = Text("", font=FONT, font_size=22, color=YELLOW).next_to(title, DOWN, buff=0.22)
        self.add(self.stmt)

        self.build_buffer()
        self.build_struct()
        self.run_loop()
        self.conclude()

    # ---------- 顶部当前语句 ----------
    def set_stmt(self, text, color=YELLOW):
        new = Text(text, font=FONT, font_size=22, color=color).next_to(self.title, DOWN, buff=0.22)
        if len(self.stmt.text) == 0:
            self.play(FadeIn(new), run_time=0.4)
            self.remove(self.stmt)
            self.stmt = new
            self.add(self.stmt)
        else:
            self.play(Transform(self.stmt, new), run_time=0.45)

    # ---------- 1. 堆上的 realPolicyValue 字节缓冲 ----------
    def build_buffer(self):
        cells = VGroup()
        for ch in POLICY:
            rect = Rectangle(width=CW, height=0.55, stroke_width=1.4, stroke_color=GREY_C)
            glyph = Text(ch, font=MONO, font_size=16, color=WHITE)
            glyph.move_to(rect)
            cells.add(VGroup(rect, glyph))
        cells.arrange(RIGHT, buff=0).move_to(UP * 1.05)
        # 把 ':' 单元先标橙，突出"待改写的分隔符"
        for c in COLON_IDX:
            cells[c][0].set_fill(ORANGE, opacity=0.25)
            cells[c][1].set_color(ORANGE)
        self.cells = cells

        heap_tag = Text("堆内存 realPolicyValue（一次 strdup，连续 1 块）",
                        font=FONT, font_size=18, color=BLUE_B)
        heap_tag.next_to(cells, UP, buff=0.22)
        self.heap_tag = heap_tag

        self.play(FadeIn(heap_tag), LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.02),
                  run_time=1.2)

        # next 指针（在缓冲下方移动的上箭头）
        self.next_ptr = self.make_cursor("next", YELLOW)
        self.next_ptr.next_to(cells[0], DOWN, buff=0.12)
        self.play(FadeIn(self.next_ptr, shift=UP * 0.2))

    def make_cursor(self, label, color):
        tri = Triangle(color=color, fill_opacity=1).scale(0.12).rotate(PI)  # 指向上
        txt = Text(label, font=MONO, font_size=16, color=color)
        txt.next_to(tri, DOWN, buff=0.06)
        return VGroup(tri, txt)

    def cursor_to(self, idx, run_time=0.5):
        target = self.cells[idx][0].get_bottom() + DOWN * 0.12
        # 仅平移 x，保持在缓冲正下方
        self.play(self.next_ptr.animate.next_to(self.cells[idx], DOWN, buff=0.12), run_time=run_time)

    # ---------- 2. struct CfgDir：paths[] + realPolicyValue ----------
    def build_struct(self):
        slots = VGroup()
        for i in range(4):
            rect = Rectangle(width=1.18, height=0.92, color=PCOL[i], stroke_width=2)
            name = Text(f"paths[{i}]", font=MONO, font_size=14, color=PCOL[i])
            val = Text("?", font=MONO, font_size=15, color=GREY_B)
            name.move_to(rect.get_top() + DOWN * 0.22)
            val.move_to(rect.get_bottom() + UP * 0.24)
            slot = VGroup(rect, name, val)
            # 段首正下方，便于竖直指针
            slot.move_to([self.cells[SEG_START[i]][0].get_x(), -2.25, 0])
            slots.add(slot)
        self.slots = slots

        struct_tag = Text("struct CfgDir 的 paths[]（各自只是指针，指向上方缓冲内部）",
                          font=FONT, font_size=18, color=YELLOW)
        struct_tag.to_edge(DOWN, buff=0.18)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.2) for s in slots], lag_ratio=0.1),
                  FadeIn(struct_tag), run_time=1.0)
        self.struct_tag = struct_tag

        # realPolicyValue 指针（指向缓冲起点）；左侧空间窄，标签两行排布避免出界
        rpv = VGroup(
            Text("realPolicy", font=MONO, font_size=13, color=PURPLE_A),
            Text("Value", font=MONO, font_size=13, color=PURPLE_A),
        ).arrange(DOWN, buff=0.04, aligned_edge=RIGHT)
        rpv.next_to(self.cells, LEFT, buff=0.18)
        rpv_arrow = Arrow(rpv.get_right(), self.cells[0][0].get_left(),
                          buff=0.06, color=PURPLE_B, stroke_width=3)
        self.play(FadeIn(rpv), GrowArrow(rpv_arrow))
        self.rpv = VGroup(rpv, rpv_arrow)

    # ---------- 3. 主循环逐步切割 ----------
    def run_loop(self):
        self.path_arrows = VGroup()
        self.nuls = VGroup()

        for i in range(4):
            seg = SEG_START[i]

            # ① paths[i] = next
            self.set_stmt(f"res->paths[{i}] = next;   // 记录段首", color=PCOL[i])
            arrow = Arrow(self.slots[i][0].get_top(),
                          self.cells[seg][0].get_bottom(),
                          buff=0.08, color=PCOL[i], stroke_width=3)
            new_val = Text(SEG_OFF[i], font=MONO, font_size=14, color=PCOL[i])
            new_val.move_to(self.slots[i][2])
            self.play(GrowArrow(arrow),
                      Transform(self.slots[i][2], new_val),
                      self.cells[seg][0].animate.set_stroke(PCOL[i], width=2.5),
                      run_time=0.6)
            self.path_arrows.add(arrow)

            # ② next = strchr(next, ':')
            if i < len(COLON_IDX):
                col = COLON_IDX[i]
                self.set_stmt("next = strchr(next, ':');   // 向后找 ':'", color=ORANGE)
                scan = SurroundingRectangle(self.cells[seg], color=ORANGE, buff=0.0, stroke_width=3)
                self.play(Create(scan), run_time=0.25)
                self.play(scan.animate.move_to(self.cells[col]), run_time=0.55)
                self.cursor_to(col, run_time=0.45)
                self.play(Indicate(self.cells[col][1], color=ORANGE, scale_factor=1.4), run_time=0.4)

                # ③ if (next == NULL) break;  —— 此处找到了，不 break
                self.set_stmt("if (next == NULL) break;   // 找到了，继续", color=GREY_A)
                self.wait(0.2)

                # ④ *next = 0;  —— 原地把 ':' 改写成 '\0'
                self.set_stmt("*next = 0;   // ':' 原地改写为 '\\0'", color=RED)
                nul = Text("\\0", font=MONO, font_size=18, color=RED).move_to(self.cells[col][1])
                self.play(
                    FadeOut(self.cells[col][1], scale=0.4),
                    self.cells[col][0].animate.set_fill(RED, opacity=0.35).set_stroke(RED),
                    FadeIn(nul, scale=1.6), run_time=0.55)
                self.nuls.add(nul)
                self.play(FadeOut(scan), run_time=0.2)

                # ⑤ next += 1;  —— 跳过分隔符，指向下一段段首
                self.set_stmt("next += 1;   // 跳过分隔符，指向下一段", color=YELLOW)
                self.cursor_to(SEG_START[i + 1], run_time=0.5)
            else:
                # i == 3：最后一段，strchr 返回 NULL → break
                self.set_stmt("next = strchr(next, ':');  // 末段无 ':' → NULL", color=ORANGE)
                self.wait(0.3)
                self.set_stmt("if (next == NULL) break;   // 循环结束", color=GREEN_B)
                self.play(Indicate(self.next_ptr, color=GREEN), run_time=0.5)
            self.wait(0.2)

    # ---------- 4. 结论 ----------
    def conclude(self):
        self.set_stmt("结果：1 块缓冲被 3 个 '\\0' 切成 4 段，paths[] 全指向它内部", color=GREEN_B)

        brace = Brace(self.cells, DOWN, color=BLUE_B).shift(DOWN * 0.55)
        btxt = Text("始终是同一块连续内存", font=FONT, font_size=18, color=BLUE_B)
        btxt.next_to(brace, DOWN, buff=0.12)
        self.play(FadeOut(self.next_ptr), GrowFromCenter(brace), FadeIn(btxt))
        self.wait(0.4)

        # 错误用法：禁止单独 free 某个 paths[i]
        warn = VGroup(
            Text("free(dirs->paths[1]);", font=MONO, font_size=20, color=RED),
            Text("禁止！它不是独立分配，会堆损坏", font=FONT, font_size=17, color=RED),
        ).arrange(DOWN, buff=0.12).to_edge(RIGHT, buff=0.5).shift(UP * 0.2)
        cross = Cross(warn[0], stroke_color=RED, stroke_width=4, scale_factor=0.62)
        self.play(Write(warn[0]))
        self.play(Create(cross), FadeIn(warn[1]))
        self.wait(1.0)

        # 正确释放：只 free realPolicyValue + 结构体
        self.set_stmt("FreeCfgDirList：只 free(realPolicyValue) + free(结构体)", color=GREEN_B)
        self.play(FadeOut(warn), FadeOut(cross))
        self.play(Indicate(VGroup(*[c[0] for c in self.cells]), color=GREEN, scale_factor=1.04),
                  run_time=0.8)
        self.play(
            FadeOut(self.path_arrows),
            FadeOut(self.cells), FadeOut(self.nuls),
            FadeOut(self.heap_tag), FadeOut(brace), FadeOut(btxt),
            FadeOut(self.rpv),
            run_time=1.0)
        ok = Text("一次分配、一次释放，paths[] 随结构体一同回收", font=FONT, font_size=20, color=GREEN_B)
        ok.move_to(UP * 0.6)
        self.play(FadeIn(ok, shift=UP * 0.2), Indicate(self.slots, color=GREEN))
        self.wait(2.0)
