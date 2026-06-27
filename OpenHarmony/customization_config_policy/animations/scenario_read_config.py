"""
config_policy 典型使用场景动画：业务读取并合并多层配置文件

完整呈现一次 GetCfgFiles 调用的全过程：
  业务发起调用 -> 内部 GetCfgDirList 建 CfgDir -> 逐层 access 查找
  -> 命中项 strdup 进 CfgFiles -> 内部 FreeCfgDirList 释放临时 CfgDir
  -> 返回业务遍历 paths[] -> 业务 FreeCfgFiles 释放（无泄漏）

渲染：
  manim -qh scenario_read_config.py ReadConfigScenario
"""

from manim import *

FONT = "Microsoft YaHei"
MONO = "Consolas"

REL = "etc/telephony/config.json"
LAYERS = ["/system", "/chipset", "/sys_prod", "/chip_prod"]
LCOL = [GREY_B, TEAL_C, BLUE_C, GREEN_C]
EXISTS = [True, False, True, False]   # 命中：/system 与 /sys_prod


class ReadConfigScenario(Scene):
    def construct(self):
        self.title = Text("典型场景：业务读取并合并多层配置文件", font=FONT, font_size=30).to_edge(UP, buff=0.3)
        self.play(Write(self.title))
        self.caption = Text("", font=FONT, font_size=22, color=YELLOW).next_to(self.title, DOWN, buff=0.18)
        self.add(self.caption)

        self.phase_call()
        self.phase_getcfgdir()
        self.phase_search()
        self.phase_free_cfgdir()
        self.phase_return_iterate()
        self.phase_free_cfgfiles()
        self.phase_summary()

    # 更新顶部步骤说明
    def set_caption(self, text):
        new = Text(text, font=FONT, font_size=22, color=YELLOW).next_to(self.title, DOWN, buff=0.18)
        self.play(Transform(self.caption, new), run_time=0.5)

    # ---------- 阶段1：业务发起调用 ----------
    def phase_call(self):
        self.set_caption("第 1 步：业务需要一个配置文件，发起调用")

        need = Text(f'业务需求：读取 "{REL}"', font=FONT, font_size=24, color=WHITE)
        need.move_to(UP * 1.2)
        self.play(FadeIn(need, shift=DOWN))

        code = VGroup(
            Text('CfgFiles *files =', font=MONO, font_size=26, color=GREY_A),
            Text(f'    GetCfgFiles("{REL}");', font=MONO, font_size=26, color=GREEN_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(need, DOWN, buff=0.6)
        self.play(Write(code))
        self.play(Indicate(code[1], color=GREEN))
        self.wait(0.8)
        self.play(FadeOut(need), FadeOut(code))

    # ---------- 阶段2：内部 GetCfgDirList 建 CfgDir ----------
    def phase_getcfgdir(self):
        self.set_caption("第 2 步：GetCfgFiles 内部调用 GetCfgDirList()，构建临时 CfgDir")

        # CfgDir 结构（含 4 个层路径）
        rows = VGroup()
        for i in range(4):
            cell = VGroup(
                Rectangle(width=2.4, height=0.5, color=LCOL[i]),
                Text(f"paths[{i}]", font=MONO, font_size=14, color=GREY_A),
                Text(LAYERS[i], font=MONO, font_size=16, color=WHITE),
            )
            cell[1].move_to(cell[0].get_left() + RIGHT * 0.55)
            cell[2].move_to(cell[0].get_right() + LEFT * 0.75)
            rows.add(cell)
        rows.arrange(DOWN, buff=0.12)
        title = Text("CfgDir（临时，记录所有配置层）", font=FONT, font_size=20, color=PURPLE_B)
        box = SurroundingRectangle(rows, color=PURPLE_B, buff=0.2)
        title.next_to(box, UP, buff=0.15)
        self.cfgdir = VGroup(title, box, rows).move_to(LEFT * 3.2 + DOWN * 0.6)

        self.play(Create(box), Write(title))
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in rows], lag_ratio=0.15))
        note = Text("malloc + 读取 const.cust.config_dir_layer", font=FONT, font_size=16, color=GREY_B)
        note.next_to(box, DOWN, buff=0.2)
        self.play(FadeIn(note))
        self.cfgdir_note = note
        self.wait(0.8)

    # ---------- 阶段3：逐层查找 + 命中 strdup 进 CfgFiles ----------
    def phase_search(self):
        self.set_caption("第 3 步：逐层拼接 relPath，access() 检查；命中项 strdup 存入 CfgFiles")

        # 右侧：CfgFiles 结果容器
        slots = VGroup()
        for i in range(4):
            s = VGroup(
                Rectangle(width=5.0, height=0.5, color=GREY_D),
                Text(f"paths[{i}]", font=MONO, font_size=13, color=GREY_B),
            )
            s[1].next_to(s[0].get_left(), RIGHT, buff=0.15)
            slots.add(s)
        slots.arrange(DOWN, buff=0.12)
        ftitle = Text("CfgFiles（返回给业务）", font=FONT, font_size=20, color=YELLOW)
        fbox = SurroundingRectangle(slots, color=YELLOW, buff=0.2)
        ftitle.next_to(fbox, UP, buff=0.15)
        self.cfgfiles = VGroup(ftitle, fbox, slots).move_to(RIGHT * 3.4 + DOWN * 0.6)
        self.cfgfiles_slots = slots
        self.play(Create(fbox), Write(ftitle), *[FadeIn(s) for s in slots])

        idx = 0
        for i in range(4):
            layer_cell = self.cfgdir[2][i]
            hl = SurroundingRectangle(layer_cell, color=ORANGE, buff=0.04)
            probe = Text(f"access: {LAYERS[i]}/{REL}", font=MONO, font_size=15,
                         color=ORANGE).to_edge(DOWN, buff=0.5)
            self.play(Create(hl), FadeIn(probe), run_time=0.5)
            if EXISTS[i]:
                # 命中：strdup 进 CfgFiles 槽位，飞行动画（缩短显示，置于 paths[i] 标签右侧）
                short = f"{LAYERS[i]}/.../config.json"
                target = self.cfgfiles_slots[idx]
                dst = Text(short, font=MONO, font_size=15, color=GREEN_B)
                dst.next_to(target[1], RIGHT, buff=0.25)
                flying = Text(short, font=MONO, font_size=15, color=GREEN_B).move_to(layer_cell)
                self.play(
                    Transform(hl, SurroundingRectangle(layer_cell, color=GREEN, buff=0.04)),
                    FadeIn(flying, scale=0.8), run_time=0.4)
                strtag = Text("strdup ->", font=MONO, font_size=14, color=GREEN_B)
                strtag.next_to(probe, RIGHT, buff=0.4)
                self.play(FadeIn(strtag),
                          flying.animate.move_to(dst.get_center()),
                          target[0].animate.set_stroke(GREEN), run_time=0.7)
                self.remove(flying)
                target.add(dst)   # 作为槽位子对象，后续随 CfgFiles 整体移动
                idx += 1
                self.play(FadeOut(hl), FadeOut(probe), FadeOut(strtag), run_time=0.25)
            else:
                miss = Text("不存在，跳过", font=FONT, font_size=15, color=GREY_C).next_to(probe, RIGHT, buff=0.3)
                self.play(FadeIn(miss), run_time=0.3)
                self.play(FadeOut(hl), FadeOut(probe), FadeOut(miss), run_time=0.3)
        self.wait(0.6)

    # ---------- 阶段4：内部释放临时 CfgDir ----------
    def phase_free_cfgdir(self):
        self.set_caption("第 4 步：GetCfgFiles 返回前，内部 FreeCfgDirList() 释放临时 CfgDir")
        free = Text("FreeCfgDirList(dirs)", font=MONO, font_size=22, color=RED)
        free.next_to(self.cfgdir, DOWN, buff=0.2)
        self.play(FadeOut(self.cfgdir_note), Write(free))
        self.play(Indicate(self.cfgdir[1], color=RED))
        self.play(FadeOut(self.cfgdir, shift=LEFT * 0.4), FadeOut(free), run_time=0.8)
        gone = Text("临时 CfgDir 已释放（业务无需关心）", font=FONT, font_size=18, color=GREY_B)
        gone.move_to(LEFT * 3.2 + DOWN * 0.6)
        self.play(FadeIn(gone))
        self.cfgdir_gone = gone
        self.wait(0.6)

    # ---------- 阶段5：返回业务并遍历 ----------
    def phase_return_iterate(self):
        self.set_caption("第 5 步：CfgFiles 返回业务；按 低→高 优先级遍历并合并")
        self.play(FadeOut(self.cfgdir_gone))
        # 把 CfgFiles 移到中间偏左，右侧放业务遍历
        self.play(self.cfgfiles.animate.move_to(LEFT * 3.4 + DOWN * 0.4))

        code = VGroup(
            Text("for (i=0; i<MAX; i++)", font=MONO, font_size=20, color=GREY_A),
            Text("  if (files->paths[i])", font=MONO, font_size=20, color=GREY_A),
            Text("    load(files->paths[i]);", font=MONO, font_size=20, color=GREEN_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).move_to(RIGHT * 3.2 + UP * 0.3)
        self.play(Write(code))

        merge = Text("低优先级先加载，高优先级覆盖", font=FONT, font_size=18, color=BLUE_B)
        merge.next_to(code, DOWN, buff=0.4)
        self.play(FadeIn(merge))
        # 依次点亮已命中的两个槽位
        for i in (0, 1):
            self.play(Indicate(self.cfgfiles_slots[i][0], color=GREEN), run_time=0.6)
        self.wait(0.6)
        self.iter_code = code
        self.iter_merge = merge

    # ---------- 阶段6：释放 CfgFiles ----------
    def phase_free_cfgfiles(self):
        self.set_caption("第 6 步：业务用完后 FreeCfgFiles()，逐个 free 每个 strdup + 结构体")
        self.play(FadeOut(self.iter_code), FadeOut(self.iter_merge))
        free = Text("FreeCfgFiles(files);", font=MONO, font_size=24, color=RED)
        free.move_to(RIGHT * 3.2)
        self.play(Write(free))
        # 逐个释放命中的槽位
        for i in (0, 1):
            self.play(Indicate(self.cfgfiles_slots[i][0], color=RED), run_time=0.4)
        self.play(FadeOut(self.cfgfiles, shift=DOWN * 0.3), FadeOut(free), run_time=0.9)
        self.wait(0.4)

    # ---------- 阶段7：总结 ----------
    def phase_summary(self):
        self.set_caption("完成：一次调用，两个结构体各司其职、各自释放，无内存泄漏")
        lines = VGroup(
            Text("GetCfgFiles  ——  对外一次调用", font=FONT, font_size=22, color=WHITE),
            Text("CfgDir   : 内部临时使用，GetCfgFiles 内部 FreeCfgDirList 释放", font=FONT, font_size=20, color=PURPLE_B),
            Text("CfgFiles : 返回业务，业务用完 FreeCfgFiles 释放", font=FONT, font_size=20, color=YELLOW),
            Text("规则：谁拿到、谁负责释放；CfgDir 的 paths[] 禁止单独 free", font=FONT, font_size=20, color=GREEN_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to(DOWN * 0.3)
        self.play(LaggedStart(*[FadeIn(l, shift=UP * 0.2) for l in lines], lag_ratio=0.3))
        self.wait(2.5)
