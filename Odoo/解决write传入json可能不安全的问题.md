*Thinking...*

> **Verifying Odoo 18 module fields**
> 
> I need to create code for an Odoo 18 module and add fields like `external_ref` and `external_raw_payload`. I'm unsure if `fields.Json` is available in Odoo 18 since the documentation doesn't mention it. I think it might be introduced in Odoo 16, but I'm not totally sure. I should verify this by searching on official sources like GitHub to get the correct information. It’s crucial to be careful about the version details!
> 
> **Evaluating JSON handling in Odoo**
> 
> I’m looking into whether the documents still reference `fields.Json` since the path may have changed in Odoo 18. Using `fields.Text` could be safer to store a JSON string, particularly for raw or unknown data. If `fields.Json` is available, that’s better, but using `Text` is more universal and can work for logging. I also want to avoid recursion issues with `write` methods, so I need to ensure that my approach doesn't inherit any mixins that might cause problems.
> 
> **Defining the log model**
> 
> I need to define my log model for integration payloads. It looks something like this:
> 
> ```python
> class IntegrationPayloadLog(models.Model):
>     _name = 'integration.payload.log'
>     _description = 'External Payload Unknown Fields Log'
>     _order = 'create_date desc'
> 
>     model_name = fields.Char(required=True, index=True)
>     res_id = fields.Integer(index=True)
>     operation = fields.Selection([...])
>     unknown_keys = fields.Text()
>     ignored_payload = fields.Text()
>     raw_payload = fields.Text()
>     message = fields.Char()
> ```
> 
> For the `unknown_keys`, I might use a character/text field with comma-separated values, and for `unknown_values_json`, I could also use text.
> 
> **Creating the mixin for safety**
> 
> I'm focusing on creating a mixin responsible for safely writing external payloads. Here's the outline: 
> 
> ```python
> import json
> import logging
> from odoo import api, fields, models, _
> from odoo.exceptions import ValidationError
> 
> _logger = logging.getLogger(__name__)
> 
> class ExternalPayloadSafeMixin(models.AbstractModel):
>     _name = 'external.payload.safe.mixin'
>     _description = 'Safe External Payload Writer'
> 
>     _external_payload_blacklist = {'id', 'display_name', 'create_uid', ...}
>     _external_payload_allow_fields = None
>     _external_payload_deny_fields = set()
>     
>     @api.model
>     def _external_writable_field_names(self):
>         field_names = set(self._fields)
>         denied = set(self._external_payload_blacklist) | set(getattr(self, '_external_payload_deny_fields', set()))
>         allowed = getattr(self, '_external_payload_allow_fields', None)
>         if allowed: field_names &= set(allowed)
>         result = set()
>         
>         for name in field_names - denied:
>             field = self._fields[name]
>             if not field.store and not getattr(field, 'inverse', None):
>                 continue
>             if field.compute and not field.inverse:
>                 continue
>             
>             result.add(name)
>         return result
> ```
> 
> I need to be cautious about field attributes like compute, inverse, and store. For related fields that are computed, if there’s no inverse, it seems I can't set them. It’s essential to understand these conditions to avoid issues!
> 
> **Sanitizing external values in Odoo**
> 
> I’m refining the method to sanitize external values for Odoo. I need to consider that related fields can usually be writable unless noted otherwise, so I’ll exclude computed fields without an inverse.
> 
> Here's the outline for `_sanitize_external_vals`:
> 
> ```python
> @api.model
> def _sanitize_external_vals(self, vals):
>     if not isinstance(vals, dict):
>         _logger.warning(...)
>         raise ValidationError(_("External payload must be a dict."))
>     valid_fields = self._external_writable_field_names()
>     clean, unknown, blocked = {}, {}, {}
>     for key, value in vals.items():
>         if key in valid_fields:
>             clean[key] = value
>         elif key in self._fields:
>             blocked[key] = value
>         else:
>             unknown[key] = value
>     return clean, unknown, blocked
> ```
> 
> I need to handle untrusted JSON carefully since JSON object keys are always strings, but Python may not. If a key isn't a string, I should handle it by converting it, like `unknown[str(key)]`. Additionally, when it comes to values, they may include dates or datetimes that aren't serializable, and values for x2many might even use tuples, which aren't JSON-compatible.
> 
> **Implementing logging for external payloads**
> 
> I'm going to add a logging function for handling issues with external payloads. Here's my helper function for JSON serialization:
> 
> ```python
> def _json_dumps(value):
>     return json.dumps(value, ensure_ascii=False, default=str, indent=2)
> ```
> 
> Now for the logging function:
> 
> ```python
> def _log_external_payload_issues(self, operation, raw_vals, unknown, blocked, record_ids=None):
>     if not (unknown or blocked): return
>     msg = ...
>     _logger.warning(...)
>     if self.env.context.get('skip_external_payload_db_log'): return
>     self.env['integration.payload.log'].sudo().create({...})
> ```
> 
> I need to decide whether to create a log for each record or one log entry with all the record IDs as text. Since writes can involve multiple records, I'd lean towards using `res_ids` as text. 
> 
> For the `create` operation, I’ll log the information after calling the super method to ensure I have the ID. If `clean` is empty during a write, it should still return `True` unless the only fields are unknown. Also, if both `clean` and `self` are empty, my logic might still need to write. 
> 
> Ideally, in Odoo, `write` should return `True`. I can return `True` after logging. However, if `clean` is empty when creating, I need to handle cases where required fields might be missing. Using default values might be the way to go here!
> 
> **Overriding the write method**
> 
> I’m implementing the `write` method override:
> 
> ```python
> def write(self, vals):
>     if not self.env.context.get('from_external_api'):
>         return super().write(vals)
>     clean, unknown, blocked = self._sanitize_external_vals(vals)
>     self._log_external_payload_issues('write', vals, unknown, blocked, record_ids=self.ids)
>     if not clean:
>         return True
>     return super().write(clean)
> ```
> 
> Now I'm thinking about the ordering of the logging. If calling `super()` fails validation, the unknown fields would already be logged. Maybe I should log after calling `super()`, but I want to ensure I log unknowns even if the cleaned data is invalid.
> 
> Logging before would be beneficial to capture unknowns, but if a transaction rolls back, the database log fails as well. Since `_logger` keeps the server log, I might not need a separate savepoint or cursor.
> 
> It’s important to note that unknown fields won’t cause failures, but valid fields might fail due to type issues. If the write fails due to valid fields, I could avoid logging before trying to write. But for iteration, it might be okay to log first. Ultimately, I should note that the database log will rollback with any exceptions while the server log persists.
> 
> **Overriding the create method**
> 
> I’m working on the `create` method override:
> 
> ```python
> @api.model_create_multi
> def create(self, vals_list):
>     if not self.env.context.get('from_external_api'):
>         return super().create(vals_list)
>     clean_list = []
>     issues = []
>     for vals in vals_list: ...
>     records = super().create(clean_list)
>     for rec, raw, unknown, blocked in zip(records, ...):
>         rec._log...
>     return records
> ```
> 
> I need to log after calling `super()` to ensure that if the creation fails due to missing required fields, I won't have a database log. I could log to the server before the creation happens, while the database log would come after. If `clean` values are empty but contain required fields as unknown, it makes sense to log beforehand using `_logger`.
> 
> However, I should be cautious; if I log within the `create` override and the transaction rolls back later, the log disappears too. I also want to implement a context flag method, like:
> 
> ```python
> record.with_context(from_external_api=True).write(payload)
> ```
> 
> When handling external API calls in a controller or job, I could use something like this:
> 
> ```python
> vals = response.json()
> rec = self.env['my.model'].search([('external_id','=',vals['id'])], limit=1)
> if rec:
>    rec.with_context(from_external_api=True).write(vals)
> else:
>    self.env['my.model'].with_context(from_external_api=True).create(vals)
> ```
> 
> This is better because it makes model `write` operations safer.
> 
> **Defining an external model**
> 
> I’m considering exposing a dedicated method like this:
> 
> ```python
> def write_external_json(self, payload):
>     return self.with_context(from_external_api=True).write(payload)
> ```
> 
> Next, I'm establishing the model that uses my mixin:
> 
> ```python
> class MyExternalModel(models.Model):
>     _name = 'my.external.model'
>     _inherit = ['external.payload.safe.mixin']
>     # fields...
>     _external_payload_deny_fields = {'state'}
> ```
> 
> Now, with Odoo's multiple inheritance, I'm wondering about using `_inherit` without `_name`. To create a model named `my.external.model`, I can write:
> 
> ```python
> class MyExternalModel(models.Model):
>    _name = 'my.external.model'
>    _inherit = ['external.payload.safe.mixin']
> ```
> 
> That’s valid! Odoo allows `_inherit` to list multiple entries, and when I’m making a new model with a mixin, including `fields.Model` might be necessary.
> 
> For existing models, I could do something like:
> 
> ```python
> class MyExternalModel(models.Model):
>    _inherit = ['my.external.model', 'external.payload.safe.mixin']
> ```
> 
> In Odoo, it seems you can extend with the `_inherit` and not need `_name`. If there’s only one model, it might be simpler to override directly in it. The user may want a custom model `write` method, so providing direct code could be more straightforward.
> 
> **Discussing field matching**
> 
> I need to provide a concise answer while ensuring it's actionable. When discussing field matching, I can contrast `self._fields` with `fields_get`. While `fields_get()` returns a dictionary of field definitions, which can be filtered and is considered the official method, `self._fields` is faster and includes all fields directly within the Python model. 
> 
> It’s good to mention that `fields_get()` is useful for external clients to query field metadata. Also, when writing values, be aware of the correct field names and types, as writing might raise `AccessError` or `ValidationError`. 
> 
> I need to reference official documentation because type coercion can be a concern. "不安全 JSON" might contain invalid value types like incorrect selections or wrong date formats. Filtering out unknown fields alone won’t resolve these type errors.
> 
> **Discussing validation and coercion**
> 
> I should definitely advise adding validation and coercion for each field for full safety. For instance, convert external booleans to actual bool values and format dates using `fields.Date.to_string()`. Also, it's essential to validate selections by checking against allowed keys in `field.selection`—if the keys are invalid, log and discard them.
> 
> For relational fields, I must map external IDs to internal ones and avoid sending nested arbitrary JSON to `many2one` or `x2many`. I might use `check_field_access_rights('write', clean.keys())` to ensure there are no permission issues, especially since access rights are critical.
> 
> I should include an optional type guard, like:
> 
> ```python
> def _coerce_external_value(self, name, value):
>    field = self._fields[name]
>    if field.type == 'selection':
>        # Validate selection
>    if field.type in ('one2many', 'many2many') and not isinstance(value, list):
>        return  # Drop if invalid
> ```
> 
> The main concern is still unknown fields, and it’s important to log unmatched fields. If fields match but are invalid, that can still lead to errors, which is expected unless the value is sanitized. I could even consider implementing custom mapping, given that external JSON field names may differ from internal names.
> 
> **Planning citations and examples**
> 
> I need to incorporate proper citations throughout my writing. For instance, when discussing `write(vals)`, I should mention that this method updates records with field values and can raise `AccessError` or `ValidationError` if value types don't match the expected format, particularly for `x2many` commands—citing the relevant documentation will help back this up.
> 
> Also, readonly fields exist primarily for the UI; they can be set in code if they are stored or inversable. Computed fields are readonly by default unless they have an inverse. I should reference automatic fields like `create_uid` as mentioned in the docs, without including raw URLs.
> 
> I don't need to mention the current date, and I might not have to cite every single code fact. Just providing enough context is sufficient. I could even include a final code snippet as a minimal direct example, keeping in mind to follow CommonMark formatting while avoiding single dollar signs for math. Let’s ensure the code design is detailed and clear!
> 
> **Ensuring record order matches**
> 
> I need to verify that when using `zip(records, issue_list)`, the order of the records matches the order of the incoming issue list. This alignment is crucial for maintaining consistency when logging issues.
> 
> Since both lists are created based on the original input order, and I retrieve records in the same sequence, it should work seamlessly. However, it's always good to double-check to avoid potential mismatches that could lead to confusion when associating records with their corresponding payload issues later on. I want to ensure everything is correctly linked and nothing gets out of order!
> 
> **Considering allowed fields and logging**
> 
> It seems like when using Odoo’s `create` method, the order of the records returned should be the same as the order in which they were passed, which is good! But, there might be an issue in `_external_payload_get_allowed_field_names` if the `_external_payload_allowed_fields` is set to `None`, potentially including fields from the log mixin that should be ignored.
> 
> Should I call `self.check_field_access_rights('write', list(clean_vals))` prior to the write? Super will handle it, but since I’m using `sudo()`, access shouldn’t pose a problem. Also, should I avoid DB log creation when the model isn't installed? Since it belongs to the same module, it might be alright.
> 
> Additionally, if the log model contains potentially large field names in `unknown_keys`, it could be a concern. Perhaps, a direct model example could clarify this approach for defining allowed fields. If there are API changes adding new fields, those would end up logged as unknowns. It's worth considering if we want all current fields to be auto-written too. My final recommendation would be to specify allowed fields carefully!
> 
> **Implementing external payload handling**
> 
> I’m planning to call the API response with the payload fetched via `response.json()`. I’ll be working with a model that has a context for handling external payloads safely. When searching for an existing record using `external_id`, there's a possibility that it might not be mapped correctly or could be considered unknown. 
> 
> An alternative approach would be a method like `safe_write_from_payload` that uses a savepoint to ensure integrity during the write. It's important to note that if a separate log model isn't desired, I can use `_logger.warning` for logging issues, although a separate DB log might be more convenient for tracking iterations.
> 
> Additionally, I should consider using `fields_get` to introspect the external client’s available fields. This retrieves a dictionary mapping field names, which can be particularly useful in RPC calls. Although, internally within Odoo, I’ll rely on `_fields`, as that’s crucial for my implementation!
> 
> **Planning for value filtering in writes**
> 
> If the write operation fails due to unknown values, that could be a problem, so I should mention that types of values can also lead to write failures. I think adding per-field converters could help, so maybe I’ll include a skeleton for an optional method, though I won’t implement it fully right now. 
> 
> It would be good to provide a simple solution that filters values for one model:
> 
> ```python
> def _filter_vals(self, vals):
>     fields = set(self._fields) - BLACKLIST
>     safe = {k:v for k,v in vals.items() if k in fields}
>     unknown = {k:v for k,v in vals.items() if k not in fields}
> ```
> 
> In the final answer, I should clearly state the problem of unknown keys causing `write` errors and outline a solution with value pre-filtering using model meta fields, while logging rejected keys. I want to avoid overriding the write method globally, instead using a context flag or a dedicated method. Including minimal code for just one model will give the user a quick solution, while also discussing a more robust mixin approach!
> 
> **Creating a direct model for external data**
> 
> I’m working on direct model code for `MyModel`, which uses the external data structure. It’s structured like a mixin but designed specifically for a model. I've noticed that we could define `_external_payload_field_denylist` and `_external_payload_field_allowlist` within the model.
> 
> I’ll include a method to get writable fields, using the allowlist or defaulting to all the keys in `_fields`. 
> 
> Additionally, I should mention the option of using the `ir.logging` model in Odoo for logging purposes, though that might require some specific settings. Writing to logs with Python would go to a file, but a custom log might be better. 
> 
> One important nuance is that the `write` method I’m creating shouldn’t apply to internal writes. I’ll use a context flag to handle that. The user mentioned that if they call write manually with external JSON, they can wrap it within the context. If they want all writes to be safe without requiring this context, I need to ensure errors are still visible and not hidden. I think that covers the essentials!
> 
> **Implementing safe write and create methods**
> 
> I want to set up a method that checks for a context flag when writing values, like this: 
> 
> ```python
> if not self.env.context.get('external_json_safe_write'):
>     return super().write(vals)
> ```
> 
> Then, I’ll create a method called `safe_write_external_json`, allowing users to write payloads that toggle the context flag on.
> 
> I should consider if there's a need for `safe_create_external_json` too, since `create` may be called without existing records. Both methods will include context flags. 
> 
> My code might look like this:
> 
> ```python
> def write_external_json(self, payload):
>     return self.with_context(external_json_safe_write=True).write(payload)
> 
> @api.model
> def create_external_json(self, payload):
>     return self.with_context(external_json_safe_write=True).create(payload)
> ```
> 
> I'll make sure that `self.with_context` returns the correct model environment. 
> 
> Also, I need to address upserts and potentially log empty records. It’s essential to prevent the creation of junk records by raising a `ValidationError` if there are no clean values in the create method. This helps ensure that users are only inserting useful data!
> 
> **Handling external payloads safely**
> 
> If the external payload only contains unknown fields due to an outdated model, I definitely don't want to create default empty records. For safe creation, I'll implement a check: if there are no safe fields, I’ll log the issue and raise a `ValidationError` saying, "No known fields."
> 
> However, the user wants to log unmatched records too, so if nothing matches, I may decide not to create anything.
> 
> I'll check:
> 
> ```python
> if self.env.context.get("external_json_skip_empty_create", True) and not clean_vals:
>     raise ValidationError(_("No writable fields in external payload."))
> ```
> 
> This could potentially be risky, since if required fields are missing, it will fail anyway. I need to guard against creating junk records, so I’ll include:
> 
> ```python
> if not clean_vals:
>     raise ValidationError(_("External payload contains no writable field for %s.") % self._name)
> ```
> 
> If the `external_id` is missing, I need to think about that too. 
> 
> For the write operation, if there are no known fields, returning `True` might indicate there’s nothing to update after logging. But for create operations, raising an error might defeat the purpose of a safe implementation. 
> 
> Since the goal is safety without failures, I could consider logging to the server log before raising an error rather than affecting the database. This way, I’m managing risk without interrupting the flow!
> 
> **Safeguarding record creation from unknown data**
> 
> When dealing with unknown-only creates, I think it’s better not to create records at all. I could use a flag like `_external_payload_create_empty = False`. If there are no clean values in a create operation, returning isn’t an option since `create` must return a record, so I would raise a `ValidationError` indicating that the create payload has no writable field.
> 
> There shouldn’t be a DB log for this error, yet if the source contains only unknowns, raising an error may be acceptable. Although the user is primarily interested in the write method, data from an API could also involve create operations.
> 
> I should note that Odoo documentation expects Many2one IDs and x2many commands for relational fields. If the external JSON includes nested objects, filtering won’t suffice, and mapping will be necessary.
> 
> Also, perhaps it’s wise to automatically include one2many/many2many in a denylist unless I can confirm these are command lists. After all, the current code allows all relational fields, which may not be safe for untrusted external JSON!
> 
> **Improving safety with external JSON payloads**
> 
> I’m considering excluding one2many and many2many fields by default for external JSON handling, even though user models might only have simple fields. It seems wise to create an allowlist for security, which would limit what fields can be included. If an allowlist isn’t set, it could allow all stored fields except the denied ones, though that could be risky. 
> 
> I think it’s best to ensure that only fields in the allowlist are included, especially since including Many2one could lead to external JSON setting arbitrary IDs.
> 
> For large payloads, I should add a truncation feature to prevent them from overwhelming the database. I’d also want to mask any sensitive information (like PII) before logging, particularly if the payloads are considered untrusted. Additionally, I should verify that the import for `fields.Text` in Odoo 18 is functioning correctly.
> 
> **Citing documentation for clarity**
> 
> I’m considering how to incorporate citations in the code, and it seems we don’t need any direct citations there. For the final output, it’s important to reference relevant documents. For instance, in the section “为什么不能直接write,” I’ll cite Odoo 18 documentation on the `write(vals)` method, clarifying that this uses field values and listing expectations for valid fields—especially since unknown or invalid fields should be filtered out before writing. 
> 
> For `fields_get`, I can note that the official docs explain it returns a dictionary indexed by field name. Additionally, I might want to mention nuances around `readonly` fields and automatic fields, but we don't need specific citations for those. I can also explain that the "invalid field" errors arise when keys are provided outside the model’s field set, and it’s best to cite the docs when necessary.

