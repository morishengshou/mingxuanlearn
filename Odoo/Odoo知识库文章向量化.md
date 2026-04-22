# Odoo 知识库文章自动同步到 llm_knowledge 的完整方案

下面是一套可直接落地的工程方案，覆盖数据建模、增量同步、切片策略、向量化、更新/删除级联、触发机制和容错。

## 一、前置理解：两个模块的数据模型

### 1. Odoo `knowledge.article`（Enterprise 模块）

如果你用的是社区版，`knowledge` 模块是 Enterprise 的。社区版可用替代：
- **OCA `document_knowledge`** 或 **`document_page`**（文档页）
- **自研 `knowledge.article` 类模型**

关键字段（以 `knowledge.article` 为例）：

| 字段 | 说明 |
|------|------|
| `name` | 标题 |
| `body` | HTML 正文 |
| `parent_id` | 父文章（树形） |
| `write_date` | 最后修改时间（增量同步关键） |
| `active` | 是否归档 |
| `category` | 分类（Workspace/Private/Shared） |

### 2. `llm_knowledge` 的核心模型

基于 apexive odoo-llm 的实现，涉及的模型大致如下（以实际源码为准）：

```
llm.knowledge.collection     # 知识库集合（类似 "公司制度" "产品手册"）
  ├─ llm.document            # 原始文档（一篇文章 = 一个 document）
  │    ├─ source_model       # 源数据来源模型，如 'knowledge.article'
  │    ├─ source_res_id      # 源记录 ID
  │    ├─ content_hash       # 内容哈希，用于判断是否需要重新向量化
  │    └─ state              # draft / parsed / chunked / embedded / error
  └─ llm.document.chunk      # 切片
       ├─ document_id
       ├─ sequence
       ├─ content             # 切片文本
       ├─ token_count
       └─ embedding           # pgvector(1024) 或 JSON
```

如果你用的是官方 llm_knowledge，字段名请在安装后用 `Developer → Technical → Models` 核对；下面的代码以最通用的字段命名给出，你按实际稍作替换即可。

## 二、同步架构设计

```
┌───────────────────────────┐
│  knowledge.article        │
│  (create/write/unlink)    │
└───────────┬───────────────┘
            │ override CRUD + Cron(增量)
            ▼
┌───────────────────────────────────────────┐
│  llm.knowledge.sync (中间层，自研模块)      │
│  - mapping: article -> document           │
│  - content_hash 比对                      │
│  - HTML → Markdown/纯文本                 │
└───────────┬───────────────────────────────┘
            │ 入队
            ▼
┌───────────────────────────────────────────┐
│  queue_job (OCA) 或 ir.cron               │
│  异步执行：parse → chunk → embed           │
└───────────┬───────────────────────────────┘
            ▼
┌───────────────────────────────────────────┐
│  llm.document / llm.document.chunk        │
│  pgvector 存储                             │
└───────────────────────────────────────────┘
```

设计要点：
1. **解耦**：用户保存文章的事务必须快速返回；向量化走异步队列。
2. **增量**：用 `content_hash` + `write_date` 判断是否真的需要重跑 embedding（embedding 是付钱/耗 GPU 的）。
3. **级联删除**：文章归档/删除时，对应 document 和 chunk 也要清理（或标记 inactive）。
4. **幂等**：同一篇文章重复触发不会产生多份数据。

## 三、自研桥接模块 `llm_knowledge_bridge`

### 1. 目录结构

```
llm_knowledge_bridge/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── knowledge_article.py      # 继承 knowledge.article
│   ├── llm_knowledge_sync.py     # 同步控制器
│   └── llm_document.py           # 扩展 llm.document
├── data/
│   ├── ir_cron.xml
│   └── llm_collection.xml
├── views/
│   └── sync_views.xml
└── security/
    └── ir.model.access.csv
```

### 2. `__manifest__.py`

```python
{
    "name": "LLM Knowledge Bridge",
    "version": "18.0.1.0.0",
    "depends": [
        "knowledge",          # 或 document_page / document_knowledge
        "llm",
        "llm_knowledge",
        "queue_job",          # 可选，强烈建议
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/llm_collection.xml",
        "data/ir_cron.xml",
        "views/sync_views.xml",
    ],
    "license": "LGPL-3",
}
```

### 3. 核心：同步服务 `llm_knowledge_sync.py`

