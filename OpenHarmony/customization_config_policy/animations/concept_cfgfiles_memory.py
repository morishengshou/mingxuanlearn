"""
config_policy 概念动画 3：CfgFiles 结构体的内存原理（与 CfgDir 对比）

演示 GetCfgFiles() 返回的 CfgFiles：
  - 每个 paths[i] 都是独立 strdup(buf) 分配的内存块
  - 因此可以逐个 free，也可用 FreeCfgFiles 统一释放
  - 与 CfgDir（共用一块缓冲）形成对比

渲染：
  manim -pqh concept_cfgfiles_memory.py CfgFilesMemory
"""

from manim import *

FONT = "Microsoft YaHei"

FOUND = [
    "/system/etc/config.xml",
    "/sys_prod/etc/config.xml",
    "/chip_prod/etc/config.xml",
]


class CfgFilesMemory(Scene):
    def construct(self):
        title = Text("CfgFiles 的内存模型：每个 paths[i] 独立分配", font=FONT, font_size=28)
        title.to_edge(UP)
        self.play(Write(title))

        # ---------- struct CfgFiles ----------
        path_slots = VGroup()
        for i in range(3):
            slot = VGroup(
                Rectangle(width=1.7, height=0.6, color=GREY_B),
                Text(f"paths[{i}]", font="Consolas", font_size=16, color=WHITE),
            )
            slot[1].move_to(slot[0])
            path_slots.add(slot)
        path_slots.arrange(DOWN, buff=0.25)
        struct_box = SurroundingRectangle(path_slots, color=YELLOW, buff=0.2)
        struct_label = Text("struct CfgFiles", font="Consolas", font_size=18, color=YELLOW)
        struct_label.next_to(struct_box, UP, buff=0.12)
        struct_group = VGroup(struct_label, struct_box, path_slots)
        struct_group.to_edge(LEFT, buff=1.0).shift(DOWN * 0.3)
        self.play(Create(struct_box), Write(struct_label),
                  LaggedStart(*[FadeIn(s) for s in path_slots], lag_ratio=0.15))

        # ---------- 每个 paths[i] 各自的堆块 ----------
        heap_blocks = VGroup()
        arrows = VGroup()
        for i in range(3):
            txt = Text(FOUND[i], font="Consolas", font_size=18)
            rect = SurroundingRectangle(txt, color=GREEN_C, buff=0.15, corner_radius=0.08)
            block = VGroup(rect, txt)
            heap_blocks.add(block)
        heap_blocks.arrange(DOWN, buff=0.4).to_edge(RIGHT, buff=0.8).shift(DOWN * 0.3)

        tag = Text("堆内存：每块由独立 strdup(buf) 分配", font=FONT, font_size=18, color=GREEN_B)
        tag.next_to(heap_blocks, UP, buff=0.3)
        self.play(FadeIn(tag))

        for i in range(3):
            arrow = Arrow(path_slots[i].get_right(), heap_blocks[i].get_left(),
                          buff=0.15, color=GREEN_C, stroke_width=3)
            self.play(Create(heap_blocks[i]), GrowArrow(arrow),
                      path_slots[i][0].animate.set_stroke(GREEN), run_time=0.6)
            arrows.add(arrow)
        self.wait(1)

        # ---------- 对比说明 ----------
        note = VGroup(
            Text("对比 CfgDir：", font=FONT, font_size=20, color=YELLOW),
            Text("• CfgDir   → paths[] 共用一块缓冲，禁止单独 free", font=FONT, font_size=17, color=GREY_A),
            Text("• CfgFiles → paths[] 各自独立，可逐个 free", font=FONT, font_size=17, color=GREY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        note.to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note, shift=UP))
        self.wait(1.5)

        # ---------- FreeCfgFiles：逐块释放 ----------
        free_txt = Text("FreeCfgFiles(files)：逐个 free(paths[i]) + free(结构体)",
                        font=FONT, font_size=20, color=RED)
        free_txt.move_to(note)
        self.play(FadeOut(note), FadeIn(free_txt))
        for i in range(3):
            self.play(FadeOut(heap_blocks[i], scale=0.3), FadeOut(arrows[i]),
                      path_slots[i][0].animate.set_stroke(GREY_C), run_time=0.5)
        self.play(FadeOut(struct_group), run_time=0.6)
        self.wait(1.5)
