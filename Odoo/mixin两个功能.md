*Thinking...*

> **Clarifying Odoo inheritance**
> 
> I need to answer about using citations since I referred to web resources. Citing the relevant Odoo docs is important, but I shouldn't overdo it. I think about creating a complete module with an abstract model, log model, and mixin that uses _inherit = ['external.sync.mixin'] in the models.
> 
> I want to confirm the details for the abstract model, specifically setting _name, _description, and _auto = False. Since this is an AbstractModel, it doesn’t create a table, right? I’ll also clarify multiple inheritance syntax and how to implement it robustly.
> 
> **Implementing whitelist and functions**
> 
> I need to implement a default whitelist for all writable, non-computed fields, excluding denied ones, but I prefer a per-model whitelist for safety. I should consider allowing the mapping of API keys to field names, particularly if earlier model fields align with JSON.
> 
> I’ll also define attributes like _external_sync_denied_fields for system fields and set the timezone fields to 'UTC.' Additionally, I want to establish policies for logging and error handling. Functions like external_write and overriding write/create functions need careful management to avoid recursion issues. I’ll ensure there’s a proper context for safety too.
> 
> **Creating multi-model methods**
> 
> I need to consider implementing @api.model_create_multi, ensuring it handles context flags appropriately. If called with a single dictionary, Odoo's wrapper may assume a list. In Odoo 18, the create signature is `create(vals_list)`, so if the context flag is present, I should check if vals_list is a dictionary. To avoid issues, I might convert it to a list since model_create_multi expects that.
> 
> During logging, I should log every record after super().create. If there are invalid fields, I wonder if we should allow creating records with just defaults, perhaps using a context flag like `external_skip_empty_payload_on_create`, which defaults to false. For a generic mixin, raising a ValidationError if all fields are unknown could avoid creating invalid records. I’ll need to ensure some clean writable field is present or set defaults. Raising an error by default could be better, especially if the model doesn't require specific keys.
> 
> **Implementing context and logging**
> 
> I'm planning to implement a context for `external_allow_empty_write`, which will be true for write operations and false for creates.
> 
> For write operations without clean values, I’ll ensure it simply returns true while logging the action. This will include logging to the database under `external.payload.issue.log`, and I need to check if the model is installed; if not, I’ll include that info.
> 
> For date and datetime conversions, I will format datetime fields to the expected string format `YYYY-MM-DD HH:MM:SS` in UTC, as specified in Odoo docs. For date fields, normalization will be optional; I want to avoid timezones there.
> 
> In parsing, I should support values like None, False, or empty strings as false. When handling datetimes, if a date is provided but not a datetime, I will combine it with time.min and adjust for the source timezone. The dateutil.parser.isoparse will handle ISO formatted strings and return naive datetimes, which is helpful. Additionally, I might consider supporting numeric timestamps, as external JSON may use Unix timestamps.
> 
> **Supporting datetime context and timezone handling**
> 
> I’m considering supporting the context `external_datetime_epoch_unit` to allow choices between seconds and milliseconds. While it could be nice, I worry about the added code complexity; I should think about whether to default to seconds.
> 
> Regarding timezone handling, Odoo historically uses pytz, but it seems Odoo 18 might rely on zoneinfo now, so I need to confirm that. Importing `DEFAULT_SERVER_DATETIME_FORMAT` from `odoo.tools` may also help with formatting.
> 
> I should ensure the dateutil parser is available, along with handling timezone conversions carefully for aware and naive datetimes. For `+08:00` conversions, using `aware_dt.astimezone(pytz.UTC).replace(tzinfo=None)` could work. I also need to define safe fields to exclude from external sync, such as id, display_name, and others, while considering parent_path for hierarchical models.
> 
> **Defining field access rules**
> 
> I’m considering whether to define default denied fields using `message_*`, focusing on safe handling. For field object attributes, I wonder if readonly status is strictly a UI concern. In the code, readonly fields might not block ORM operations, but since safety is key, I think I should exclude them unless they meet specific criteria.
> 
> I need to establish rules, such as skipping fields that are not defined, those in the denied list, related or computed fields without inverses, and defaulting to omit readonly fields to avoid skipping important ones. Additionally, I must be cautious with relationships, especially skipping `one2many` and `many2many` fields unless whitelisted, since external JSON may not correctly handle relational values. I also need to consider how Many2one fields are managed, defaulting to allow simple fields and Many2one only with safe write criteria.
> 
> **Configuring API field access**
> 
> I’m realizing that if API fields mirror the model structure, the Many2one identifiers might not match. For safety, I think it’s best to start with explicitly allowed fields. If there’s no whitelist, I would default to only permitting simple scalar types, skipping one2many and many2many fields but allowing Many2one.
> 
> However, I’ll probably skip relational fields by default unless they’re whitelisted, providing methods to define allowed and denied fields. If `_external_json_allow_all_model_fields` is set to false, we can implement functionality to automatically allow safe scalar fields while keeping security in mind. Logging warnings for usages of auto-allowed fields would also be beneficial to maintain usability and clarity.
> 
> **Handling unknown JSON keys and logging**
> 
> I need to clarify that "unsafe JSON" implies that there may be unknown keys. In production, it's crucial to set a whitelist. I also need to implement logging for any unknown fields that are known but not writable.
> 
> For logging database fields, it might be useful to link Many2one fields to `ir.model`, but I could also just store the model name along with user and company IDs for simplicity. 
> 
> I need to include several files like `__manifest__.py` and `models/external_json_mixin.py` to ensure everything is set up properly, including access rights for logging. Odoo requires these rights for non-transient models, so menus may need to be optional.
> 
> Lastly, it's essential to explain that AbstractModel doesn’t create tables as it is meant for shared mixins, allowing concrete models to inherit from them. I should definitely include citations from the Odoo docs for clarity.
> 
> **Planning for code implementation**
> 
> I need to write the code in Chinese to meet the user's request. It's essential to avoid invalid citations when referencing statements from the internet. When we pull information from the web, I should cite the Odoo documentation for any facts related to Odoo. I’ll aim to provide concise citations for each supported statement.
> 
> While constructing the code, I want to ensure the mixin is robust but not overly lengthy, targeting a level of verbosity that's manageable. Since "帮我实现" suggests the user wants the full code, I'll include all relevant files for a complete implementation.
> 
> **Assessing potential code issues**
> 
> I see some potential issues with the `@api.model_create_multi` method in my code. The function starts by checking the context; if it’s not set, it defaults to the super class's create method. If `vals_list` is a dictionary, I convert it to a list for processing.
> 
> During the looping through `vals_list`, the code sanitizes each value. However, if `clean_vals` is empty and the context allows it, calling `super().create({}) could fail due to missing required fields. I’ll need to think this through and address these nuances!
> 
> **Clarifying methods for JSON handling**
> 
> I’m working on the `@api.model` method `_external_json_sanitize_vals(self, vals)`, which returns a tuple of `clean_vals` and a report. This report should capture raw values, unknown values, ignored known values, invalid values, and possibly normalized values.
> 
> For mapping keys, I have the function `_external_json_key_to_field(self, key)`, which retrieves the Odoo field corresponding to each external key. I need to log any unknown keys and handle potential collisions between similar names like "startTime" and "start_time," where the last one would take priority. A conflict log could be useful here for thoroughness.
> 
> Lastly, the method `_external_json_get_allowed_fields` determines which fields are allowed based on explicit settings or defaults. I'm considering if the explicit set could intentionally be empty.
> 
> **Defining allowed and denied fields**
> 
> I’m figuring out fallback logic for allowed fields. If `allowed` is `None`, then I want to auto-generate the set of candidate fields, which could be either an empty list or a combination of default and specific model fields.
> 
> For the default allowed fields, I’ve got `_external_json_auto_allow_field_types`, and I'm currently considering whether to include `many2one` types, but I'm leaning towards excluding them. 
> 
> Then, for denied fields, I’m merging default denied fields with model-specific ones. I'm implementing the `_external_json_get_denied_fields` method to accommodate these changes.
> 
> In checking if fields are writable through `_external_json_is_field_writable`, I’m establishing conditions to skip certain field types that aren't suitable for writing. It's crucial to identify explicit allowances for clear access management.
> 
> **Clarifying field handling**
> 
> I’m considering how to manage explicit allowed fields, especially with many-to-many (m2m) relationships in mind. If those are included, it could complicate things since it would call the super class's write method.
> 
> I'm also contemplating how `readonly` fields are treated. While they’re read-only in the UI, they can still be manipulated by ORM in certain contexts. So perhaps my strategy should be to skip `readonly` fields by default in our safe filter unless they are explicitly included in the whitelist.
> 
> I also need to remember to implement code for parsing date and datetime formats when importing.
> 
> **Handling datetime parsing**
> 
> In the Odoo module, I'm importing necessary libraries like JSON, logging, and datetime utilities to manage our datetime functions effectively.
> 
> I'm focusing on the `_external_json_parse_datetime` method. If the value is empty, I want to return false. I need to ensure that boolean values are rejected since they are a subclass of int. For numeric input, it’s essential to check if it's an integer or float. I should retrieve the appropriate epoch unit and convert it to a UTC aware timestamp using `datetime.fromtimestamp(seconds, tz=pytz.UTC)`.
> 
> I’ll also need to implement normalization for `datetime` and `date` types, and lastly, I must create a logging method `_external_json_create_issue_log` using `sudo().create` since the log should work like a normal model.
> 
> **Setting up logging for issues**
> 
> I'm defining the `ExternalJsonIssueLog` model, which includes fields to capture important details like `model_name`, `res_ids`, `operation`, and various payload-related fields, such as `unknown_keys`, `ignored_known_keys`, and `invalid_keys`.
> 
> It might also be beneficial to add an `external_ref` field from the context for future reference. When dumping sensitive data in `safe_json_dumps`, I want to implement a masking function to avoid exposing key terms like passwords or tokens. I'll define some masking keywords within the mixin and ensure the `fields.Text` size is manageable by allowing truncation.
> 
> Additionally, I need to prepare for scenarios where the log model may not be present. I can utilize a try-except block to avoid crashing if the model isn't available, as Odoo raises a KeyError if a model isn't installed.
> 
> **Clarifying context and logging issues**
> 
> I'm considering the potential issue with the context, specifically `self.env.context.get("external_json_sync")`, and using a single flag instead of multiple ones for enabling the context.
> 
> Another thing I noticed is the creation of logging records without available model IDs, which might be fine, but I need to check that.
> 
> When subclassing, if `_external_json_denied_fields` is overridden, I want to ensure that my getter properly merges those settings.
> 
> For models inheriting from multiple mapped models, I'm setting safe defaults for time zone, preferring UTC as a fallback instead of the user's time zone, which can be unstable. I'll prioritize using `self._external_json_source_tz` and the context's time zone when available.
> 
> **Using attributes and handling data types**
> 
> I'm thinking about how to use attributes for my methods and whether I can call `record.external_json_write(payload, source_tz="Asia/Shanghai")` and `self.env['x.external.order'].external_json_create(payload, source_tz="Asia/Shanghai")`. In my model methods for these, I'm returning the context with the payload.
> 
> For `external_json_create`, I need to ensure it accepts both individual records and lists, which should be fine.
> 
> If I'm working with nested dictionaries, Odoo's `fields.Json` should be able to handle that appropriately, and I might want to log any unknown nested structures.
> 
> Additionally, I should remember to note that the `write()` method returns `True` and that I might need to consider HTML sanitization for fields.
> 
> **Defining field types and safety measures**
> 
> I’m considering whether to exclude HTML fields for safety due to potential XSS issues, even though Odoo does sanitize HTML. It might be safer to be conservative about including those by default. So, I’m thinking of setting `_EXTERNAL_JSON_AUTO_ALLOWED_FIELD_TYPES` to exclude HTML, binary, and all relation types, while allowing only safer types like boolean, integer, and so on.
> 
> If HTML is part of an explicit whitelist, we would allow writes. For mapping, I might want to include converter hooks, like searching for a partner ID. I’ll pay attention to logging unknown fields, making sure to capture the mapped key and any denied known fields.
> 
> **Considering logging and method structure**
> 
> I'm focusing on logging for different validation scenarios. For ignored known values, I'm using a structure that pairs the field name, value, and reason. This seems effective, especially since I track unknown values separately. When it comes to invalid values, I’ll log the relevant field, value, and error message.
> 
> It’s important to ensure `self._fields` captures inherited fields, and for methods that don’t rely on records, I need to add `@api.model`. Also, I should remember to call `super()` in abstract methods to maintain functionality. Plus, if I use `self.with_context(external_json_safe_write=True).create(payload)`, that needs to leverage my mixin for proper sanitization.
> 
> **Establishing context flags and behavior**
> 
> I need to define context flags for the external JSON handling. These include settings like `external_json_safe_write` and `external_json_source_tz`, plus options for strict datetime checks and logging raw payloads. It's essential to consider how I want to handle invalid datetime entries. 
> 
> On one hand, a strict approach might raise errors, while a more flexible default could log and skip the invalid fields, allowing other fields to process. However, I'll definitely note that for required datetime fields, we might want to ensure completeness to avoid data issues. So, I think it’s reasonable to start with a more lenient default while allowing production setups to enforce strict checks. I'll implement a way to raise errors based on context.
> 
> **Addressing transaction logs and logging behavior**
> 
> It’s great that we’re discussing how to handle invalid fields. If those fields are skipped and required ones are missing, calling `super().create` will indeed raise an error, which is fine.
> 
> I need to think about transaction logs; if we log while in a transaction and then raise an error, rolling back will erase those logs. If strict mode raises, any logs would be lost too. To keep logs during failed transactions, I’d require a separate cursor or an explicit external logger, which isn't advisable in the Odoo environment. Maybe we could look into savepoints, but those could still be rolled back.
> 
> Also, I want to establish the `safe_json_dumps` function at the module level, define the log model fields, and set `_log_access` to true by default. I’ll add access permissions to ensure only certain groups can interact with the logs. It seems wise to generate external IDs for the log models while keeping access models abstract. Including optional XML for views could aid in future updates, so I'll consider adding a minimal tree/form for readability.
> 
> **Clarifying Odoo 18 view changes and organizing structure**
> 
> In Odoo 18, it seems there’s a shift from using `<tree>` to `<list>` for views. I should confirm this since the Odoo 18 UI appears to use `<list>`. If I'm unsure, a quick web search might help, but maybe it’s unnecessary. I can choose to omit XML unless specifically needed or use the `<list>` structure. 
> 
> I need to focus on creating a minimal module while ensuring we still provide sufficient access, as logs will be important for the DBA. Mentioning an optional view is a good idea too.
> 
> Now, regarding the manifest file, it should look like this:
> 
> ```python
> {
>  'name': 'External JSON Sync Mixin',
>  'version': '18.0.1.0.0',
>  'depends': ['base'],
>  'data': ['security/ir.model.access.csv'],
>  'installable': True,
>  'application': False,
>  'license': 'LGPL-3',
> }
> ```
> 
> In `models/__init__.py`, I can import the necessary files like this:
> 
> ```python
> from . import external_json_sync_mixin
> from . import external_json_issue_log
> ```
> 
> I’m wondering if class definitions should stay in the same file or if splitting them up is better. It might be cleaner to simplify things into one file for the external JSON sync. I do need to ensure that the field names don’t conflict between Python fields and models. Finally, I’ll make sure the code is accurate in every aspect.
> 
> **Carefully organizing code for external JSON handling**
> 
> I’m working on the `models/external_json_sync.py` file, and I need to be methodical about how I write the code.
> 
> First, here's the setup for the safe JSON dumps function. It ensures that I can handle the value correctly while managing potential exceptions. If the JSON length exceeds a specified maximum, I’ll truncate it for clarity:
> 
> ```python
> def _safe_json_dumps(value, max_length=30000):
>     try:
>         text = json.dumps(value, ensure_ascii=False, default=str, indent=2)
>     except Exception:
>         text = repr(value)
>     if max_length and len(text) > max_length:
>         return text[:max_length] + "\n... truncated ..."
>     return text
> ```
> 
> For my log model, I’m defining the `ExternalJsonIssueLog` class, and considering adding attributes like `source_model` and `model_name`, as well as `res_ids` for tracking. 
> 
> In the mixin class itself, I’m establishing several important attributes, such as `_external_json_enabled_context_key` and `_external_json_allowed_fields`. I wonder if some class attributes should be lowercase for consistency and clarity. 
> 
> Overall, I want to ensure that everything stays organized and functions smoothly within the framework!
> 
> **Refining Odoo methods for external JSON handling**
> 
> Odoo seems to treat underscore attributes well, so I'll set up some methods accordingly. 
> 
> First, I'll create the `_external_json_is_enabled` method to check whether JSON functionality is enabled based on context. 
> 
> Next, I'll define `_external_json_get_source_tz_name` to retrieve the source timezone, defaulting to "UTC" if not specified.
> 
> For the `external_json_write` method, I’ll build context and call the write method with it. I need to ensure that if `extra` includes None, I'll filter it out.
> 
> I’m also considering renaming `external_json_create` to `create_external_json` for clarity and then providing aliases like `write_external_json`.
> 
> In the `write` method, I will log the operation after calling the super method, even if the write fails. This ensures I capture all essential logs, but I need to be cautious about transaction rollbacks if failures happen.
> 
> **Clarifying logging and writing strategy in Odoo**
> 
> I’m thinking through the logging process. If I log before the write operation and the write fails, the log will roll back too, so maybe logging after the successful write is ideal to include actual results.
> 
> But I need to ensure that if `super().write(clean_vals)` fails because of invalid data, I’ll miss logging unknown values. It might be necessary to utilize a separate cursor for unknown log entries, even if Odoo raises a value error.
> 
> So, I plan to sanitize data, log, then write. If `super().write` fails, it will trigger a rollback, but I can log the unknown values before the write for transparency. I should make sure that unknown values get logged to aid debugging and keep improving the fields.
> 
> **Optimizing logging strategy for create and write operations**
> 
> I’m considering the logging process carefully to avoid unnecessary database logs for writes that don't occur. It could make sense to use `_logger.warning` before calling `super().write`, which would allow logging to a file even if the database operation fails.
> 
> In the create method, I’ll log the report after successfully creating records. If `clean_vals` is empty and creation isn’t allowed, I can log a recordless report before raising an error — though this will roll back the transaction. But I can still utilize `_logger` for those cases!
> 
> **Implementing JSON sanitization in create method**
> 
> I'm refining the `create` method to integrate external JSON functionality. First, I check if this feature is enabled; if not, I fall back on the standard `super().create`.
> 
> Next, I ensure that `vals_list` is a list. As I iterate through the values, I'll sanitize them while collecting reports. If any values are not clean and empty creations aren't allowed, I log and raise a `ValidationError`. 
> 
> After the records are created, I'll make sure to log the reports accurately associated with each record. Then, I have to ensure that the `_external_json_sanitize_vals` method handles various data types correctly!
> 
> **Clarifying field properties for JSON handling**
> 
> I'm thinking about how to manage related fields effectively. It seems normally, `readonly=True` would make them non-writable, but if there's an explicit allow for writing when there's no inverse, that might be a gray area. If a related field isn't marked readonly, it could potentially be writable.
> 
> Next, I need to gather ignore reasons for fields that aren’t writable. If a field is in the denied list or isn’t in the writable fields, I’ll note that it’s not allowed or is readonly, computed, or unsupported. I’m looking at how to check those writable fields recursively!
> 
> **Streamlining value conversion methods**
> 
> I'm simplifying the field checks for conversions. First, I need to ensure the field exists, then see if it's part of the denied list. If it's computed but lacks an inverse, it shouldn't be writable. I also have to check if the field type is among the auto types.
> 
> Next, I'm setting up custom converters. So, for `_external_json_convert_value`, I'll define how to handle specific values based on the field type—as in dealing with datetime and date formats.
> 
> For date parsing, I’m creating a method to return a proper string format while managing various input types. I will ensure that it raises a `ValidationError` for any issues encountered. Plus, I need to incorporate local timezone handling properly.
> 
> **Updating datetime handling and logging**
> 
> I'm considering the importance of handling UTC localization correctly. If `dt_value` is aware, I can convert it to UTC using `astimezone(pytz.UTC)`. The `fields.Datetime.to_string` function may help with formatting the datetime.
> 
> Next, I need to define how to handle strict conversion conditions using `_external_json_should_raise_conversion_error`. This checks context settings for strictness.
> 
> For masking sensitive data, I’m creating a method that replaces certain keywords with "***". To avoid infinite loops, I should ensure that the JSON data has no cycles.
> 
> Lastly, I need to manage the logging of reports to capture unknown keys and adjust how I log raw payloads based on context.
> 
> **Handling context overrides and logging**
> 
> I'm implementing a context override for logging raw payloads. If `log_raw` isn't specified, I default it to a class attribute. I need to be aware that raw logs can contain sensitive fields, so masking will be important.
> 
> When creating log entries, I can use `self.env[log_model].sudo().create(log_vals)`. However, I should check if `log_model` exists within `self.env`. It might be safer to use a try-except block for this.
> 
> For additional logging, I’m using `_logger.warning("External JSON sanitized...")`, which is good.
> 
> I also need to ensure proper code imports and formatting, especially regarding validation errors when the payload isn't a dict or has duplicate fields. The naming of `should_raise_conversion_error` might be too vague, so I may want to reconsider it.
> 
> **Implementing error handling and record creation**
> 
> I’ll use `external_json_raise_on_invalid` for better error management. In the sanitization process, if something is invalid and strict mode is false, I can skip it, which seems like a good approach.
> 
> I want to ensure that `_normalize_custom` can handle any potential exceptions since it might throw errors. Regarding the `external_json_field_map`, if it maps to a field not in `_fields`, I should handle that as unknown, and if it maps API keys to system fields, I can categorize them as denied or ignored.
> 
> Next, for the `create` function, it handles one dictionary but can return a list of records. Odoo's `@api.model_create_multi` ensures that if a single dict is passed, it’s converted to a list for processing, returning the proper record set. I'm glad our checks for this are safe!
> 
> Lastly, using `zip(records, reports)` should maintain the order since the `create` method returns records in order, which is perfect for what I need!
> 
> **Establishing creation and write behavior**
> 
> Everything looks good! I need to ensure that if the creation list contains an empty clean entry and allowing that isn’t permissible, I’ll log the issue and raise an error before any records are created. 
> 
> If there’s no context flag, I want to maintain the strict default behavior in Odoo, which raises an error for unknown fields. It could be useful to reference the Odoo AbstractModel documentation that mentions how to create models without a database table. 
> 
> Odoo’s `write(vals)` expects field values, ensuring date and time are in UTC. I think it would be good to mention that Odoo doesn’t save time zones in the database; everything is stored in UTC. 
> 
> I’ll prepare my final answer in Markdown CommonMark with headings, aiming for clear and comprehensive content that addresses implementing these features based on what the user asked!
> 
> **Considering code implementation and edge cases**
> 
> I’m thinking about including code excerpts for the entire class, even though that might be a bit long. I want to aim for about six complete implementations without using raw URLs, opting for citations instead.
> 
> Edge cases come into play if a subclass inherits a mixin and overrides the `write` or `create` methods. The order of methods is crucial here. In Odoo, if a subclass defines `write`, it needs to call `super()` to allow the mixin to function properly. If the subclass method runs before the mixin, I need to check the method resolution order (MRO) to ensure everything works as intended.
> 
> If I set `_inherit = ['external.json.sync.mixin', 'mail.thread']`, I should also consider the MRO, which is usually fine. Using `_inherit = 'external.json.sync.mixin'` and `_name = ...` means I can use a string, but I recommend using a list. There’s a potential issue with abstract fields and attributes not creating columns since the abstract mixin has no fields. It only contains methods. 
> 
> I need to create the log model in the same file as the mixin for cohesion.
> 
> **Finalizing implementation notes**
> 
> I need to note that it's possible to directly override `write` in an abstract model, but this should only be done if the context flag is enabled. Otherwise, all writes will filter out unknown fields and hide underlying developer bugs, which is important to remember.
> 
> I also want to include code regarding "可写字段." If the explicit whitelist includes x2many, it will allow passing raw data, but for x2many, I need to use Odoo commands. When external JSON provides an array, the `write` method may throw an error, so I should consider adding a converter hook for x2many.
> 
> For the opening, I might say: "It's feasible and recommended to use `models.AbstractModel` as a mixin because it doesn't create a table, while all external models inherit from it; this ensures safe behavior only under the right context. Odoo's AbstractModel is meant for abstract superclasses with no tables, and datetime is stored in UTC."
> 
> I should structure files appropriately:
> ```
> external_json_sync/
> ├── __manifest__.py
> ├── security/ir.model.access.csv
> └── models/
>     ├── __init__.py
>     └── external_json_sync.py
> ```
> 
> Then, in the code, I must make sure there are no dollar sign math operations. I want to ensure my translations follow a format like this:
> ```
> _("Unsupported datetime value type for field '%(field)s': %(type)s") % {...}
> ```
> Alright, I’m ready to write the full code!
> 
> **Clarifying field types and handling datetime**
> 
> I need to ensure that the Odoo field type for `monetary` is 'monetary', and that `fields.Monetary` is likely also "monetary". For the `html` field, it might be 'html', which is excluded. The `field.compute` can be either None or a string, while `field.related` might be a tuple accessed using `getattr`. 
> 
> It’s good to clarify that `field.store` should be a boolean, and `field.inverse` can be a string method or None for computed fields. 
> 
> Regarding dates, the `fields.Datetime.to_datetime("2026-06-05")` returns a datetime at 00:00, and the `dateutil_parser.isoparse("2026-06-05 12:30:00")` does support formatted dates. For strings like "2026/06/05 12:30:00," I will need a custom converter to handle slashes since it could be risky to rely on `dateutil.parser.parse`.
> 
> I should also note that `pytz.UTC` has a `.zone` property, and while `source_tz.zone` may not exist for a zoneinfo, if it's a pytz timezone, it should be fine. Additionally, `pytz.timezone("UTC")` returns UTC, and `dateutil`'s `isoparse` provides an aware datetime object with `tzutc`, which can be converted to pytz with `astimezone(pytz.UTC)`. 
> 
> Lastly, I’m recalling that `datetime` is a subclass of `date`, so the order of checking types is valid. Good to have that clarified!
> 
> **Clarifying logging and write operations**
> 
> I’m considering potential log model field names like `ignored_payload` versus `ignored_known_payload`, and I want to prioritize clarity. 
> 
> In my `write` method, if there are clean values, I call `super().write(clean_vals)`, but if not, I’ll default the result to True. After that, I need to log write reports, which is crucial, especially if `super.write` changes the `write_date`.
> 
> Logging after `super` should be fine since it doesn’t inherit mixins, avoiding conflicts. However, if invalid fields are skipped, it could still work with clean writes being logged. 
> 
> Now, I wonder if logging could happen before calling `super`, but if `super.write` raises a `ValidationError` due to unknown keys or invalid selections, it wouldn’t log to the database because the transaction is rolled back. Although, I can still log on the server. Calling `_external_json_log_report` before `super` is possible but doesn’t capture failed writes since `_logger.warning` won’t run when logging after `super`. This is something I need to consider more!
> 
> **Deciding on logging strategy**
> 
> I'm thinking about calling `_external_json_log_report` before `super` so that the server log captures any unknown or invalid entries, even if the `super` call fails. Since database logs roll back with a failed write, I’ll make the logging decision before the `super` call.
> 
> If there are no clean values, I can simply return True. This way, I create a log entry even if the subsequent write raises an error. I’m noting that `_logger` warnings persist, which is helpful.
> 
> For the create method, I won't have a record ID until after creation, so I can log in a way that associates the entry. If `super` fails later, that won't log. I could log with no record before calling `super` and log again afterward, although that might create duplicates. To avoid that, it could make sense to log before only if there are invalid or unknown fields.
> 
> Also, it’s worth considering if system logs capture anything before a failure. I’ll leave the create logging after since if it fails, those logs might roll back too. I wonder if logging before the write could let me update the log entry with the `create_uid` and then let `super.write` handle the changes. That seems fine!
> 
> **Evaluating logging procedures**
> 
> I’m considering that logging before the write might trigger a flush, but it shouldn’t be a major issue. The `_external_json_log_report` uses `self.ids`, which works for creating logs afterward.
> 
> If the report contains unknown entries but no clean values, I can log that and return True. With `external_json_raise_on_invalid` set to true, invalid entries will raise errors before logging, so I might need a catch outside to handle that, though I can set a default to false.
> 
> I’ll need to include code in a block. For security CSV, I’m noting access settings for different user groups and confirming that `base.group_system` exists.
> 
> **Defining an example model**
> 
> Let’s take a look at the example model for handling external orders. I’m defining a class called `ExternalOrder`, which inherits from `external.json.sync.mixin`. Within this model, I’ll specify allowed fields and a mapping between external and internal field names.
> 
> When using the model, I'll check for existing records and decide whether to write or create new entries based on the payload. I’ll ensure to convert any date-time values correctly with the specified timezone, handling both aware and naive payloads properly. Also, I need to remember that direct writes without the right context may lead to errors and note how subclasses should call `super()` when overriding methods. A custom converter for Many2one fields could be beneficial too!
> 
> **Preparing citations and code**
> 
> I need to ensure that I incorporate proper citations throughout my work. The first paragraph discussing the `AbstractModel` and how DateTime fields are written should be cited from Odoo. Next, I’ll include a citation for the information on storing DateTime in UTC, again referencing Odoo. It's important to structure these correctly after their respective paragraphs without complicating the citations.
> 
> I also want to mention that according to Odoo 18's ORM, values for creating fields are a dictionary of field names, and date/time strings must be in UTC format. I'll keep the math clean with no dollar signs, and I should remember to include the necessary Chinese information and potential conflicts regarding date relevance in the tool's knowledge. Finally, I’ll prepare to write the actual code, including a line for handling messages related to external JSON creation!
> 
> **Defining model components**
> 
> I'm considering defining a `source` field in my log model, along with an `external_ref` field for better indexing. 
> 
> In the mixin code, I need to build a context that accommodates optional parameters like `source_tz`, `strict_datetime`, and `epoch_unit`, along with any additional context via `extra_context`. If `strict_datetime` is specified, I'll flag that in the context.
> 
> When it comes to methods, `external_json_create` should return an instance with the appropriate context, and I also need to think through how I handle field mapping with `_external_json_get_field_map`. It might be helpful to have that as an attribute instead of a method for simplicity, although there's a consideration around naming conflicts if I have a method and an attribute with the same name.
> 
> **Checking field writability**
> 
> If a subclass requires dynamic behavior, I might need to override the getter for field configurations.
> 
> In the method `_external_json_get_explicit_allowed_fields`, I’ll check if the allowed fields are set and return them as a set if they are present.
> 
> For `_external_json_is_field_writable`, if the field is not defined, I’ll return false. I also need to think about conditions like `readonly` fields, specifically if field types like Date/Datetime should be treated as read-only. 
> 
> For fields that aren't explicitly allowed, if they are in a whitelist and not included, I'll log that as a reason for denial. It’s about making sure dynamic checking is thorough!
> 
> **Reviewing field validations**
> 
> I’m noticing that the sanitization process only checks if `field_name` is writable. If it’s not and exists in `self._fields`, it gets ignored. To enhance this, I need an explicit reason method to verify allowed fields.
> 
> I plan to check `explicit_allowed` using `_external_json_get_explicit_allowed_fields()`. If a field is in the explicit list but not writable due to denials or computed fields, I’ll log that appropriately.
> 
> In `_external_json_should_raise_invalid`, I’ll retrieve the context value and return it if present; otherwise, I’ll default to the class-level variable. Lastly, for `_external_json_get_log_raw_payload`, I need to confirm how to manage the context's raw payload logging efficiently.
> 
> **Handling datetime parsing**
> 
> I’m checking how to handle values in my context. It’s good that `self.env.context.get()` returns `None` if absent and `False` if set, which simplifies the checks.
> 
> For the `_external_json_parse_datetime` method, I'm watching out for values that are booleans. If I encounter one, I’ll raise a ValidationError. 
> 
> When dealing with epoch units, I’ll retrieve it from the context or class attributes. Depending on whether it’s in seconds or milliseconds, I’ll calculate the total seconds and convert that to a UTC-aware datetime.
> 
> For string handling, I’ll first try to parse using `dateutil_parser.isoparse`, and if that fails, I’ll attempt `fields.Datetime.to_datetime()`. If either raises an error, I’ll handle that appropriately. I suspect `to_datetime()` can return either a date or datetime object—I'll need to verify that it always returns a datetime when given a date string.
> 
> **Managing datetime and logging tasks**
> 
> I'm focusing on the function `_external_json_datetime_to_utc_string`. First, I'll parse the input value using my `_external_json_parse_datetime` method. If it returns `False`, I’ll return `False` directly. If the datetime is naive, I'll localize it; otherwise, I’ll keep it as is. I’ll then convert it to UTC while ensuring it’s formatted properly.
> 
> For date parsing, I need to ensure that if the `dateutil_parser.isoparse` gives me an aware datetime, I extract the date in the correct local timezone rather than UTC. 
> 
> I also have an `_external_json_mask_payload` function that checks if the value is a dictionary or list, applying masking as necessary to protect sensitive information.
> 
> Finally, when logging with `_external_json_log_report`, I’ll handle any unknown values appropriately, masking them before logging warnings for external JSON sanitation. If there are no unknown, ignored, or invalid values, I’ll simply return without doing anything.
> 
> **Finalizing logging process**
> 
> I’m implementing the logging by creating a log with `log_vals`. If an exception occurs during creation, I’ll use `_logger.exception()` to log the error appropriately. 
> 
> For `_logger.warning`, I can include a message like, "Some keys from external JSON were not written," which conveys the issue without exposing sensitive information. I'll also check for `raw_payload` in the context and log raw values only when necessary.
> 
> When passing `res_ids`, I'll ensure it’s a list and defaults to `self.ids` if not specified. After creation, I’ll use `rec.ids` for clarity. I’m all set for the final response and will be careful not to overload with citations, keeping them concise.

可行，而且这个方案很适合你的场景。建议做成一个 **AbstractModel / mixin**：抽象模型里统一实现“外部 JSON 安全写入”和“Datetime 自动转 UTC”，每个外部映射模型只需要继承它并配置白名单即可。Odoo 官方文档也明确说明，`AbstractModel` 用于可被多个模型共享的抽象父类，不会像普通模型那样建立业务数据表；同时 Odoo 的 `Datetime` 字段按 UTC 存储，传给 ORM 的日期时间字符串也应是 UTC 的服务端格式。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html?utm_source=openai))

下面给你一套可直接落地的实现。

---

## 一、模块结构建议

例如新建模块：

```text
external_json_sync/
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── external_json_sync.py
└── security/
    └── ir.model.access.csv