可以这样处理：**不要把外部 JSON 直接丢给 `write()`，而是在 `write()` 前做一层字段白名单/模型字段过滤；能写的传给 `super().write()`，不能写的记录日志。** Odoo 18 的 `write(vals)` 本质上就是用 `vals` 里的字段和值更新 `self` 中的记录，并且不同字段类型有各自的值格式要求，所以过滤应发生在调用 `super().write()` 之前。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html))

另外建议**不要让所有 `write()` 都静默过滤字段**，否则会把你自己代码里的拼写错误也吞掉。更好的做法是：只在外部 API 同步场景下通过 `context` 开启安全写入。

---

## 推荐实现方式

### 1. 定义一个日志模型

```python
# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def safe_json_dumps(value, max_length=20000):
    """避免日志字段过大；default=str 防止日期等对象无法序列化。"""
    text = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    if len(text) > max_length:
        return text[:max_length] + "\n... truncated ..."
    return text


class ExternalPayloadIssueLog(models.Model):
    _name = "external.payload.issue.log"
    _description = "External Payload Issue Log"
    _order = "create_date desc, id desc"

    model_name = fields.Char(required=True, index=True)
    res_ids = fields.Char(string="Record IDs", index=True)
    operation = fields.Selection(
        [
            ("create", "Create"),
            ("write", "Write"),
        ],
        required=True,
        index=True,
    )

    unknown_keys = fields.Text(string="Unknown Keys")
    ignored_known_keys = fields.Text(string="Ignored Known Keys")

    unknown_payload = fields.Text(string="Unknown Payload")
    ignored_known_payload = fields.Text(string="Ignored Known Payload")
    raw_payload = fields.Text(string="Raw Payload")
```