```python
import hashlib
import logging
import re
from html import unescape

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMKnowledgeSync(models.AbstractModel):
    """知识库 → llm_knowledge 同步服务（无状态工具类）"""
    _name = "llm.knowledge.sync"
    _description = "LLM Knowledge Sync Service"

    # ---------------------- 工具方法 ----------------------

    @api.model
    def _html_to_text(self, html):
        """把 Odoo 富文本字段转成适合 LLM 的纯文本/Markdown。
        生产环境推荐用 markdownify 或 readability-lxml。"""
        if not html:
            return ""
        # 简化版：去标签 + 解码实体
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</p>|</div>|</li>|</h[1-6]>", "\n", text, flags=re.I)
        text = re.sub(r"<li[^>]*>", "- ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    @api.model
    def _compute_content_hash(self, title, body_text):
        """内容哈希：用于判定是否需要重跑 embedding"""
        raw = f"{title or ''}\n\n{body_text or ''}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @api.model
    def _get_default_collection(self):
        """默认知识库集合"""
        col = self.env.ref(
            "llm_knowledge_bridge.collection_internal_knowledge",
            raise_if_not_found=False,
        )
        if not col:
            col = self.env["llm.knowledge.collection"].search(
                [("name", "=", "Internal Knowledge")], limit=1
            )
        if not col:
            raise UserError("未找到默认 LLM Knowledge Collection，请先配置。")
        return col

    # ---------------------- 主流程 ----------------------

    @api.model
    def sync_article(self, article, force=False):
        """同步单篇文章到 llm.document。
        返回 document 记录。"""
        if not article.exists():
            return False

        Document = self.env["llm.document"].sudo()
        collection = self._get_default_collection()

        body_text = self._html_to_text(article.body)
        content_hash = self._compute_content_hash(article.name, body_text)

        # 查找是否已存在对应 document
        doc = Document.search(
            [
                ("source_model", "=", "knowledge.article"),
                ("source_res_id", "=", article.id),
            ],
            limit=1,
        )

        # 空内容则跳过（也可以选择删除旧 doc）
        if not body_text.strip():
            if doc:
                doc.action_archive() if hasattr(doc, "action_archive") else doc.unlink()
            return False

        vals = {
            "name": article.name or f"Article #{article.id}",
            "collection_id": collection.id,
            "source_model": "knowledge.article",
            "source_res_id": article.id,
            "mimetype": "text/plain",
            "raw_content": body_text,
            "content_hash": content_hash,
            "metadata": {
                "article_id": article.id,
                "parent_id": article.parent_id.id if article.parent_id else None,
                "write_date": fields.Datetime.to_string(article.write_date),
                "url": f"/odoo/knowledge/{article.id}",
            },
        }

        if doc:
            if not force and doc.content_hash == content_hash:
                _logger.debug("Article %s unchanged, skip embedding.", article.id)
                return doc
            doc.write(vals)
            doc.state = "draft"          # 重置状态，重新走流水线
            doc.chunk_ids.unlink()       # 清旧切片
        else:
            doc = Document.create(vals)

        # 入队（推荐）或同步执行
        if "queue_job" in self.env.registry._init_modules or hasattr(doc, "with_delay"):
            doc.with_delay(priority=20, description=f"Embed {doc.name}").action_process()
        else:
            doc.action_process()  # 阻塞式：parse → chunk → embed

        return doc

    @api.model
    def sync_articles(self, articles, force=False):
        """批量同步"""
        results = []
        for art in articles:
            try:
                results.append(self.sync_article(art, force=force))
            except Exception as e:
                _logger.exception("Sync article %s failed: %s", art.id, e)
        return results

    @api.model
    def sync_all_incremental(self, since=None):
        """Cron 入口：增量同步。since 为 None 时取上次运行时间。"""
        Param = self.env["ir.config_parameter"].sudo()
        last_run_key = "llm_knowledge_bridge.last_sync"
        since = since or Param.get_param(last_run_key)

        domain = [("active", "=", True)]
        if since:
            domain.append(("write_date", ">=", since))

        articles = self.env["knowledge.article"].search(domain)
        _logger.info("Incremental sync: %s articles.", len(articles))
        self.sync_articles(articles)

        Param.set_param(last_run_key, fields.Datetime.to_string(fields.Datetime.now()))
        return len(articles)

    @api.model
    def remove_for_article(self, article_id):
        """文章删除/归档时清理向量"""
        docs = self.env["llm.document"].sudo().search(
            [
                ("source_model", "=", "knowledge.article"),
                ("source_res_id", "=", article_id),
            ]
        )
        docs.chunk_ids.unlink()
        docs.unlink()
```