```

---

## 二、`__manifest__.py`

```python
# -*- coding: utf-8 -*-

{
    "name": "External JSON Sync Mixin",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Safe external JSON write and datetime UTC normalization",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
```

---

## 三、`models/__init__.py`

```python
# -*- coding: utf-8 -*-

from . import external_json_sync
```

---

## 四、核心实现：`models/external_json_sync.py`

```python
# -*- coding: utf-8 -*-

import json
import logging
from datetime import date, datetime, time

import pytz
from dateutil import parser as dateutil_parser

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def safe_json_dumps(value, max_length=30000):
    """
    安全序列化日志内容，避免日志字段过大。
    """
    try:
        text = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    except Exception:
        text = repr(value)

    if max_length and len(text) > max_length:
        return text[:max_length] + "\n... truncated ..."

    return text


class ExternalJsonIssueLog(models.Model):
    """
    外部 JSON 写入问题日志。

    用于记录：
    - 外部 JSON 中 Odoo 模型不存在的字段；
    - Odoo 模型存在但不允许外部写入的字段；
    - Datetime / Date / 自定义转换失败的字段。
    """

    _name = "external.json.issue.log"
    _description = "External JSON Issue Log"
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

    source = fields.Char(index=True)
    external_ref = fields.Char(index=True)

    unknown_keys = fields.Text()
    ignored_keys = fields.Text()
    invalid_keys = fields.Text()

    unknown_payload = fields.Text()
    ignored_payload = fields.Text()
    invalid_payload = fields.Text()
    raw_payload = fields.Text()

    message = fields.Text()


class ExternalJsonSyncMixin(models.AbstractModel):
    """
    外部 JSON 同步通用 mixin。

    功能：
    1. 安全过滤外部 JSON 字段：
       - 模型中存在且允许写入的字段才进入 super().create/write；
       - 未知字段、被忽略字段、非法字段写入日志。

    2. Datetime 自动转 UTC：
       - fields.Datetime 自动转为 Odoo ORM 推荐的 UTC 字符串；
       - 无时区时间按照 external_json_source_tz 解释；
       - 有时区时间按自身时区转换。

    使用方式：
        record.external_json_write(payload, source_tz="Asia/Shanghai")

        self.env["x.external.model"].external_json_create(
            payload,
            source_tz="Asia/Shanghai",
        )

    或者：
        record.with_context(
            external_json_safe_write=True,
            external_json_source_tz="Asia/Shanghai",
        ).write(payload)
    """

    _name = "external.json.sync.mixin"
    _description = "External JSON Sync Mixin"

    # 开启安全写入的 context key
    _external_json_context_key = "external_json_safe_write"

    # 推荐：每个业务模型显式配置白名单。
    # 如果为 None，则使用自动模式，只允许部分简单字段类型。
    _external_json_allowed_fields = None

    # 外部 JSON key 到 Odoo 字段名的映射。
    # 例如：
    # _external_json_field_map = {
    #     "createdAt": "external_created_at",
    # }
    _external_json_field_map = {}

    # 每个模型可以追加禁止字段。
    _external_json_denied_fields = frozenset()

    # 默认永远不允许外部 JSON 直接写入的字段。
    _external_json_default_denied_fields = frozenset(
        {
            "id",
            "display_name",
            "__last_update",
            "create_uid",
            "create_date",
            "write_uid",
            "write_date",
        }
    )

    # 当模型没有配置 _external_json_allowed_fields 时，自动模式允许的字段类型。
    # 为了安全，默认不自动允许 many2one、one2many、many2many、binary、html。
    _external_json_auto_allowed_field_types = frozenset(
        {
            "char",
            "text",
            "boolean",
            "integer",
            "float",
            "monetary",
            "selection",
            "date",
            "datetime",
            "json",
        }
    )

    # 外部接口传入的无时区 datetime 默认属于哪个时区。
    # 强烈建议调用时通过 source_tz 显式传入。
    _external_json_source_tz = "UTC"

    # 默认宽松模式：字段转换失败时记录日志并跳过该字段。
    # 如果希望转换失败直接报错，可在模型中设为 True，
    # 或调用时传 strict_datetime=True。
    _external_json_raise_on_invalid = False

    # 可选：支持数字时间戳。
    # None 表示默认不接受数字时间戳。
    # 可设置为 "seconds" 或 "milliseconds"。
    _external_json_epoch_unit = None

    # 是否记录原始 payload。
    # 会自动对 token、password 等字段做简单脱敏。
    _external_json_log_raw_payload = True

    _external_json_log_model = "external.json.issue.log"

    _external_json_mask_keywords = frozenset(
        {
            "password",
            "passwd",
            "pwd",
            "token",
            "secret",
            "authorization",
            "api_key",
            "apikey",
            "access_key",
            "refresh_token",
        }
    )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @api.model
    def external_json_create(
        self,
        payload,
        source_tz=None,
        strict_datetime=None,
        epoch_unit=None,
        **extra_context,
    ):
        """
        外部 JSON 安全 create 入口。
        """
        ctx = self._external_json_build_context(
            source_tz=source_tz,
            strict_datetime=strict_datetime,
            epoch_unit=epoch_unit,
            **extra_context,
        )
        return self.with_context(**ctx).create(payload)

    def external_json_write(
        self,
        payload,
        source_tz=None,
        strict_datetime=None,
        epoch_unit=None,
        **extra_context,
    ):
        """
        外部 JSON 安全 write 入口。
        """
        ctx = self._external_json_build_context(
            source_tz=source_tz,
            strict_datetime=strict_datetime,
            epoch_unit=epoch_unit,
            **extra_context,
        )
        return self.with_context(**ctx).write(payload)

    # 兼容你前面使用过的命名风格
    @api.model
    def create_external_json(self, payload, **kwargs):
        return self.external_json_create(payload, **kwargs)

    def write_external_json(self, payload, **kwargs):
        return self.external_json_write(payload, **kwargs)

    # -------------------------------------------------------------------------
    # ORM overrides
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """
        只有 context 开启 external_json_safe_write 时才过滤外部 JSON。

        普通 Odoo 内部 create 不受影响。
        """
        if not self._external_json_is_enabled():
            return super().create(vals_list)

        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        clean_vals_list = []
        reports = []

        for vals in vals_list:
            clean_vals, report = self._external_json_sanitize_vals(
                vals,
                operation="create",
            )

            if not clean_vals and not self.env.context.get(
                "external_json_allow_empty_create",
                False,
            ):
                self._external_json_log_report(
                    operation="create",
                    report=report,
                    res_ids=[],
                    message="External JSON create skipped because no writable values were found.",
                )
                raise ValidationError(
                    _(
                        "External JSON create payload contains no writable fields "
                        "for model %s."
                    )
                    % self._name
                )

            clean_vals_list.append(clean_vals)
            reports.append(report)

        records = super().create(clean_vals_list)

        for record, report in zip(records, reports):
            record._external_json_log_report(
                operation="create",
                report=report,
                res_ids=record.ids,
            )

        return records

    def write(self, vals):
        """
        只有 context 开启 external_json_safe_write 时才过滤外部 JSON。

        普通 Odoo 内部 write 不受影响。
        """
        if not self._external_json_is_enabled():
            return super().write(vals)

        clean_vals, report = self._external_json_sanitize_vals(
            vals,
            operation="write",
        )

        self._external_json_log_report(
            operation="write",
            report=report,
            res_ids=self.ids,
        )

        if not clean_vals:
            return True

        return super().write(clean_vals)

    # -------------------------------------------------------------------------
    # Context helpers
    # -------------------------------------------------------------------------

    @api.model
    def _external_json_build_context(
        self,
        source_tz=None,
        strict_datetime=None,
        epoch_unit=None,
        **extra_context,
    ):
        ctx = {
            self._external_json_context_key: True,
        }

        if source_tz:
            ctx["external_json_source_tz"] = source_tz

        if strict_datetime is not None:
            ctx["external_json_raise_on_invalid"] = bool(strict_datetime)

        if epoch_unit:
            ctx["external_json_epoch_unit"] = epoch_unit

        ctx.update(extra_context)
        return ctx

    @api.model
    def _external_json_is_enabled(self):
        return bool(self.env.context.get(self._external_json_context_key))

    # -------------------------------------------------------------------------
    # Field allow / deny logic
    # -------------------------------------------------------------------------

    @api.model
    def _external_json_get_field_map(self):
        return dict(getattr(self, "_external_json_field_map", {}) or {})

    @api.model
    def _external_json_map_key_to_field(self, key):
        return self._external_json_get_field_map().get(key, key)

    @api.model
    def _external_json_get_denied_fields(self):
        return set(self._external_json_default_denied_fields) | set(
            getattr(self, "_external_json_denied_fields", set()) or set()
        )

    @api.model
    def _external_json_get_explicit_allowed_fields(self):
        allowed = getattr(self, "_external_json_allowed_fields", None)

        if allowed is None:
            return None

        return set(allowed)

    @api.model
    def _external_json_get_writable_fields(self):
        explicit_allowed = self._external_json_get_explicit_allowed_fields()
        explicit_mode = explicit_allowed is not None

        if explicit_mode:
            candidates = explicit_allowed
        else:
            candidates = set(self._fields.keys())

        writable = set()

        for field_name in candidates:
            if self._external_json_is_field_writable(
                field_name,
                explicit_mode=explicit_mode,
            ):
                writable.add(field_name)

        return writable

    @api.model
    def _external_json_is_field_writable(self, field_name, explicit_mode=False):
        field = self._fields.get(field_name)

        if not field:
            return False

        if field_name in self._external_json_get_denied_fields():
            return False

        # 计算字段没有 inverse，不能作为普通字段写入。
        if getattr(field, "compute", None) and not getattr(field, "inverse", None):
            return False

        # 自动模式下更保守：
        # - 只允许简单字段；
        # - readonly 字段不自动允许。
        if not explicit_mode:
            if field.type not in self._external_json_auto_allowed_field_types:
                return False

            if getattr(field, "readonly", False):
                return False

        return True

    @api.model
    def _external_json_get_ignore_reason(self, field_name):
        field = self._fields.get(field_name)

        if not field:
            return "field does not exist on model"

        explicit_allowed = self._external_json_get_explicit_allowed_fields()
        explicit_mode = explicit_allowed is not None

        if field_name in self._external_json_get_denied_fields():
            return "field is denied"

        if explicit_mode and field_name not in explicit_allowed:
            return "field is not in _external_json_allowed_fields"

        if getattr(field, "compute", None) and not getattr(field, "inverse", None):
            return "computed field without inverse"

        if not explicit_mode:
            if field.type not in self._external_json_auto_allowed_field_types:
                return "field type is not allowed in auto mode: %s" % field.type

            if getattr(field, "readonly", False):
                return "readonly field is not allowed in auto mode"

        return "field is not writable by external JSON policy"

    # -------------------------------------------------------------------------
    # Sanitization
    # -------------------------------------------------------------------------

    @api.model
    def _external_json_sanitize_vals(self, vals, operation=None):
        if not isinstance(vals, dict):
            raise ValidationError(
                _("External JSON payload must be a dict, got %s.")
                % type(vals).__name__
            )

        writable_fields = self._external_json_get_writable_fields()

        clean_vals = {}
        unknown_vals = {}
        ignored_vals = {}
        invalid_vals = {}

        field_sources = {}

        for raw_key, value in vals.items():
            if not isinstance(raw_key, str):
                unknown_vals[str(raw_key)] = value
                continue

            field_name = self._external_json_map_key_to_field(raw_key)

            if field_name in writable_fields:
                if field_name in clean_vals:
                    invalid_vals[raw_key] = {
                        "field": field_name,
                        "value": value,
                        "error": "duplicate external keys map to the same Odoo field; previous key: %s"
                        % field_sources[field_name],
                    }

                    if self._external_json_should_raise_invalid():
                        raise ValidationError(
                            _(
                                "Duplicate external JSON keys map to the same "
                                "Odoo field '%s'."
                            )
                            % field_name
                        )

                    continue

                try:
                    clean_vals[field_name] = self._external_json_convert_field_value(
                        field_name,
                        value,
                    )
                    field_sources[field_name] = raw_key

                except Exception as exc:
                    invalid_vals[raw_key] = {
                        "field": field_name,
                        "value": value,
                        "error": str(exc),
                    }

                    if self._external_json_should_raise_invalid():
                        raise

            elif field_name in self._fields:
                ignored_vals[raw_key] = {
                    "field": field_name,
                    "value": value,
                    "reason": self._external_json_get_ignore_reason(field_name),
                }

            else:
                unknown_vals[raw_key] = value

        report = {
            "raw_payload": vals,
            "unknown_vals": unknown_vals,
            "ignored_vals": ignored_vals,
            "invalid_vals": invalid_vals,
            "operation": operation,
        }

        return clean_vals, report

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    @api.model
    def _external_json_convert_field_value(self, field_name, value):
        """
        单字段转换入口。

        支持每个模型自定义字段转换方法：
            def _external_json_convert_partner_id(self, value):
                ...
        """
        custom_converter = getattr(
            self,
            "_external_json_convert_%s" % field_name,
            None,
        )

        if callable(custom_converter):
            return custom_converter(value)

        field = self._fields.get(field_name)

        if not field:
            return value

        if field.type == "datetime":
            return self._external_json_datetime_to_utc_string(value, field_name)

        if field.type == "date":
            return self._external_json_date_to_string(value, field_name)

        return value

    @api.model
    def _external_json_is_empty_time_value(self, value):
        return value is False or value is None or (
            isinstance(value, str) and not value.strip()
        )

    @api.model
    def _external_json_should_raise_invalid(self):
        context_value = self.env.context.get("external_json_raise_on_invalid")

        if context_value is not None:
            return bool(context_value)

        return bool(getattr(self, "_external_json_raise_on_invalid", False))

    @api.model
    def _external_json_get_source_tz(self):
        tz_name = (
            self.env.context.get("external_json_source_tz")
            or getattr(self, "_external_json_source_tz", None)
            or "UTC"
        )

        try:
            return pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError as exc:
            raise ValidationError(_("Invalid external JSON source timezone: %s") % tz_name) from exc

    @api.model
    def _external_json_get_epoch_unit(self):
        return (
            self.env.context.get("external_json_epoch_unit")
            or getattr(self, "_external_json_epoch_unit", None)
        )

    @api.model
    def _external_json_parse_datetime(self, value, field_name):
        if self._external_json_is_empty_time_value(value):
            return False

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, time.min)

        if isinstance(value, bool):
            raise ValidationError(
                _("Unsupported boolean datetime value for field '%s'.") % field_name
            )

        if isinstance(value, (int, float)):
            epoch_unit = self._external_json_get_epoch_unit()

            if epoch_unit not in {"seconds", "milliseconds"}:
                raise ValidationError(
                    _(
                        "Numeric datetime value for field '%(field)s' is not enabled. "
                        "Set external_json_epoch_unit to 'seconds' or 'milliseconds'."
                    )
                    % {
                        "field": field_name,
                    }
                )

            seconds = float(value)

            if epoch_unit == "milliseconds":
                seconds = seconds / 1000.0

            return datetime.fromtimestamp(seconds, tz=pytz.UTC)

        if isinstance(value, str):
            text = value.strip()

            try:
                return dateutil_parser.isoparse(text)
            except Exception:
                pass

            try:
                return fields.Datetime.to_datetime(text)
            except Exception as exc:
                raise ValidationError(
                    _("Invalid datetime value for field '%(field)s': %(value)s")
                    % {
                        "field": field_name,
                        "value": value,
                    }
                ) from exc

        raise ValidationError(
            _("Unsupported datetime value type for field '%(field)s': %(type)s")
            % {
                "field": field_name,
                "type": type(value).__name__,
            }
        )

    @api.model
    def _external_json_localize_naive_datetime(self, dt_value, field_name):
        source_tz = self._external_json_get_source_tz()

        try:
            return source_tz.localize(dt_value, is_dst=None)

        except pytz.AmbiguousTimeError as exc:
            strategy = self.env.context.get("external_json_dst_strategy", "raise")

            if strategy == "standard":
                return source_tz.localize(dt_value, is_dst=False)

            if strategy == "dst":
                return source_tz.localize(dt_value, is_dst=True)

            raise ValidationError(
                _(
                    "Ambiguous datetime value for field '%(field)s' "
                    "in timezone '%(tz)s': %(value)s"
                )
                % {
                    "field": field_name,
                    "tz": source_tz.zone,
                    "value": dt_value,
                }
            ) from exc

        except pytz.NonExistentTimeError as exc:
            raise ValidationError(
                _(
                    "Non-existent datetime value for field '%(field)s' "
                    "in timezone '%(tz)s': %(value)s"
                )
                % {
                    "field": field_name,
                    "tz": source_tz.zone,
                    "value": dt_value,
                }
            ) from exc

    @api.model
    def _external_json_datetime_to_utc_string(self, value, field_name):
        """
        将外部 datetime 转成 Odoo ORM 推荐的 UTC naive string：
            YYYY-MM-DD HH:MM:SS
        """
        dt_value = self._external_json_parse_datetime(value, field_name)

        if not dt_value:
            return False

        if dt_value.tzinfo is None or dt_value.utcoffset() is None:
            aware_dt = self._external_json_localize_naive_datetime(
                dt_value,
                field_name,
            )
        else:
            aware_dt = dt_value

        utc_naive_dt = aware_dt.astimezone(pytz.UTC).replace(tzinfo=None)

        return fields.Datetime.to_string(utc_naive_dt)

    @api.model
    def _external_json_date_to_string(self, value, field_name):
        """
        Date 字段不做 UTC 转换，只归一化为 YYYY-MM-DD。
        """
        if self._external_json_is_empty_time_value(value):
            return False

        if isinstance(value, datetime):
            return fields.Date.to_string(value.date())

        if isinstance(value, date):
            return fields.Date.to_string(value)

        if isinstance(value, str):
            text = value.strip()

            try:
                parsed_date = fields.Date.to_date(text)
                if parsed_date:
                    return fields.Date.to_string(parsed_date)
            except Exception:
                pass

            try:
                parsed_dt = dateutil_parser.isoparse(text)
                return fields.Date.to_string(parsed_dt.date())
            except Exception as exc:
                raise ValidationError(
                    _("Invalid date value for field '%(field)s': %(value)s")
                    % {
                        "field": field_name,
                        "value": value,
                    }
                ) from exc

        raise ValidationError(
            _("Unsupported date value type for field '%(field)s': %(type)s")
            % {
                "field": field_name,
                "type": type(value).__name__,
            }
        )

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    @api.model
    def _external_json_should_log_raw_payload(self):
        context_value = self.env.context.get("external_json_log_raw_payload")

        if context_value is not None:
            return bool(context_value)

        return bool(getattr(self, "_external_json_log_raw_payload", True))

    @api.model
    def _external_json_mask_payload(self, value):
        keywords = tuple(
            str(keyword).lower()
            for keyword in getattr(self, "_external_json_mask_keywords", set())
        )

        def should_mask_key(key):
            key_text = str(key).lower()
            return any(keyword in key_text for keyword in keywords)

        def mask(obj):
            if isinstance(obj, dict):
                result = {}

                for key, val in obj.items():
                    if should_mask_key(key):
                        result[key] = "***"
                    else:
                        result[key] = mask(val)

                return result

            if isinstance(obj, list):
                return [mask(item) for item in obj]

            if isinstance(obj, tuple):
                return tuple(mask(item) for item in obj)

            return obj

        return mask(value)

    def _external_json_log_report(
        self,
        operation,
        report,
        res_ids=None,
        message=None,
    ):
        unknown_vals = report.get("unknown_vals") or {}
        ignored_vals = report.get("ignored_vals") or {}
        invalid_vals = report.get("invalid_vals") or {}

        if not unknown_vals and not ignored_vals and not invalid_vals:
            return

        unknown_keys = sorted(str(key) for key in unknown_vals.keys())
        ignored_keys = sorted(str(key) for key in ignored_vals.keys())
        invalid_keys = sorted(str(key) for key in invalid_vals.keys())

        res_ids = res_ids if res_ids is not None else self.ids

        _logger.warning(
            "External JSON sanitized: model=%s, ids=%s, operation=%s, "
            "unknown_keys=%s, ignored_keys=%s, invalid_keys=%s",
            self._name,
            res_ids,
            operation,
            unknown_keys,
            ignored_keys,
            invalid_keys,
        )

        try:
            Log = self.env[self._external_json_log_model].sudo()

            raw_payload = report.get("raw_payload")
            masked_raw_payload = (
                self._external_json_mask_payload(raw_payload)
                if self._external_json_should_log_raw_payload()
                else False
            )

            log_vals = {
                "model_name": self._name,
                "res_ids": ",".join(map(str, res_ids)) if res_ids else False,
                "operation": operation,
                "source": self.env.context.get("external_json_source"),
                "external_ref": self.env.context.get("external_json_external_ref"),
                "unknown_keys": ", ".join(unknown_keys),
                "ignored_keys": ", ".join(ignored_keys),
                "invalid_keys": ", ".join(invalid_keys),
                "unknown_payload": safe_json_dumps(
                    self._external_json_mask_payload(unknown_vals)
                ),
                "ignored_payload": safe_json_dumps(
                    self._external_json_mask_payload(ignored_vals)
                ),
                "invalid_payload": safe_json_dumps(
                    self._external_json_mask_payload(invalid_vals)
                ),
                "raw_payload": safe_json_dumps(masked_raw_payload)
                if masked_raw_payload is not False
                else False,
                "message": message
                or "Some external JSON keys were not written to the target model.",
            }

            Log.create(log_vals)

        except Exception:
            _logger.exception("Failed to create external JSON issue log.")
