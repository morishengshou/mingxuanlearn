"""
config_policy 概念动画 1：多层配置查找原理

包含两个场景：
  - LayerLookupOne : GetOneCfgFile —— 高优先级优先，返回第一个命中
  - LayerLookupAll : GetCfgFiles  —— 收集所有层命中（低→高）

渲染（在本文件所在目录执行）：
  manim -pqh concept_layers.py LayerLookupOne
  manim -pqh concept_layers.py LayerLookupAll
"""

from manim import *

# 中文字体：Windows 用 "Microsoft YaHei"，macOS 用 "PingFang SC"，Linux 用 "Noto Sans CJK SC"
FONT = "Microsoft YaHei"

LAYER_COLORS = [GRAY_B, TEAL_C, BLUE_C, GREEN_C]
# 优先级低 → 高
LAYERS = ["/system", "/chipset", "/sys_prod", "/chip_prod"]
REL_PATH = "etc/telephony/config.json"
# 哪些层实际存在该文件（True = 存在）
EXISTS = [True, False, True, True]


def make_layer_box(name, color, exists):
    box = RoundedRectangle(width=6.6, height=0.85, corner_radius=0.12,
                           color=color, fill_color=color, fill_opacity=0.18)
    # 左：层目录名（等宽字体）
    label = Text(name, font="Consolas", font_size=24, color=WHITE)
    label.next_to(box.get_left(), RIGHT, buff=0.45)
    # 右：状态徽标（小圆点 + 文字），与层名分置两端，不再重叠
    dot = Dot(radius=0.08, color=(GREEN_B if exists else GREY_C))
    status = Text("有此文件" if exists else "无此文件",
                  font=FONT, font_size=20, color=(GREEN_B if exists else GREY_C))
    badge = VGroup(dot, status).arrange(RIGHT, buff=0.15)
    badge.next_to(box.get_right(), LEFT, buff=0.45)
    return VGroup(box, label, badge)


class LayerLookupOne(Scene):
    def construct(self):
        title = Text("GetOneCfgFile：高优先级优先，返回首个命中", font=FONT, font_size=30)
        title.to_edge(UP)
        self.play(Write(title))

        rel = Text(f'查询相对路径：  "{REL_PATH}"', font=FONT, font_size=24, color=YELLOW)
        rel.next_to(title, DOWN, buff=0.35)
        self.play(FadeIn(rel, shift=DOWN))

        boxes = VGroup(*[make_layer_box(LAYERS[i], LAYER_COLORS[i], EXISTS[i])
                         for i in range(len(LAYERS))])
        boxes.arrange(DOWN, buff=0.3).next_to(rel, DOWN, buff=0.5)
        self.play(LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.2))

        # 优先级标注
        low = Text("低优先级", font=FONT, font_size=18, color=GREY_B).next_to(boxes[0], LEFT, buff=0.4)
        high = Text("高优先级", font=FONT, font_size=18, color=GREEN_B).next_to(boxes[-1], LEFT, buff=0.4)
        arrow = Arrow(boxes[0].get_left() + LEFT * 0.9, boxes[-1].get_left() + LEFT * 0.9,
                      buff=0.1, color=WHITE, stroke_width=3)
        self.play(FadeIn(low), FadeIn(high), GrowArrow(arrow))
        self.wait(0.5)

        # 从高到低扫描指针
        scan = Text("扫描", font=FONT, font_size=18, color=ORANGE)
        for i in reversed(range(len(LAYERS))):
            highlight = SurroundingRectangle(boxes[i], color=ORANGE, buff=0.05)
            scan.next_to(boxes[i], RIGHT, buff=0.4)
            self.play(Create(highlight), FadeIn(scan), run_time=0.5)
            if EXISTS[i]:
                hit = SurroundingRectangle(boxes[i], color=GREEN, buff=0.05, stroke_width=6)
                self.play(Transform(highlight, hit))
                result = Text(f'返回：  {LAYERS[i]}/{REL_PATH}', font=FONT, font_size=22, color=GREEN_B)
                result.to_edge(DOWN, buff=0.5)
                self.play(Indicate(boxes[i], color=GREEN), Write(result))
                self.wait(2)
                break
            else:
                cross = Cross(boxes[i], stroke_color=RED, stroke_width=3, scale_factor=0.45)
                self.play(Create(cross), run_time=0.4)
                self.play(FadeOut(highlight), FadeOut(cross), FadeOut(scan), run_time=0.3)
        self.wait(1.5)


class LayerLookupAll(Scene):
    def construct(self):
        title = Text("GetCfgFiles：收集所有层命中（低→高优先级）", font=FONT, font_size=30)
        title.to_edge(UP)
        self.play(Write(title))

        boxes = VGroup(*[make_layer_box(LAYERS[i], LAYER_COLORS[i], EXISTS[i])
                         for i in range(len(LAYERS))])
        boxes.arrange(DOWN, buff=0.3).next_to(title, DOWN, buff=0.6)
        self.play(LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.2))
        self.wait(0.5)

        # 结果数组容器
        result_title = Text("CfgFiles->paths[]（低→高）", font=FONT, font_size=20, color=YELLOW)
        result_title.to_edge(DOWN, buff=1.6)
        slots = VGroup(*[Square(side_length=0.5, color=GREY_B) for _ in range(4)])
        slots.arrange(RIGHT, buff=0.15).next_to(result_title, DOWN, buff=0.25)
        self.play(Write(result_title), Create(slots))

        idx = 0
        for i in range(len(LAYERS)):  # 低 → 高
            highlight = SurroundingRectangle(boxes[i], color=ORANGE, buff=0.05)
            self.play(Create(highlight), run_time=0.4)
            if EXISTS[i]:
                dot = Dot(color=GREEN).move_to(slots[idx])
                tag = Text(LAYERS[i], font=FONT, font_size=12, color=GREEN_B).next_to(slots[idx], DOWN, buff=0.1)
                self.play(slots[idx].animate.set_stroke(GREEN),
                          FadeIn(dot), FadeIn(tag),
                          Transform(highlight, SurroundingRectangle(boxes[i], color=GREEN, buff=0.05)))
                idx += 1
            else:
                self.play(FadeOut(highlight), run_time=0.3)
                continue
            self.play(FadeOut(highlight), run_time=0.2)
        self.wait(2)
