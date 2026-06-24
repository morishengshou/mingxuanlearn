"""
config_policy 概念动画 2（核心）：CfgDir 结构体的内存原理

演示 GetCfgDirList() 如何：
  1. 一次性 strdup 出 realPolicyValue 缓冲区
  2. 原地将 ':' 改写为 '\\0'，把 paths[i] 指向同一块缓冲区内部
  3. 因此 paths[i] 不是独立分配，禁止单独 free
  4. FreeCfgDirList 只释放 realPolicyValue + 结构体本身

渲染：
  manim -pqh concept_cfgdir_memory.py CfgDirMemory
"""

from manim import *

FONT = "Microsoft YaHei"

POLICY = "/system:/chipset:/sys_prod:/chip_prod"
COLON_IDX = [7, 16, 26]          # ':' 在字符串中的位置
SEG_START = [0, 8, 17, 27]       # 各段起始字符下标
SEG_NAME = ["/system", "/chipset", "/sys_prod", "/chip_prod"]


class CfgDirMemory(Scene):
    def construct(self):
        title = Text("CfgDir 的内存模型：paths[] 指向同一块缓冲区", font=FONT, font_size=28)
        title.to_edge(UP)
        self.play(Write(title))

        # ---------- 1. 堆上的 realPolicyValue 缓冲区 ----------
        buf_text = Text(POLICY, font="Consolas", font_size=26)
        buf_text.move_to(UP * 1.4)
        buf_rect = SurroundingRectangle(buf_text, color=BLUE_C, buff=0.18, corner_radius=0.1)
        heap_tag = Text("堆内存：realPolicyValue（一次 strdup 分配）",
                        font=FONT, font_size=18, color=BLUE_B)
        heap_tag.next_to(buf_rect, UP, buff=0.2)

        self.play(Create(buf_rect), Write(buf_text), FadeIn(heap_tag))
        self.wait(0.5)

        # ---------- 2. CfgDir 结构体 ----------
        path_slots = VGroup()
        for i in range(4):
            slot = VGroup(
                Rectangle(width=1.7, height=0.55, color=GREY_B),
                Text(f"paths[{i}]", font="Consolas", font_size=16, color=WHITE),
            )
            slot[1].move_to(slot[0])
            path_slots.add(slot)
        rpv_slot = VGroup(
            Rectangle(width=1.7, height=0.55, color=PURPLE_B),
            Text("realPolicy", font="Consolas", font_size=14, color=PURPLE_A),
        )
        rpv_slot[1].move_to(rpv_slot[0])

        struct_body = VGroup(*path_slots, rpv_slot).arrange(DOWN, buff=0.12)
        struct_label = Text("struct CfgDir", font="Consolas", font_size=18, color=YELLOW)
        struct_box = SurroundingRectangle(struct_body, color=YELLOW, buff=0.18)
        struct_label.next_to(struct_box, UP, buff=0.12)
        struct_group = VGroup(struct_label, struct_box, struct_body)
        struct_group.to_edge(DOWN, buff=0.4).to_edge(LEFT, buff=0.7)

        self.play(Create(struct_box), Write(struct_label),
                  LaggedStart(*[FadeIn(s) for s in [*path_slots, rpv_slot]], lag_ratio=0.1))

        # realPolicyValue 指针 → 缓冲区
        rpv_arrow = Arrow(rpv_slot.get_right(), buf_rect.get_corner(DL) + RIGHT * 0.3,
                          buff=0.1, color=PURPLE_B, stroke_width=3)
        self.play(GrowArrow(rpv_arrow))
        self.wait(0.5)

        # ---------- 3. 原地切割：paths[i] = next; *next(':') = '\0' ----------
        explain = Text("解析：paths[i] 指向段首，再把 ':' 原地改写为 '\\0'",
                       font=FONT, font_size=20, color=ORANGE)
        explain.next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(explain))

        seg_arrows = VGroup()
        nuls = VGroup()
        for i in range(4):
            start_glyph = buf_text[SEG_START[i]]
            arrow = Arrow(path_slots[i].get_right(),
                          start_glyph.get_bottom() + DOWN * 0.05,
                          buff=0.1, color=path_slots[i][0].get_color(), stroke_width=2.5)
            self.play(GrowArrow(arrow), path_slots[i][0].animate.set_stroke(GREEN),
                      run_time=0.5)
            seg_arrows.add(arrow)
            # 把该段后的 ':' 改写为 '\0'
            if i < len(COLON_IDX):
                colon = buf_text[COLON_IDX[i]]
                nul = Text("\\0", font="Consolas", font_size=22, color=RED).move_to(colon)
                self.play(FadeOut(colon, scale=0.5), FadeIn(nul, scale=1.5), run_time=0.4)
                nuls.add(nul)
        self.wait(1)

        # ---------- 4. 结论：单块内存，禁止单独 free ----------
        bracket = Brace(buf_rect, DOWN, color=BLUE_B)
        bracket_txt = Text("4 个子串共用这一块内存", font=FONT, font_size=20, color=BLUE_B)
        bracket_txt.next_to(bracket, DOWN, buff=0.15)
        self.play(GrowFromCenter(bracket), FadeIn(bracket_txt))
        self.wait(0.5)

        warn = VGroup(
            Text("free(dirs->paths[0]);", font="Consolas", font_size=22, color=RED),
            Text("禁止！paths[i] 非独立分配，会堆损坏", font=FONT, font_size=18, color=RED),
        ).arrange(DOWN, buff=0.15).to_edge(RIGHT, buff=0.6).shift(DOWN * 0.5)
        warn_cross = Cross(warn[0], stroke_color=RED, stroke_width=4, scale_factor=0.6)
        self.play(Write(warn[0]))
        self.play(Create(warn_cross), FadeIn(warn[1]))
        self.wait(1.5)

        # ---------- 5. 正确释放 ----------
        self.play(FadeOut(warn), FadeOut(warn_cross), FadeOut(explain))
        free_ok = Text("FreeCfgDirList(dirs)：只 free(realPolicyValue) + free(结构体)",
                       font=FONT, font_size=20, color=GREEN_B)
        free_ok.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.6).scale(0.85)
        self.play(Write(free_ok))
        self.play(Indicate(buf_rect, color=GREEN), Indicate(struct_box, color=GREEN))
        self.play(FadeOut(VGroup(buf_rect, buf_text, nuls, heap_tag, bracket, bracket_txt,
                                 seg_arrows, rpv_arrow)),
                  run_time=1)
        self.wait(1.5)