---

### 2. 在你的业务模型中重写 `create()` / `write()`

下面示例假设你的模型叫 `x.external.data`，你可以改成自己的模型名。

```python
class ExternalData(models.Model):
    _name = "x.external.data"
    _description = "External Data"

    # 你的字段示例
    external_id = fields.Char(index=True)
    name = fields.Char()
    amount = fields.Float()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        default="draft",
    )

    # 强烈建议生产环境使用白名单，而不是默认允许所有字段
    _external_json_allowed_fields = {
        "external_id",
        "name",
        "amount",
        "state",
    }

    # 即使在模型中存在，也不希望外部 JSON 直接写入的字段
    _external_json_denied_fields = {
        "id",
        "display_name",
        "__last_update",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
    }

    @api.model
    def _get_external_json_writable_fields(self):
        """
        返回允许外部 JSON 写入的字段名集合。

        说明：
        - 推荐使用 _external_json_allowed_fields 白名单。
        - 如果你想偷懒，也可以不定义白名单，改为从 self._fields 自动筛选。
        """
        allowed = set(getattr(self, "_external_json_allowed_fields", set()) or set())
        denied = set(getattr(self, "_external_json_denied_fields", set()) or set())

        result = set()

        for field_name in allowed:
            field = self._fields.get(field_name)
            if not field:
                continue

            if field_name in denied:
                continue

            # 排除无 inverse 的计算字段、非存储字段
            if getattr(field, "compute", None) and not getattr(field, "inverse", None):
                continue

            if not getattr(field, "store", True) and not getattr(field, "inverse", None):
                continue

            result.add(field_name)

        return result

    @api.model
    def _sanitize_external_json_vals(self, vals):
        """
        将外部 JSON 拆成三部分：
        - clean_vals: 可以写入 Odoo 的字段
        - unknown_vals: Odoo 模型中不存在的字段
        - ignored_known_vals: Odoo 模型中存在，但被禁止或不适合外部写入的字段
        """
        if not isinstance(vals, dict):
            raise ValidationError(_("External JSON payload must be a dict."))

        writable_fields = self._get_external_json_writable_fields()

        clean_vals = {}
        unknown_vals = {}
        ignored_known_vals = {}

        for key, value in vals.items():
            if not isinstance(key, str):
                unknown_vals[str(key)] = value
                continue

            if key in writable_fields:
                clean_vals[key] = value
            elif key in self._fields:
                ignored_known_vals[key] = value
            else:
                unknown_vals[key] = value

        return clean_vals, unknown_vals, ignored_known_vals

    def _log_external_json_issues(
        self,
        operation,
        raw_vals,
        unknown_vals,
        ignored_known_vals,
    ):
        if not unknown_vals and not ignored_known_vals:
            return

        unknown_keys = sorted(unknown_vals.keys())
        ignored_known_keys = sorted(ignored_known_vals.keys())

        _logger.warning(
            "External JSON sanitized: model=%s, ids=%s, operation=%s, "
            "unknown_keys=%s, ignored_known_keys=%s",
            self._name,
            self.ids,
            operation,
            unknown_keys,
            ignored_known_keys,
        )

        # 记录到数据库，便于后续迭代字段
        try:
            self.env["external.payload.issue.log"].sudo().create(
                {
                    "model_name": self._name,
                    "res_ids": ",".join(map(str, self.ids)) if self.ids else False,
                    "operation": operation,
                    "unknown_keys": ", ".join(unknown_keys),
                    "ignored_known_keys": ", ".join(ignored_known_keys),
                    "unknown_payload": safe_json_dumps(unknown_vals),
                    "ignored_known_payload": safe_json_dumps(ignored_known_vals),
                    "raw_payload": safe_json_dumps(raw_vals),
                }
            )
        except Exception:
            # 日志失败不应该影响主业务写入
            _logger.exception("Failed to create external payload issue log.")

    def write(self, vals):
        """
        只有 context 中带 safe_external_json=True 时才做安全过滤。
        普通 Odoo UI 或内部代码调用 write() 时仍保持原生行为。
        """
        if not self.env.context.get("safe_external_json"):
            return super().write(vals)

        clean_vals, unknown_vals, ignored_known_vals = self._sanitize_external_json_vals(vals)

        self._log_external_json_issues(
            operation="write",
            raw_vals=vals,
            unknown_vals=unknown_vals,
            ignored_known_vals=ignored_known_vals,
        )

        # 外部 JSON 只有未知字段时，不写入，但也不报错
        if not clean_vals:
            return True

        return super().write(clean_vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        create 也建议一并处理，否则首次同步新增记录时仍可能因为未知字段报错。
        """
        if not self.env.context.get("safe_external_json"):
            return super().create(vals_list)

        clean_vals_list = []
        issue_list = []

        for vals in vals_list:
            clean_vals, unknown_vals, ignored_known_vals = self._sanitize_external_json_vals(vals)

            if not clean_vals:
                _logger.warning(
                    "External JSON create skipped because no writable fields were found. "
                    "model=%s, unknown_keys=%s, ignored_known_keys=%s",
                    self._name,
                    sorted(unknown_vals.keys()),
                    sorted(ignored_known_vals.keys()),
                )
                raise ValidationError(
                    _("External JSON payload contains no writable fields for model %s.")
                    % self._name
                )

            clean_vals_list.append(clean_vals)
            issue_list.append((vals, unknown_vals, ignored_known_vals))

        records = super().create(clean_vals_list)

        for record, issue in zip(records, issue_list):
            raw_vals, unknown_vals, ignored_known_vals = issue
            record._log_external_json_issues(
                operation="create",
                raw_vals=raw_vals,
                unknown_vals=unknown_vals,
                ignored_known_vals=ignored_known_vals,
            )

        return records

    def write_external_json(self, payload):
        """
        给外部同步任务调用的安全入口。
        """
        return self.with_context(safe_external_json=True).write(payload)

    @api.model
    def create_external_json(self, payload):
        """
        给外部同步任务调用的安全入口。
        """
        return self.with_context(safe_external_json=True).create(payload)
```