```

---

## 五、`security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_external_json_issue_log_user,external.json.issue.log.user,model_external_json_issue_log,base.group_user,1,0,0,0
access_external_json_issue_log_manager,external.json.issue.log.manager,model_external_json_issue_log,base.group_system,1,1,1,1
```

---

## 六、业务模型如何继承

假设你有一个外部订单映射模型：

```python
# -*- coding: utf-8 -*-

from odoo import fields, models


class ExternalOrder(models.Model):
    _name = "x.external.order"
    _description = "External Order"
    _inherit = ["external.json.sync.mixin"]

    # 推荐显式白名单。
    # 外部 JSON 只有这些字段才允许写入。
    _external_json_allowed_fields = {
        "external_id",
        "name",
        "amount_total",
        "state",
        "external_created_at",
        "external_updated_at",
    }

    # 如果外部 JSON key 和 Odoo 字段名不一致，可以在这里映射。
    _external_json_field_map = {
        "id": "external_id",
        "createdAt": "external_created_at",
        "updatedAt": "external_updated_at",
    }

    # 当外部接口传来的 datetime 没有时区时，默认按这个时区解释。
    _external_json_source_tz = "Asia/Shanghai"

    external_id = fields.Char(index=True)
    name = fields.Char()
    amount_total = fields.Float()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("paid", "Paid"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )

    external_created_at = fields.Datetime()
    external_updated_at = fields.Datetime()