### 4. 挂钩 CRUD：`knowledge_article.py`

```python
from odoo import api, fields, models


class KnowledgeArticle(models.Model):
    _inherit = "knowledge.article"

    # 标记该文章是否参与 LLM 同步（默认 True，敏感文章可关闭）
    llm_sync_enabled = fields.Boolean(
        string="Sync to AI Knowledge",
        default=True,
        help="取消勾选后该文章不会被向量化检索。",
    )
    llm_document_id = fields.Many2one(
        "llm.document",
        string="LLM Document",
        compute="_compute_llm_document",
        store=False,
    )

    def _compute_llm_document(self):
        Doc = self.env["llm.document"].sudo()
        for rec in self:
            rec.llm_document_id = Doc.search(
                [
                    ("source_model", "=", "knowledge.article"),
                    ("source_res_id", "=", rec.id),
                ],
                limit=1,
            )

    # ---------- CRUD 钩子 ----------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.llm_sync_enabled and rec.active:
                # 异步入队，保证用户保存不卡
                self.env["llm.knowledge.sync"].sudo().with_delay(
                    priority=30
                ).sync_article(rec)
        return records

    def write(self, vals):
        res = super().write(vals)
        # 只有影响内容/可见性的字段变更才触发
        trigger_fields = {"name", "body", "active", "llm_sync_enabled", "parent_id"}
        if trigger_fields & set(vals.keys()):
            Sync = self.env["llm.knowledge.sync"].sudo()
            for rec in self:
                if not rec.active or not rec.llm_sync_enabled:
                    Sync.with_delay(priority=30).remove_for_article(rec.id)
                else:
                    Sync.with_delay(priority=30).sync_article(rec)
        return res

    def unlink(self):
        ids = self.ids
        res = super().unlink()
        Sync = self.env["llm.knowledge.sync"].sudo()
        for aid in ids:
            Sync.with_delay(priority=30).remove_for_article(aid)
        return res

    # ---------- 手动按钮 ----------

    def action_force_resync(self):
        """form view 上的"强制重新向量化"按钮"""
        self.env["llm.knowledge.sync"].sudo().sync_articles(self, force=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "AI 知识库同步",
                "message": f"已提交 {len(self)} 篇文章重新向量化。",
                "type": "success",
            },
        }
```

> ⚠️ 注意：`with_delay` 需要装 `queue_job`。如果没装，把 `.with_delay(...)` 全部替换为直接调用即可，但同步会阻塞保存操作，文章多或向量化慢时体验差。

### 5. 扩展 `llm.document`，实现流水线

不同发行版字段名不同，下面给一个通用模板，你按实际模型补齐：

```python
from odoo import api, fields, models


class LLMDocument(models.Model):
    _inherit = "llm.document"

    content_hash = fields.Char(index=True)
    source_model = fields.Char(index=True)
    source_res_id = fields.Integer(index=True)
    raw_content = fields.Text()

    def action_process(self):
        """完整流水线：parse → chunk → embed"""
        for doc in self:
            try:
                doc._llm_parse()
                doc._llm_chunk()
                doc._llm_embed()
                doc.state = "embedded"
            except Exception as e:
                doc.state = "error"
                doc.message_post(body=f"向量化失败：{e}")
                raise

    # --- 解析 ---
    def _llm_parse(self):
        # 对于纯文本直接跳过；PDF 时可接 unstructured / pdfminer
        self.state = "parsed"

    # --- 切片 ---
    def _llm_chunk(self, chunk_size=600, overlap=100):
        Chunk = self.env["llm.document.chunk"].sudo()
        text = self.raw_content or ""
        chunks = self._split_text(text, chunk_size, overlap)
        self.chunk_ids.unlink()
        for idx, piece in enumerate(chunks):
            Chunk.create(
                {
                    "document_id": self.id,
                    "sequence": idx,
                    "content": piece,
                }
            )
        self.state = "chunked"

    @staticmethod
    def _split_text(text, size, overlap):
        """按中文句号/换行优先的滑动窗口切片"""
        import re
        sents = re.split(r"(?<=[。！？!?\n])", text)
        out, buf = [], ""
        for s in sents:
            if len(buf) + len(s) <= size:
                buf += s
            else:
                if buf:
                    out.append(buf)
                # overlap
                buf = buf[-overlap:] + s if overlap else s
        if buf.strip():
            out.append(buf)
        return out

    # --- 向量化 ---
    def _llm_embed(self, batch_size=16):
        provider = self.collection_id.embedding_provider_id or self.env[
            "llm.provider"
        ].search([("is_default_embedding", "=", True)], limit=1)
        if not provider:
            raise Exception("未配置 Embedding Provider")

        chunks = self.chunk_ids.sorted("sequence")
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = provider.embed([c.content for c in batch])
            for c, v in zip(batch, vectors):
                c.embedding = v  # pgvector 字段
```

