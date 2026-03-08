<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  <node TEXT="LeetCode Stream 极简背诵版" ID="LC_ROOT">
    <node TEXT="1. 核心定位" POSITION="left" ID="LC_1">
      <node TEXT="前处理、后处理适合用 Stream" ID="LC_1_1"/>
      <node TEXT="核心算法流程更适合 for" ID="LC_1_2"/>
    </node>

    <node TEXT="2. 高频技巧" POSITION="right" ID="LC_2">
      <node TEXT="去重排序：distinct sorted" ID="LC_2_1"/>
      <node TEXT="统计：sum count max min" ID="LC_2_2"/>
      <node TEXT="收集：toList toSet toMap" ID="LC_2_3"/>
      <node TEXT="词频：groupingBy + counting" ID="LC_2_4"/>
      <node TEXT="打平：flatMap" ID="LC_2_5"/>
      <node TEXT="判断：anyMatch allMatch noneMatch" ID="LC_2_6"/>
      <node TEXT="索引：IntStream.range" ID="LC_2_7"/>
    </node>

    <node TEXT="3. 不适合场景" POSITION="left" ID="LC_3">
      <node TEXT="双指针" ID="LC_3_1"/>
      <node TEXT="滑动窗口" ID="LC_3_2"/>
      <node TEXT="动态规划" ID="LC_3_3"/>
      <node TEXT="回溯" ID="LC_3_4"/>
      <node TEXT="DFS BFS 图搜索" ID="LC_3_5"/>
      <node TEXT="复杂下标控制" ID="LC_3_6"/>
    </node>

    <node TEXT="4. 常见坑" POSITION="right" ID="LC_4">
      <node TEXT="toMap 重复 key 报错" ID="LC_4_1"/>
      <node TEXT="IntStream 收集前常要 boxed" ID="LC_4_2"/>
      <node TEXT="toList 可能不可变" ID="LC_4_3"/>
      <node TEXT="不要为了用 Stream 而用 Stream" ID="LC_4_4"/>
    </node>

    <node TEXT="5. 背诵口诀" POSITION="left" ID="LC_5">
      <node TEXT="去重、排序、统计、分组、打平、判断" ID="LC_5_1"/>
      <node TEXT="前后处理用 Stream，核心循环用 for" ID="LC_5_2"/>
    </node>
  </node>
</map>