```

---

## 七、同步代码调用方式

```python
payload = {
    "id": "EXT-10001",
    "name": "测试订单",
    "amount_total": 128.5,
    "state": "paid",
    "createdAt": "2026-06-05 12:30:00",
    "updatedAt": "2026-06-05T15:00:00+08:00",
    "api_new_field": "这个字段 Odoo 暂时没有",
}

Order = self.env["x.external.order"]

record = Order.search(
    [
        ("external_id", "=", payload.get("id")),
    ],
    limit=1,
)

if record:
    record.external_json_write(
        payload,
        source_tz="Asia/Shanghai",
        external_json_source="order_api",
        external_json_external_ref=payload.get("id"),
    )
else:
    Order.external_json_create(
        payload,
        source_tz="Asia/Shanghai",
        external_json_source="order_api",
        external_json_external_ref=payload.get("id"),
    )
```

上面这个例子中：

```python
"createdAt": "2026-06-05 12:30:00"
```

因为没有时区，会按 `Asia/Shanghai` 解释，然后写入 UTC：

```python
"2026-06-05 04:30:00"
```

而：

```python
"updatedAt": "2026-06-05T15:00:00+08:00"
```

因为本身带 `+08:00`，会直接转为：

```python
"2026-06-05 07:00:00"
```

未知字段：

```python
"api_new_field": "这个字段 Odoo 暂时没有"
```

不会传给 `super().write()` 或 `super().create()`，而是写入 `external.json.issue.log`。

---

## 八、如果有 Many2one 字段怎么办？

默认自动模式不建议直接写 `many2one`，因为外部系统的 ID 通常不是 Odoo 数据库 ID。你可以通过字段转换器处理。

例如外部 JSON 里有：

```json
{
  "partner_id": "CUST-001"
}
```

你希望它映射到 Odoo 的 `res.partner`：

```python
class ExternalOrder(models.Model):
    _name = "x.external.order"
    _description = "External Order"
    _inherit = ["external.json.sync.mixin"]

    _external_json_allowed_fields = {
        "external_id",
        "name",
        "partner_id",
        "external_created_at",
    }

    external_id = fields.Char(index=True)
    name = fields.Char()
    partner_id = fields.Many2one("res.partner")
    external_created_at = fields.Datetime()

    def _external_json_convert_partner_id(self, value):
        if not value:
            return False

        partner = self.env["res.partner"].search(
            [
                ("x_external_customer_id", "=", value),
            ],
            limit=1,
        )

        return partner.id or False