### 6. Cron：兜底增量同步 `data/ir_cron.xml`

```xml
<odoo>
    <record id="cron_llm_knowledge_incremental_sync" model="ir.cron">
        <field name="name">LLM Knowledge: Incremental Sync</field>
        <field name="model_id" ref="model_llm_knowledge_sync"/>
        <field name="state">code</field>
        <field name="code">model.sync_all_incremental()</field>
        <field name="interval_number">15</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>
</odoo>
```

Cron 的作用是兜底：万一 CRUD 钩子漏掉（批量导入、DB 级修改、队列失败等），15 分钟内也会补上。

### 7. 默认 Collection `data/llm_collection.xml`

```xml
<odoo>
    <record id="collection_internal_knowledge" model="llm.knowledge.collection">
        <field name="name">Internal Knowledge</field>
        <field name="description">公司内部知识库文章（自动同步）</field>
        <!-- <field name="embedding_model_id" ref="..."/> -->
        <!-- <field name="chunk_size">600</field> -->
        <!-- <field name="chunk_overlap">100</field> -->
    </record>
</odoo>
```

## 四、检索侧：把同步的知识用起来

RAG 查询时，除了向量相似度，还要回带 Odoo 的访问控制：

```python
class LLMKnowledgeSearch(models.AbstractModel):
    _inherit = "llm.knowledge.search"  # 或 llm.document（按实际）

    @api.model
    def search_with_acl(self, query, user=None, top_k=5):
        user = user or self.env.user
        # 1. 向量召回 top_k * 5
        candidates = self.semantic_search(query, top_k=top_k * 5)
        # 2. 按来源模型做 ACL 过滤
        kept = []
        for chunk in candidates:
            doc = chunk.document_id
            if doc.source_model == "knowledge.article":
                art = (
                    self.env["knowledge.article"]
                    .with_user(user)
                    .browse(doc.source_res_id)
                )
                try:
                    art.check_access_rights("read")
                    art.check_access_rule("read")
                except Exception:
                    continue
            kept.append(chunk)
            if len(kept) >= top_k:
                break
        return kept
```

这一步很重要：**不做 ACL 过滤的话，AI 会把 A 用户看不到的文章内容回答给他**，这是典型的数据泄露。

## 五、工程落地细节与坑

### 1. 事务与并发
- CRUD 钩子里一定用 `with_delay`，不要在 `create/write` 里同步调用 HTTP（Odoo 事务会被 LLM 请求拉长，写锁期间影响并发）。
- 同一 document 的 embedding 任务要去重，用 `queue_job` 的 `identity_key`：
  ```python
  .with_delay(identity_key=f"embed-doc-{rec.id}").sync_article(rec)
  ```

### 2. 内容清洗
- Odoo 富文本里常有 `<o_image>`、`data-oe-*` 属性，简单正则会残留一堆标签。建议用 **markdownify** 或 **readability-lxml** 转成 Markdown，效果更适合 LLM。
- 表格要保留：富文本里的 `<table>` 用 markdownify 可转成 Markdown 表格，对 Qwen/GLM 理解表格很友好。

### 3. 切片策略（中文）
- 推荐 `chunk_size=500~800 字符`，`overlap=100~150`。
- 优先按标题层级切：先按 `#`、`##` 分段，再在段内滑窗。
- 每个 chunk 头部可加面包屑：`"《员工手册》 > 考勤规则 > 请假流程\n\n..."`，召回后上下文更完整。

