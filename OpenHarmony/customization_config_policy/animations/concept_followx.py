"""
config_policy 概念动画 4：Follow-X 运营商差异化路径

演示 followMode 如何在标准层路径中插入运营商子目录 etc/carrier/<opkey>/

渲染：
  manim -pqh concept_followx.py FollowXLookup
"""

from manim import *

FONT = "Microsoft YaHei"


class FollowXLookup(Scene):
    def construct(self):
        title = Text("Follow-X：在层路径中插入运营商子目录", font=FONT, font_size=30)
        title.to_edge(UP)
        self.play(Write(title))

        # 输入条件
        cond = VGroup(
            Text('relPath  = "etc/config.xml"', font="Consolas", font_size=22, color=YELLOW),
            Text('followMode = SIM_DEFAULT (10)', font="Consolas", font_size=22, color=ORANGE),
            Text('opkey(默认卡) = 46060', font="Consolas", font_size=22, color=GREEN_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        cond.next_to(title, DOWN, buff=0.5)
        self.play(LaggedStart(*[FadeIn(c, shift=RIGHT) for c in cond], lag_ratio=0.3))
        self.wait(0.8)

        layer = Text("/sys_prod", font="Consolas", font_size=24, color=BLUE_B)
        layer.next_to(cond, DOWN, buff=0.7).to_edge(LEFT, buff=1.2)

        # 标准路径
        std_label = Text("标准路径：", font=FONT, font_size=20, color=GREY_A)
        std_path = Text("/sys_prod/etc/config.xml", font="Consolas", font_size=22, color=GREY_B)
        std = VGroup(std_label, std_path).arrange(RIGHT, buff=0.2)
        std.next_to(layer, DOWN, buff=0.6).to_edge(LEFT, buff=1.2)
        self.play(FadeIn(layer), Write(std))
        self.wait(0.6)

        # Follow-X 插入运营商段
        fx_label = Text("Follow-X：", font=FONT, font_size=20, color=GREEN_B)
        p1 = Text("/sys_prod/", font="Consolas", font_size=22, color=BLUE_B)
        carrier = Text("etc/carrier/46060/", font="Consolas", font_size=22, color=RED)
        p2 = Text("etc/config.xml", font="Consolas", font_size=22, color=GREY_B)
        fx_path = VGroup(p1, carrier, p2).arrange(RIGHT, buff=0.05)
        fx = VGroup(fx_label, fx_path).arrange(RIGHT, buff=0.2)
        fx.next_to(std, DOWN, buff=0.7).to_edge(LEFT, buff=1.2)

        self.play(FadeIn(fx_label), Write(p1), Write(p2))
        # 高亮插入点
        insert_arrow = Arrow(carrier.get_top() + UP * 0.6, carrier.get_top(),
                             buff=0.1, color=RED)
        insert_tag = Text("插入运营商段", font=FONT, font_size=16, color=RED)
        insert_tag.next_to(insert_arrow, UP, buff=0.1)
        self.play(GrowArrow(insert_arrow), FadeIn(insert_tag),
                  Write(carrier))
        self.play(Indicate(carrier, color=RED))
        self.wait(0.8)

        # 优先命中 Follow-X 路径
        result = Text("优先返回 Follow-X 路径（若存在），否则回退标准路径",
                      font=FONT, font_size=20, color=GREEN_B)
        result.to_edge(DOWN, buff=0.5)
        hit = SurroundingRectangle(fx_path, color=GREEN, buff=0.12)
        self.play(Create(hit), Write(result))
        self.wait(2)
