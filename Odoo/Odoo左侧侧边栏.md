在 Odoo 的 hr 模块（员工看板视图 hr.employee kanban）中，左侧可折叠的“部门侧边栏”并不是由某个单一小部件独立实现的，而是“看板分组 + 控制面板 + Web 客户端侧边栏机制”的综合效果。核心要点如下：

- 视图层使用的是 hr.employee 的 kanban 视图，结合 group_by=department_id 分组
- Web 客户端（web_enterprise/web）提供的控制面板和侧边栏容器，配合企业版的 sidebar/filters UI
- 通过搜索面板（searchpanel）或分组器（groupBy）将部门作为一个分面（facet）呈现到左侧
- 折叠/展开、计数、选中高亮、过滤等交互是由前端框架（OWL/legacy JS）统一处理

实现路径概览：

1) 视图定义中启用基于部门的分组/搜索面板  
- 在 hr/views/hr_employee_views.xml 的 kanban 和 search 视图中，通常会有：
  - department_id 字段作为可分组字段（group_expand / groupby）
  - 搜索视图内启用 searchpanel，让部门显示为左侧面板项

示例（简化伪代码，非原样源码）：
- search 视图
  - <search>
    - <filter name="group_by_department" context="{'group_by': 'department_id'}" string="部门"/>
    - <searchpanel>
      - <field name="department_id" icon="fa-sitemap" enable_counters="1"/>
- kanban 视图
  - <kanban default_group_by="department_id" class="o_kanban_view o_hr_kanban">
    - <templates> ... 员工卡片 ... </templates>

说明：
- searchpanel 的 <field name="department_id"> 会在左侧生成一个可折叠的层级列表（若部门是层级结构），并且带有计数和过滤行为。
- default_group_by 或者顶部过滤器可以把看板按部门分组；但左侧的“侧边栏”外观主要来自 searchpanel 特性。

2) Web 客户端侧边栏容器  
- 企业版界面在控制面板下方渲染一个侧栏，用于 searchpanel。该侧栏支持折叠/展开、移动端自适应、滚动等。
- 折叠状态常通过本地存储或上下文在前端保持。

3) 部门层级与 group_expand  
- hr.department 是多层级（parent_id 树形），searchpanel 能递归显示层级，点击节点会应用 domain 过滤 hr.employee。
- 若要在看板列头中显示“未分配部门”等组，可使用 group_expand 或在模型中定义 _read_group_domain 或 _read_group_process_group。

4) 关键文件位置（参考，版本略有差异）  
- addons/hr/views/hr_employee_views.xml：定义 kanban 与 search 视图（含 searchpanel / filters / group_by）
- addons/web/static/src/views/search/panels/（或 enterprise 对应目录）：SearchPanel 组件
- addons/hr/models/hr_employee.py：与 read_group、字段定义有关
- addons/hr/models/hr_department.py：部门层级定义（parent_id）

5) 自己实现/定制的方式  
- 在你的模型的 search 视图中添加 searchpanel，并将层级字段放进去：
  - <searchpanel>
    - <field name="department_id" domain="[]" enable_counters="1" icon="fa-sitemap"/>
- 在 kanban/list 中设置 default_group_by 或提供一个“按部门分组”的 filter。
- 若需要“可折叠”的树形效果，确保该字段对应的关联模型是层级结构（有 parent_id 和 _parent_store），searchpanel 才会以树形展示。
- 样式与折叠行为无需你写额外 JS，Odoo 前端会自动提供；你可以通过类名或继承资产进行轻量样式调整。

6) 常见问题  
- 社区版与企业版差异：Search Panel 早期是企业版特性，具体版本请以你的 Odoo 版本为准（Odoo 14 起社区也有简化版）。如果你在社区版看不到侧边栏，检查版本与模块依赖（web_enterprise）。  
- 计数不显示：检查 enable_counters 是否开启，并确认当前用户对数据有读权限。  
- 未出现树形折叠：确认部门模型支持树结构并已正确写入 parent_id 与 _parent_store。  
- 默认展开/折叠状态：由前端保存；也可通过小幅 JS 扩展覆盖。

总结  
- 左侧可折叠的部门侧边栏，是 searchpanel 把 department_id 作为一个分面渲染在看板左侧形成的；结合 group_by 在 kanban 中分组，最终呈现员工看板+部门侧边栏的 UI。你主要需要在 search 视图中加入 <searchpanel><field name="department_id"/></searchpanel> 并确保部门是树形模型。