<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  <node TEXT="Java Stream API 极简背诵版" ID="JS_ROOT">
    <node TEXT="1. 核心思想" POSITION="left" ID="JS_1">
      <node TEXT="声明式：写做什么" ID="JS_1_1"/>
      <node TEXT="内部迭代：框架负责遍历" ID="JS_1_2"/>
      <node TEXT="惰性求值：无终止操作不执行" ID="JS_1_3"/>
      <node TEXT="一次性消费：不能重复用" ID="JS_1_4"/>
      <node TEXT="少副作用：少改外部变量" ID="JS_1_5"/>
    </node>

    <node TEXT="2. 基本结构" POSITION="right" ID="JS_2">
      <node TEXT="数据源" ID="JS_2_1"/>
      <node TEXT="中间操作：filter map flatMap distinct sorted limit" ID="JS_2_2"/>
      <node TEXT="终止操作：collect count sum max min findFirst match" ID="JS_2_3"/>
      <node TEXT="基本类型流：IntStream LongStream DoubleStream" ID="JS_2_4"/>
    </node>

    <node TEXT="3. 常用场景" POSITION="left" ID="JS_3">
      <node TEXT="过滤 + 转换 + 收集" ID="JS_3_1"/>
      <node TEXT="统计：和、个数、最值" ID="JS_3_2"/>
      <node TEXT="去重 + 排序" ID="JS_3_3"/>
      <node TEXT="分组、词频、聚合" ID="JS_3_4"/>
    </node>

    <node TEXT="4. 常见坑" POSITION="right" ID="JS_4">
      <node TEXT="忘记终止操作" ID="JS_4_1"/>
      <node TEXT="toMap 重复 key 报错" ID="JS_4_2"/>
      <node TEXT="基本类型转集合前常要 boxed" ID="JS_4_3"/>
      <node TEXT="toList 结果可能不可变" ID="JS_4_4"/>
      <node TEXT="forEach 不要写复杂逻辑" ID="JS_4_5"/>
    </node>

    <node TEXT="5. 一句话结论" POSITION="left" ID="JS_5">
      <node TEXT="Stream 擅长数据加工，不替代所有 for" ID="JS_5_1"/>
    </node>
  </node>
</map>