```

只要方法名符合：

```python
_external_json_convert_字段名
```

mixin 就会自动调用。

---

## 九、严格模式和宽松模式

默认是宽松模式：

```python
record.external_json_write(payload)
```

特点：

- 未知字段：记录日志，跳过；
- 禁止写入字段：记录日志，跳过；
- Datetime 转换失败：记录日志，跳过该字段；
- 其他字段继续写入。

如果你希望 Datetime 转换失败直接报错：

```python
record.external_json_write(
    payload,
    source_tz="Asia/Shanghai",
    strict_datetime=True,
)
```

或者在模型上固定开启：

```python
_external_json_raise_on_invalid = True
```

---

## 十、建议使用方式

我建议你后续所有外部映射模型都这样写：

```python
class SomeExternalModel(models.Model):
    _name = "x.some.external.model"
    _description = "Some External Model"
    _inherit = ["external.json.sync.mixin"]

    _external_json_allowed_fields = {
        "external_id",
        "name",
        "external_created_at",
        "external_updated_at",
    }

    _external_json_source_tz = "Asia/Shanghai"

    external_id = fields.Char(index=True)
    name = fields.Char()
    external_created_at = fields.Datetime()
    external_updated_at = fields.Datetime()
```

然后同步时统一调用：

```python
record.external_json_write(payload, source_tz="Asia/Shanghai")
```

或者：

```python
Model.external_json_create(payload, source_tz="Asia/Shanghai")
```

核心原则是：**不要让外部 JSON 直接进入原生 `write()`；通过抽象 mixin 的安全入口统一过滤、转换、记录日志，再调用 `super()`。**

---
Learn more:
1. [ORM API — Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html?utm_source=openai)