---

## 3. 同步代码这样调用

```python
payload = external_response.json()

Model = self.env["x.external.data"].with_context(safe_external_json=True)

external_id = payload.get("external_id")

record = Model.search([("external_id", "=", external_id)], limit=1)

if record:
    record.write(payload)
else:
    Model.create(payload)
```

如果外部 API 的主键叫 `id`，不要直接写 Odoo 的 `id`，建议先映射：

```python
payload["external_id"] = payload.pop("id", False)
```

---

## 注意点

1. **推荐白名单。** 不建议默认把 `self._fields` 里的所有字段都允许外部写入，尤其是 `company_id`、`user_id`、`active`、`state`、金额、权限相关字段等。

2. **未知字段和非法字段值是两类问题。** 上面的代码解决的是“外部 JSON 多了模型不存在的 key”。但如果 key 是存在的，value 类型不对，例如 `Float` 给了字符串、`Selection` 给了不存在的值、`Many2one` 给了外部系统 ID，`super().write()` 仍可能报错。Odoo 18 官方文档也说明了 `Many2one` 应传数据库记录 ID，`One2many` / `Many2many` 应传 `Command` 列表，日期时间字符串还要符合服务端格式。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html))

3. **不要只看 `readonly`。** Odoo 文档说明 `readonly` 主要影响 UI，代码中仍可能写入存储字段或有 inverse 的字段；计算字段默认不存储，且没有 inverse 时不能作为普通写入字段处理。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html))

4. **系统字段要排除。** 例如 `id`、`display_name`、`create_uid`、`create_date`、`write_uid`、`write_date` 属于自动/访问日志字段，不应该让外部 JSON 直接写入。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html))

5. 如果你想动态查看模型有哪些字段，可以在 Odoo 内部用 `self._fields`，外部 RPC 客户端可以用 `fields_get()`；官方说明 `fields_get()` 返回的是按字段名索引的字段定义字典。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html))

核心原则就是：**外部 JSON 进入 Odoo ORM 前先过滤、映射、校验；`super().write()` 只接收你确认安全的 `clean_vals`。**

---
Learn more:
1. [ORM API — Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)