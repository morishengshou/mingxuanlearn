# PlantUML 图转 Draw.io 格式指导

本文档说明将 `.puml` 文件转换为 Draw.io 可用格式的三种方法，以及各自的适用场景。

---

## 一、方法对比

| 方法 | 是否需要额外工具 | 结果可编辑性 | 适合场景 |
|------|-----------------|-------------|---------|
| Draw.io 内置 PlantUML 渲染 | 不需要 | 整体对象，可拖动 | 快速查看、排版组合 |
| 导出 SVG 后导入 | 需要 Java + plantuml.jar | 矢量图，不可拆分 | 需要高质量矢量嵌入 |
| 转为可编辑形状 | 需要第三方脚本 | 每个形状独立可编辑 | 需深度二次编辑 |

---

## 二、方法1：Draw.io 内置 PlantUML 渲染（推荐）

Draw.io 原生支持 PlantUML，无需本地安装 Java 或 plantuml.jar。

### 操作步骤

1. 打开 Draw.io 桌面版，或浏览器访问 [https://app.diagrams.net](https://app.diagrams.net)
2. 新建或打开一个 `.drawio` 文件
3. 菜单 **Extras → Edit Diagram**（快捷键 `Ctrl+Shift+X`）
4. 在弹出对话框的左下角，点击格式下拉菜单，选择 **PlantUML**
5. 将 `.puml` 文件的内容（`@startuml` 到 `@enduml` 全部）粘贴进去
6. 点击 **OK**

Draw.io 会请求在线渲染服务将 PlantUML 转为 SVG，并嵌入到画布中。

### 效果与限制

- 渲染结果与 VS Code PlantUML 插件预览一致
- 结果是一个**整体图片对象**，可在画布上自由拖动、缩放、与其他元素组合
- 图形内部的形状**不可单独选中编辑**
- 再次双击该对象可重新编辑 PlantUML 源码

### 离线环境配置

若环境无法访问外网，可在 Draw.io 中配置本地 PlantUML 服务：

1. 本地启动 PlantUML Server：
   ```bash
   java -jar plantuml.jar -picoweb:8888
   ```
2. Draw.io 菜单 **Extras → Configuration**，添加：
   ```json
   {
     "plantumlServerUrl": "http://localhost:8888/plantuml"
   }
   ```

---

## 三、方法2：导出 SVG 后导入

将 `.puml` 文件先渲染为 SVG，再导入 Draw.io。

### 前置条件

- 已安装 Java（JRE 8 或以上）
- 已下载 `plantuml.jar`（从 [https://plantuml.com/download](https://plantuml.com/download) 获取）

### 单文件导出

```bash
java -jar plantuml.jar -tsvg 01_逻辑视图.puml
# 在同目录生成 01_逻辑视图.svg
```

### 批量导出（当前项目全部视图）

```bash
java -jar plantuml.jar -tsvg "4+1架构视图/*.puml"
# 在 4+1架构视图/ 目录下生成所有 .svg 文件
```

导出 PNG（备用，不推荐用于 Draw.io）：

```bash
java -jar plantuml.jar -tpng "4+1架构视图/*.puml"
```

### 导入 Draw.io

1. 打开 Draw.io
2. 菜单 **File → Import From → Device**
3. 选择导出的 `.svg` 文件

### 效果与限制

- SVG 是矢量格式，放大不失真
- 导入后是**整体矢量对象**，无法拆分为独立形状
- 适合嵌入文档、演示文稿，或与其他 Draw.io 图形并列排版

---

## 四、方法3：转为可编辑的 Draw.io 形状

若需要在 Draw.io 中对每个形状（方框、连线、文字）单独编辑，需借助第三方转换工具。

### 工具选项

| 工具 | 地址 | 支持图类型 | 说明 |
|------|------|-----------|------|
| `plantuml-to-drawio`（社区项目） | GitHub 搜索 `plantuml2drawio` | 类图、序列图（部分） | 覆盖不完整，复杂图可能失真 |
| 手动重建 | — | 全部 | 参考 `.puml` 结构在 Draw.io 中重画 |

### 局限性说明

目前没有成熟的工具能将任意 PlantUML 语法完整转换为 `.drawio` XML 中可编辑的形状。对于包含复杂序列图、组件图、部署图的项目（如本项目的 4+1 视图），方法1 或方法2 是更实际的选择。

---

## 五、针对本项目的操作建议

本项目 `4+1架构视图/` 目录包含 9 个 `.puml` 文件，建议按以下流程处理：

### 快速预览与排版（方法1）

```
在 Draw.io 中新建一个 .drawio 文件
→ 依次用 Extras → Edit Diagram 导入每个 .puml 文件
→ 在画布上拖动排列，添加标题、说明文字
→ 保存为 4+1架构视图.drawio
```

### 批量生成 SVG 备用文件（方法2）

```bash
# 在项目根目录执行
java -jar plantuml.jar -tsvg "4+1架构视图/*.puml" -o "4+1架构视图/svg/"
```

生成的 SVG 可导入 Draw.io，也可直接嵌入 Word、Confluence 等文档。

---

## 六、Draw.io 文件格式说明

Draw.io 的原生格式 `.drawio` 本质是 XML，结构如下：

```xml
<mxfile>
  <diagram name="逻辑视图">
    <mxGraphModel>
      <!-- 各图形元素 -->
    </mxGraphModel>
  </diagram>
  <diagram name="进程视图">
    ...
  </diagram>
</mxfile>
```

一个 `.drawio` 文件可包含**多个页面（diagram）**，适合将 4+1 视图的 9 张图组织在一个文件的不同页中。