### 4. Embedding 性能
- `bge-m3` 在 A100/3090 上 batch=32 时约 500~1000 chunk/s；量大时建议专用 embedding 服务（Xinference / TEI）。
- 把 embedding provider 的 `timeout` 调大（60s+），batch 请求比单条快 10 倍。

### 5. pgvector
- `llm_knowledge` 通常已建好 ivfflat 或 hnsw 索引；如果自建，建议：
  ```sql
  CREATE INDEX ON llm_document_chunk USING hnsw (embedding vector_cosine_ops);
  ```
- 向量维度必须和 embedding 模型一致（bge-m3 是 1024，bge-large-zh 是 1024，text-embedding-3-small 是 1536）。切换模型时要全量重跑。

### 6. 删除 vs 归档
- 对"可恢复"的归档（`active=False`），建议同步把 document 也设为 inactive，而不是 unlink。这样用户取消归档时可以通过 hash 判断无变化从而免去重新 embedding。
- 彻底删除才走 `remove_for_article`。

### 7. 多语言
- 如果知识库有中英混合，用 **bge-m3**（原生支持多语言）；不要用纯中文 embedding 模型，否则英文语义召回会退化。

### 8. 监控
- 加一个"同步看板"：
  - 总文章数 / 已向量化数 / 失败数 / 待处理数
  - 最近 24h embedding 耗时 p50 / p95
  - queue_job 队列积压
- 失败的 document `state='error'` 可以在列表视图里加个 "Retry" 按钮。

### 9. 权限
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_llm_sync_user,llm.knowledge.sync.user,model_llm_knowledge_sync,base.group_user,1,0,0,0
access_llm_sync_admin,llm.knowledge.sync.admin,model_llm_knowledge_sync,base.group_system,1,1,1,1
```

### 10. 初始化一次性全量同步
装完模块后，跑一次全量：

```bash
./odoo-bin shell -d yourdb
>>> env['llm.knowledge.sync'].sync_all_incremental(since='2000-01-01')
```

或加个按钮 action：

```python
def action_full_resync(self):
    arts = self.env["knowledge.article"].search([("active", "=", True)])
    for a in arts:
        self.env["llm.knowledge.sync"].sudo().with_delay(
            priority=50, identity_key=f"resync-{a.id}"
        ).sync_article(a, force=True)
```

## 六、扩展：同步其他来源

这套桥接层设计成泛型的，只要在 `sync_article` 里加分支，就能同时同步：

- `product.template` 的 `description` / `description_sale`
- `helpdesk.ticket` 已解决的问题 + 解决方案
- `mail.message` 中带标签的 FAQ
- 网站 `website.page` 的 HTML
- 附件 `ir.attachment`（PDF/Word）

推荐做一个配置表 `llm.knowledge.source`，让管理员在界面上配置：
```
{model: 'product.template', domain: [('sale_ok','=',True)], 
 title_field: 'name', body_fields: ['description_sale', 'description']}
```
然后同步服务读配置表循环处理，不用为每个模型写代码。

## 七、完整流程验证清单

完成后按顺序验证：

1. ✅ 创建一篇 `knowledge.article`，保存 → 后台 queue_job 出现任务 → 几秒后 `llm.document` 生成 → chunks 生成 → embedding 非空。
2. ✅ 修改文章正文 → `content_hash` 变化 → 旧 chunks 被清、新 chunks 和 embedding 替换。
3. ✅ 修改文章标题不改内容 → hash 不变 → 不触发重新 embedding（省钱）。
4. ✅ 归档文章 → 关联 document 归档/删除，AI 问答不再命中。
5. ✅ A 用户问只有 B 用户能看到的文章 → AI 不返回内容（ACL 生效）。
6. ✅ 批量关闭 queue_job worker，CRUD 钩子积压 → 开启 cron → 15 分钟内补齐。
7. ✅ 在 Odoo 里问一个只有知识库里才有的答案 → LLM 正确引用文章。

---

以上方案在生产环境可用，但具体字段名（特别是 `llm.document`、`llm.document.chunk` 上的字段）请以你安装的 llm_knowledge 版本为准。告诉我你最终用的是 apexive 的 odoo-llm 还是其他仓库（或社区版用的是 `document_page` 而不是 `knowledge.article`），我可以把代码里的字段精确对齐到你的环境，并补一份 `llm_knowledge` 实际模型字段的映射说明。