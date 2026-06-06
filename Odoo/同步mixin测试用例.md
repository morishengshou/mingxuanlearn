*Thinking...*

> **Exploring Odoo testing options**
> 
> I’m looking into the Odoo testing framework, particularly regarding `TransactionCase` and `SavepointCase`—though it seems `SavepointCase` may be removed in newer versions. Thus, I'll stick to `TransactionCase`. I'm considering two approaches for building test-only models. The first option involves creating a real model in a dedicated module, but it may not be ideal. The second option uses Odoo's registry to create test-only models within test files, which might align better with how Odoo loads tests.
> 
> **Examining test model setup**
> 
> I notice a pattern where test model definitions are usually in separate modules like `test_inherit` or `test_new_api`. For my module, it might be easier to include a concrete model file loaded only in tests. If I use `tools.config['test_enable']` in `models/__init__.py`, I can conditionally import my test models. However, since these models would only create tables when tests are enabled, I need to consider how this affects production when using `--test-tags`. It may mean the models don't get registered properly. I think including a test helper model might be a safer option, albeit a bit annoying. Ultimately, I plan to recommend placing the test model in `tests/test_models.py` and importing it conditionally based on the test environment.
> 
> **Clarifying Odoo test models**
> 
> I need to ensure that when using Odoo, model definitions in test files don't get registered unless handled correctly. If I import `from ..tests import test_models` in `models/__init__.py`, it might lead to recursion issues. A better approach would be to create a separate file for my test models under `models/external_json_sync_test_models.py` and import it conditionally based on `tools.config['test_enable']`. Also, even though access control isn’t enforced for superusers, I need to consider how `TransactionCase` affects access during tests, since the environment uses `SUPERUSER_ID` and the uid is 1.
> 
> **Planning test cases for Odoo**
> 
> I need to write tests focusing on field filtering for `external_json_write`. This involves checking payloads that have valid fields, unknown fields, and demonstrating the field mapping, like mapping "id" to "external_id." I also need to assert that clean fields are written correctly while ignoring unknown or denied ones like "write_date" or "create_date." 
> 
> Next, I'll verify that any attempt to write an unknown field raises a `ValueError`. Lastly, for datetime conversion, I'll ensure that a naive datetime like "2026-06-05 12:30:00" with the Asia/Shanghai timezone is recorded correctly as "2026-06-05 04:30:00," expecting it to work with Odoo's `fields.Datetime`.
> 
> **Testing Odoo datetime handling**
> 
> I’m looking into how `fields.Datetime.to_string` processes various datetime formats. For instance, converting "2026-06-05T15:00:00+08:00" gives me "07:00". When dealing with external dates like "2026-06-05T23:30:00+08:00," I note that they shouldn't convert to UTC since that's how we're using `isoparse`. 
> 
> I also need to check how invalid datetimes are handled: in loose mode, logging invalid inputs without changing existing fields, while strict mode raises a `ValidationError` that prevents any writes. Finally, I'll be testing the `external_json_create` function to ensure it correctly filters and maps unknown fields.
> 
> **Testing log assertions and conversions**
> 
> I can assert log the `res_id` after creating a record. I'm considering adding a custom converter for partner mapping, even though it might not be necessary. To extend tests, I could create a test model with `partner_id` as a `Many2one` field and use `_external_json_convert_partner_id` for referencing. However, if there's no `x_external_customer_id` on `res.partner`, I'd create a helper partner instead.
> 
> For handling duplicate keys in a payload, if both `id` and `external_id` are present, the `field_map` should correctly map `id` to `external_id`. When duplicates occur, I'd need to ensure proper logging. Additionally, I might want to test numeric epoch values for optional milliseconds as well, especially since the test model is explicitly allowed.
> 
> **Structuring Odoo models and tests**
> 
> I’m considering adding another concrete model with no allowed fields using `_external_json_allowed_fields = None` to test the automatic mode that excludes `Many2one` and read-only fields, though it might not be necessary. 
> 
> For structuring, my directory should look like this:
> 
> ```
> external_json_sync/
> ├── models/
> │   ├── __init__.py
> │   ├── external_json_sync.py
> │   └── external_json_sync_test_models.py
> └── tests/
>     ├── __init__.py
>     └── test_external_json_sync_mixin.py
> ```
> 
> In `models/__init__.py`, I need to import my models correctly. However, I have to ensure I'm using `config.get('test_enable')` properly, since `config` isn’t a dictionary. I'll also need to consider that the test model should be loaded before `ir.model.access.csv` to avoid issues, especially if it has no access CSV.
> 
> **Defining and testing the model**
> 
> I’m working on the `ExternalJsonSyncTestModel` class and defining various fields. I think including the `active` field makes sense. The `_external_json_allowed_fields` contains fields like `external_id`, `name`, and `amount_total`, along with others.
> 
> Regarding the `state`, I wonder if invalid selections will cause conversion issues or if `super.write` will raise errors — seems like a point to clarify since we’re only tackling conversions, not selection validation.
> 
> Also, I might want to test for the `internal_note` field to ensure it’s ignored if it exists, as it isn't allowed.
> 
> **Clarifying test setup**
> 
> I'm considering whether `computed_value` should be in the allowed fields list. If it's not allowed, it might just get ignored. Looking at the test file, I see I'm using `@tagged('post_install', '-at_install')`. 
> 
> I’m wondering if that’s the best choice because the test model is conditionally imported based on `test_enable`. If it runs post-install, it could lead to timing issues with dependencies. Maybe I should use `@tagged('-at_install', 'post_install')` instead? 
> 
> When I think about how `--test-tags` works, it seems to include both installation types, which adds to the complexity.
> 
> **Deciding on test configuration**
> 
> I’m realizing that I could simplify things by using the default `standard` and `at_install` options without any decorator. Even though the test model will exist right after the module installation, the log model access should be fine. I read in the documentation that default tests run once right after a module is installed.
> 
> Maybe I could consider adding `@tagged("external_json_sync")`. However, to keep it all straightforward, it might be best not to use any tag. Using `@tagged('standard', 'at_install')` could be explicit.
> 
> It's also important that the test data is properly set up to avoid any logs from previous tests, but I see that `TransactionCase` already manages rollbacks per test.
> 
> **Planning test setup**
> 
> I need to ensure that each test starts without any logs from previous ones, which should be possible since rollbacks happen per test. The savepoint initiates around each method right after `setUpClass`, so logs created during a test will also roll back—great!
> 
> Next, I’m working on the test method `_to_string()`, which will convert datetime to a string if it's provided. My first test will be `test_external_json_write_filters_unknown_and_ignored_keys`. 
> 
> I’ll verify the behavior of the `external_json_write` method, checking that it correctly handles fields like `internal_note` and `create_date`, which should be ignored. I’m keeping an eye out for potential issues with duplicate keys, like mapping "id" to "external_id," but it seems okay for this test. I also need to think about updating the cache—or do I? It might be unnecessary!
> 
> **Testing write functionality**
> 
> I’m looking to ensure that during normal writes, if the `external_json_safe_write` isn't enabled, Odoo should raise a `ValueError` when I try to write invalid fields. I think using `assertRaisesRegex` would be better here to check for specific error messages.
> 
> Next, I’ll test the datetime conversion when writing to the record. I’ll create a record and call `external_json_write`, verifying that the created timestamps are properly converted.
> 
> I wonder about the record cache as datetime values are written and if Odoo reloads these correctly from the cache. It seems logical that it should parse the updated values correctly.
> 
> For the date testing, I'll check if a non-UTC date will be accepted and processed appropriately, as I'm curious about how the date parsing handles timezones.
> 
> **Testing datetime validation**
> 
> I'm testing how the system handles invalid datetime inputs during an `external_json_write`. I’ll create a record first with a valid datetime, then try to write with an invalid value while allowing leniency, checking that the original datetime remains unchanged. I’ll also confirm that this invalid attempt logs correctly in the record’s log.
> 
> Next, I’ll check strict validation. If an invalid datetime is provided with `strict_datetime=True`, a `ValidationError` should be raised before any changes are made—so the record's name shouldn't change.
> 
> Lastly, I’ll validate that creating records with unacceptable data raises the proper errors while considering how logs behave with transactions in case of caught exceptions.
> 
> **Testing custom converters and payloads**
> 
> I’m testing how the system handles external JSON writing, particularly concerning partner creation. When I write with the partner name, it should link to an existing partner without creating duplicates, which could cause unintended side effects. I'm cautious about the allowed fields, especially with partner_id.
> 
> Next, I’ll check for issues when mapping duplicate fields. If both "id" and "external_id" are provided, the system should process them correctly without errors, and log any invalid keys properly.
> 
> Lastly, I’ll ensure that sensitive information is masked correctly in the payload logs. I’ll verify that sensitive keys are replaced with "***" and don't expose actual values.
> 
> **Refining test strategies**
> 
> I'm realizing that my tests shouldn't overly depend on JSON formatting, as it may introduce complexity. One potential issue is when I search logs by model and res_id; if multiple logs come from the same test, counting the logs beforehand may be essential to track only the most recent one.
> 
> Now, to run the tests, I should use commands like:
> - For a new setup: `./odoo-bin -d db -i external_json_sync --test-enable --stop-after-init`.
> - For an existing database: `./odoo-bin -d db -u external_json_sync --test-tags /external_json_sync --stop-after-init`.
> 
> I also need to properly cite the Odoo documentation regarding TransactionCase and their recommendations for handling UTC dates.
> 
> **Clarifying testing considerations**
> 
> I need to mention that single dollar signs in the math aren't relevant here. I should consider if the previous mixin uses `_external_json_raise_on_invalid`, not specifically for datetime, but through the strict_datetime parameter. It seems that `_external_json_build_context` incorporates `external_json_raise_on_invalid` as a boolean, which is good.
> 
> I wonder if I should test specific conditions in the final implementation with `@tagged("external_json_sync")`. If I use this tag, the Odoo documentation notes that tag decorators can add or remove inherited tags without affecting the defaults. So using the tag should work well.
> 
> It's important to run it with `--test-tags external_json_sync` and include tests from `tests/__init__.py`, as unregistered modules won't run. Lastly, I need to highlight that when testing an abstract mixin, a concrete model is necessary since AbstractModel doesn’t have an actual table to reference. To avoid any production pollution, I'll conditionally import the test model when the test is enabled.
> 
> **Examining model imports and testing**
> 
> I need to clarify that while using a generic mixin test suite, it requires a dummy model, even though it's common practice to test actual models if they already exist. I should ensure to add a conditional import in `models/__init__.py`.
> 
> When `--test-tags` is used, it implies `--test-enable`, so the config should reflect that setting. If I don’t set it properly, the test model may not register correctly. This situation could lead to orphan tables if the server runs normally after tests. It's fine for a clean CI DB, but I must avoid this in a production database.
> 
> **Evaluating test model placement**
> 
> I’m thinking about whether to place the test model in a separate test module, but that might not be necessary. I wonder if I should consider adding a `.gitignore`, but it seems like I don’t need that right now. Also, I should note that adding tests for issue log access might not be required. It's all about streamlining and ensuring I focus on what’s truly essential for the task at hand!
> 
> **Including test model code**
> 
> I need to provide the exact code for `models/external_json_sync_test_models.py`. This model will only be imported if `odoo.tools.config['test_enable']` is true. The class `ExternalJsonSyncTestModel` inherits from an external JSON sync mixin and defines various fields, including external ID, name, and timestamps. It also includes a method for converting partner IDs, ensuring that even during creation, the converter is effectively called. This setup seems appropriate for testing the functionality I want to support!
> 
> **Testing the external JSON sync mixin**
> 
> I should check if the `fields.Json` type exists because the mixin is automatically allowed, but the test might be lacking. The test class `TestExternalJsonSyncMixin` sets up a test environment and creates a partner. I also have utility methods for creating records and retrieving logs.
> 
> In the `test_safe_write_filters_fields_and_creates_log`, I'm testing how a record handles payloads. It seems good to ensure that `internal_note` is set to false when writing, and that the log captures the correct values, especially around unknown and ignored keys. I’m making sure everything works as expected!
> 
> **Working on test cases**
> 
> I’m confirming that `amount_total` is set up correctly as a float, and moving to the test for unknown fields. For `test_plain_write_still_rejects_unknown_field`, I'm checking if Odoo 18 raises a `ValueError` when trying to write an unknown field. 
> 
> Next, for `test_datetime_fields_are_converted_to_utc`, I want to ensure the timestamps get converted properly based on the source timezone. I’m also considering using `rec.invalidate_recordset()` after the write, but it may not be necessary since Odoo handles conversion automatically. 
> 
> Lastly, for the test checking date handling, I want to ensure no time zone shifts affect the date field. I'm wondering if maybe I should select a time close to midnight to cover edge cases.
> 
> **Detailing test scenarios**
> 
> For the date handling, I’m confirming that the example `2026-01-01T00:30:00+14:00` correctly converts to January 1. This shift should return the correct date without mistakes. In `test_invalid_datetime_is_logged_and_skipped_in_lenient_mode`, I’ll ensure that an invalid datetime value doesn’t affect the record’s name when strict mode is off. 
> 
> However, in strict mode, `test_invalid_datetime_raises_in_strict_mode` will raise a `ValidationError`, so I need to check if there’s no log created.
> 
> For `test_safe_create_filters_and_logs`, I want to see that unknown fields correctly trigger logging. Finally, in `test_empty_create_without_writable_fields_raises`, I’m expecting a `ValidationError` when there are no writable fields available.
> 
> **Sorting through testing details**
> 
> I realized that even if the SQL log is created and the exception is caught, the log will still remain. I wonder if I could assert the presence of the log, even without a `res_id`. For the `test_custom_converter_for_many2one`, I'm confirming that when I write the partner's external name, it correctly maps to the partner without causing an issue, so no logs are needed here.
> 
> In `test_duplicate_mapped_keys_are_logged`, I'll check if writing duplicate keys gives the expected errors and logs the right information about invalid keys. Lastly, for `test_numeric_epoch_milliseconds`, I want to be sure I'm correctly computing the timestamp; using zero should give me a clear conversion to the expected date.
> 
> **Reviewing tests and log masking**
> 
> I realized that since `bool` is a subclass of int, my parse checks for `isinstance(value, bool)` before checking for `int`, which is good. In my test for `external_json_write`, I'm confirming that a zero input correctly translates to the date "1970-01-01 00:00:00." 
> 
> The log masking checks are crucial too. I'm validating that sensitive values, like API tokens, are replaced with "***" in the logs, ensuring security. 
> 
> I need to be cautious about how verbose my final output is when compiling the test suite, balancing thoroughness without overloading with unnecessary details. Lastly, I should mention potential issues with importing models conditionally in `models/__init__.py`, as it might affect table creation.
> 
> **Considering Odoo testing procedures**
> 
> Odoo documentation states that tests are only executed in installed modules, so if I’m working with a clean database, I’ll need to use `-i` for installation and `-u` for updates. I should also include a citation for `--test-tags` syntax.
> 
> It’s worth noting that if one doesn’t want to add test models to production code, creating a separate testing module like `external_json_sync_tests` is cleaner. However, there are potential issues to consider, such as log model access control, where only admin can create logs through the mixin. Additionally, I need to check if `fields.Datetime.to_string(rec.external_created_at)` returns False when the field itself is False. Lastly, I want to warn that conditional imports for test models only load with `--test-enable` or `--test-tags`, otherwise they won't be found.
> 
> **Evaluating Odoo testing structure**
> 
> According to the documentation, the `--test-tags` option implies `--test-enable`, meaning that the testing modules are automatically inspected and imported. I need to decide if I want to include citations in my final output—yes, because I referenced the web and I should place citations after the relevant statements, but the code itself can remain uncited.
> 
> I should mention that Odoo recommends establishing a tests sub-package with test files imported in `tests/__init__.py`. The `TransactionCase` class is ideal for testing business logic, and the `--test-tags` option can specify modules, classes, or methods, enabling tests while also referring to "Datetime stored UTC." 
> 
> Lastly, I need to reflect on subtle issues regarding the use of `models.AbstractModel` with the mixin and its methods. If a model inherits from this mixin, calling `super().write` will refer back to the mixin’s definitions. I must consider how the test models may only load when `test-enable` is active.
> 
> **Considering access issues for test models**
> 
> I need to think about generating the `ir.model.access.csv` for the test model since it has no UI access. When I create the test model, Odoo may still generate an `ir.model` record, but without a menu, the table name will be `external_json_sync_test_model`. 
> 
> It's important to clarify that if `test_enable` is false, the test model won't be present, although the `tests` file will reference it while the tests are running. I might suggest placing the test model in a small addon, `external_json_sync_test`, if conditional imports aren't desired. 
> 
> There's also a potential issue with the `@api.model_create_multi` decorator. It seems that while Odoo’s new API primarily supports lists, it can accept dictionaries too. Our existing code checks if `vals_list` is a dictionary, converting it to a list if needed, but I wonder how Odoo handles this if it wraps it as a list.
> 
> **Evaluating potential issues with testing models**
> 
> I'm considering a potential issue where `self.Model.external_json_create(payload)` returns a recordset of one. This seems fine, but I’m curious about the "normal write unknown field" after inheriting from the mixin. If the context isn’t enabled, calling `super().write(vals)` should raise an invalid exception. 
> 
> Then there's the question of handling invalid datetime values like "not-a-datetime." The `_external_json_parse_datetime` function should raise an exception if it encounters this.
> 
> In lenient mode, it appears that invalid inputs use a generic exception handler, which means no log is created until after. However, in strict mode, the original exception should be raised as a `ValidationError`, aligning with my expected behavior. 
> 
> Finally, in the `test_safe_create_filters_and_logs`, the logging occurs after `super().create`, and since the log method relies on `self.env.context`, the record should still maintain this context. This all checks out since `super().create` returns records with the same environment context. Good to have clarity here!
> 
> **Identifying potential logging issues**
> 
> I'm spotting a potential issue with how `Log.search` handles the domain `("res_ids", "=", str(record.id))`. This works if record IDs are comma-separated, but for multiple writes like "1,2", it might not equal as expected. For single records, it’s fine. There's also a need to consider that logs created with `sudo()` might have `create_uid` as 1.
> 
> Should I test multi-record writes? The mixin logs a single entry for `self.ids` and writes the same values across all records. It could be worthwhile to test with two records, like this:
> 
> ```
> recs = rec1 | rec2
> recs.external_json_write({"name":"Shared","unknown":"x"})
> ```
> Then check the log for both IDs. It’s probably not critical, but including it could be beneficial. The user asked for a coherent set rather than exhaustive details.
> 
> I should also mention that these tests assume your mixin file name and model name match `external.json.sync.mixin` and `external.json.issue.log`; if they've changed, just replace accordingly. I might mention that "these test cases cover nine points." 
> 
> Lastly, I want to ensure I present the code clearly while maintaining CommonMark. It's important to convey that test models shouldn't be defined directly under `tests/`, as they may not get registered. I recommend a conditional import from `models/__init__.py` or a separate addon.
> 
> **Final code considerations**
> 
> I’m laying out the final steps for the code update: first, I need to update `models/__init__.py`, then add a concrete test model, and include `tests/__init__.py` along with a test file. I’ll run the necessary commands, though the code length might be higher, and I want to keep verbosity under control as instructed. 
> 
> While I might not need to adjust `security/ir.model.access.csv` for the test model, I’m wondering if the test environment user isn’t a superuser? I think tests run under `TransactionCase` as a superuser (admin). If there are no ACLs, the superuser bypasses them. Tests probably use `env.uid`, which is likely admin with id=1.
> 
> If access controls are required, I could leverage `.sudo()` in my tests. For instance:
> 
> ```
> cls.Model = cls.env["external.json.sync.test.model"].sudo()
> cls.Log = cls.env["external.json.issue.log"].sudo()
> ```
> Using `.sudo()` ensures I avoid ACL issues, and for model objects, it returns the environment with superuser privileges. This way, partner creation runs smoothly, and no access control is needed since the test records would be created with uid 1.
> 
> **Using sudo for testing**
> 
> I’ve decided to use `.sudo()` when referencing models in my tests. Specifically, I’ll set up:
> 
> ```
> cls.Model = cls.env["external.json.sync.test.model"].sudo()
> cls.Log = cls.env["external.json.issue.log"].sudo()
> cls.Partner = cls.env["res.partner"].sudo()
> ```
> 
> The converter will work with `self.env`, which keeps the context when using `sudo`. It's important to ensure that when comparing `rec.partner_id` with `self.partner`, they both retain their superuser context. 
> 
> I also need to confirm that `record.write` raises an error for any invalid fields, as this behavior should persist even with superuser permissions. For the `external_json_write` method, I’ll note that `**extra_context` can accept keys like `external_json_source`.
> 
> I might want to test "log masking" with an `api_token` to see if unknown keys are logged correctly, and they should include the `res_id`. In `_last_log`, I want to ensure the default order sorts by `create_date desc` and `id desc` in the model; if there are multiple logs with the same date, I’ll check that they sort by `id desc`. 
> 
> In `test_invalid_datetime_is_logged_and_skipped`, the log should only capture invalid records, so I need to focus on that. Finally, for `test_duplicate_mapped_keys`, I should ensure that if the later "external_id" is invalid, the initial valid `external_id` remains intact.
> 
> **Clarifying test setup and log handling**
> 
> In my loop, I note that the `field_sources` get their value from the raw IDs, which is good because it logs any invalid entries. The `super().write(clean_vals)` will be executed afterward.
> 
> For the tests, I'm not including the "external_json_allow_empty_create." However, I might add a test for using `fields.Datetime.to_string` for comparisons. I can define helper methods like:
> 
> ```
> def _dt(self, record, field_name):
>     return fields.Datetime.to_string(record[field_name])
> 
> def _date(self, record, field_name):
>     return fields.Date.to_string(record[field_name])
> ```
> 
> I confirm that `record[field_name]` works within an Odoo recordset, and that's great! For completeness, I'll ensure my test code includes everything needed, starting with setting up the classes and creating a test partner. 
> 
> I must keep in mind whether the `Log` class search finds logs from previous tests. Transaction rollbacks may have cleared them, but during the `setUpClass`, there might not be any logs to find.
> 
> **Examining log handling and test robustness**
> 
> I’m considering whether logs from previous manually executed tests could linger, even when using the same database and module. Generally, a test database starts fresh. To ensure robustness, I think I should modify the `_last_log` to target both the model and `res_ids`. If the same ID is reused, that could be a concern. 
> 
> I could do a baseline record before the operation, but it's probably not necessary. I might want to add a method to search logs related to a specific record.
> 
> Regarding the test "plain_write_still_rejects_unknown_field," I should ensure it handles `ValueError` correctly and check if there's an existing cache issue.
> 
> I've also noted a test to confirm the "Date field is not shifted." I plan on using `external_date`, which should compare against an expected date value like "2026-01-01." I’m pondering if `rec.external_date` could already be a string and if `fields.Date.to_string` accepts that string type without error. It seems like the record read returns a date object, so that’s a good sign.
> 
> **Planning datetime context tests**
> 
> I think the user is looking for tests related to automatic timezone conversion for `write` operations. They might want to evaluate `with_context(external_json_safe_write=True).write`, alongside our existing `external_json_write`.
> 
> I could include a test like this: 
> ```
> def test_context_enabled_write_uses_same_pipeline(self):
>    rec.with_context(external_json_safe_write=True, external_json_source_tz="Asia/Shanghai").write({"createdAt": "...", "unknown": "x"})
> ```
> This should handle external keys and field mapping.
> 
> I also want to cover context modes, so another test might look like this:
> ```
> def test_context_enabled_write_uses_safe_pipeline(self):
>    rec.with_context(...).write({"id":"CTX-1","api_new_field":"x"})
>    self.assertEqual(rec.external_id,"CTX-1")
> ```
> It feels a bit redundant since we're already testing similar functionality. 
> 
> I’ll make sure to consider my test naming conventions with “test_mixin” and include a note for users who have different mixin versions. I believe it would be great to mention that we focus on backend ORM logic while using `TransactionCase`, stressing its clean-up capabilities.
> 
> I also want to cite where it mentions that Odoo's datetime fields store in UTC, maybe avoiding citations in code comments but including them after code statements. Finally, I’ll draft the final document in Chinese, starting with "可行，下面是一套完整 test suite".
> 
> **Clarifying assumptions and code**
> 
> Alright, I want to start by making clear assumptions before diving into the code. I might mention a warning that the test model is for testing only and shouldn’t be registered in production, using `config['test_enable']` as a condition for import. 
> 
> I should highlight that if `--test-tags` is used, it implies that `test-enable` is true according to official docs. My concern is how module tests auto-inspect the tests sub-package when the test model is conditionally loaded.
> 
> When writing the code, I need to include file paths, as potential citations can support the code. For citations, I’ll include something like this:  
> 
> - Mentioning that the official Odoo 18 documentation states Python tests are in the `tests` sub-package, which is imported in `tests/__init__.py`, and that `TransactionCase` is suitable for model logic testing. 
> - Note that datetime fields are stored in UTC. 
> 
> Lastly, if I mention that test methods start with `test_`, I’ll cite that as well. I’ll also think if I need to tag with `@tagged("external_json_sync")`, but the documentation suggests that tags are class decorators, so it may not be necessary.
> 
> **Considering test model conditions**
> 
> I might have a potential issue regarding the conditional import of the test model in `models/__init__.py`. If `test_enable` is false in production, then the test file won’t run. It’s good to note that if the config is false, there won't be any import, which means no `ir.model` record will exist.
> 
> If the module is installed with `test_enable` on, the test model stays in the database. This is fine for a clean test DB, but could leave stray tables in a dev DB, even though the model won't register in a normal run.
> 
> I could suggest using a clean test database and maybe even recommending setting up a separate testing add-on if that’s preferred. It's also important to remember that there may be no `ir.model.access.csv` for the test model, but testing with sudo should still work. 
> 
> The final code might need to include `from odoo import api` in the test model dependencies. Also, computed fields don’t require storage, so that’s acceptable. But regarding the `active` field, there shouldn’t be any test for that.
> 
> **Identifying potential issues**
> 
> I’m noticing a few potential issues I need to address. First, there's the `amount_total` field using a float instead of a monetary type, which could be a concern. Also, when using `fields.Datetime.to_string(record.external_created_at)`, if the value is `False`, it might lead to an invalid test when it should be a string. 
> 
> In the invalid lenient test, when `rec.external_json_write` builds context, the mixin `_external_json_should_raise_invalid` interprets the context value incorrectly. For the strict test, any exceptions raised happen before calling `super.write`, which could lead to confusion since the cache still contains an old value. 
> 
> Another point arises in `test_safe_create_filters_and_logs`: if an unknown field is part of the payload after `external_json_create`, there might be logs created without the necessary context source passed. Finally, in the test for context-enabled writing, if the payload includes only "id" and "api_new_field," it might produce an unknown log that sets `external_id`. It might be worth considering including a "Multi record write test" with log `res_ids`, but I'm unsure right now.
> 
> **Considering testing details**
> 
> I’m thinking about how to include a test for multi-record writing that logs all record IDs. I need to create two records, `rec1` and `rec2`, and then combine them into a record set to test the `external_json_write` method. I'll check that the name updates correctly for both records and search the log to verify that it correctly captures both IDs. 
> 
> Although this all tests multi IDs, it might not be central to my goals, so I'll have to balance what stays in. There’s also a concern regarding equality checks with different prefetches for record sets, but since Odoo handles equality based on model and IDs, that should be fine. 
> 
> To ensure everything runs correctly, I need to use specific command lines for testing. I see that according to the Odoo documentation, the `--test-tags` option supports structured naming. Lastly, if using Docker, I may need to adapt my approach a bit, and I will flag that the test files don’t need to be added to the manifest data.
> 
> **Preparing testing considerations**
> 
> I need to consider that if the test model is imported conditionally, there could be issues if I'm using an existing database where the module is installed without `test_enable`. I should run the `-u` command to rebuild the model registry and create the necessary tables.
> 
> I’m also reflecting on whether to separate the test model into its own addon, though it will still depend on the base and the `external_json_sync` module. 
> 
> Additionally, if logs from an invalid create persist after an expected exception, I can trust that the transaction rollback will clean up at the method's end. 
> 
> It’s essential that my mixin appropriately uses `external_json_write`, incorporating the right context variables. Lastly, I would like a citation noting that tests not imported from `tests/__init__` will not run, but I need to ensure everything remains concise enough.
> 
> **Listing test scenarios and code setup**
> 
> I want to note that the test suite covers ten scenarios, which include the following: default write not touched, safe write filter, context write, record creation, datetime handling in UTC, date without shifting, invalid lenient/strict tests, many2one converter, handling duplicate mapped keys, and raw payload masking.
> 
> Next, I should present the full `models/__init__.py` code block, starting with importing `external_json_sync` along with the configuration import from Odoo tools, but noting that some prefer to list `config` first. 
> 
> In `models/external_json_sync_test_models.py`, I'll define the `ExternalJsonSyncTestModel`, including the relevant description and inheritance from the mixin. I'll mention that since the test model isn't loaded in production, no access CSV is required because tests run with sudo. If UI access is needed, it's worth adding ACLs.
> 
> **Coding test initialization**
> 
> I need to write the code for `tests/__init__.py`. It should simply import the test module for the external JSON sync mixin, which looks like this:
> 
> ```python
> from . import test_external_json_sync_mixin
> ```
> 
> Next, I have to create the full code for `tests/test_external_json_sync_mixin.py`. I want to make sure I write this carefully so that it includes all necessary components and follows best practices. I'll focus on structuring the tests properly to ensure they cover all required scenarios effectively.
> 
> **Writing the test file code**
> 
> I need to develop a test file for the external JSON sync mixin in Odoo. The test code includes importing necessary modules and defining the `TestExternalJsonSyncMixin` class, which inherits from `TransactionCase`.
> 
> This class will have methods for setting up the class environment, creating records, fetching logs, and handling date and datetime formats. I see that I should ensure that handling the `record[field_name]` dynamically works, especially when the recordset length is 1. Keeping all of this in mind, I’ll finalize the structure and logic.
> 
> **Developing test methods**
> 
> I'm setting up some test methods, starting with one to check that attempting to write an unknown field to a record raises a ValueError. I want to verify that the record's name remains unchanged.
> 
> Next, in the safe write test, I'll filter out unknown fields to ensure they are ignored properly. I'll need to check if `rec.internal_note` is false versus an empty string, so I’ll use `self.assertFalse(rec.internal_note)`.
> 
> In the context-enabled write test, I should ensure that the record's cache is updated. Since updating in a different context may not refresh the original record, I might use `rec.invalidate_recordset()`.
> 
> **Refining testing methods**
> 
> I’m considering how the cache with `self.Model.browse(rec.id).external_id` might behave since different recordsets could share the same environment. It feels like invalidation is the better route here. Rather than adding a new method like `rec.flush_recordset()`, I can read directly from a context record by using `ctx_rec`.
> 
> For the `test_safe_create_filters_and_logs`, I'll be checking that the log captures unknown keys upon creation. In the `test_empty_create_without_writable_fields_raises`, I want to verify that trying to create a record with unknown fields raises a ValidationError. It's essential to ensure logs capture this correctly, even if an exception doesn't trigger a rollback.
> 
> **Testing validation and date handling**
> 
> I’m reflecting on how the `ValidationError` can be raised after a log is created, ensuring the cursor transaction remains intact.
> 
> For the `test_datetime_fields_are_converted_to_utc`, I need to verify that after writing with "createdAt," if there are no unknown fields, the log isn’t used.
> 
> With `test_invalid_datetime_is_logged_and_skipped_in_lenient_mode`, I'm creating a record and writing an invalid datetime. It’s essential to see if `log.invalid_payload` captures the erroneous input. Lastly, in the strict mode test, I want to confirm that an invalid datetime raises a ValidationError and that the record’s name remains unchanged.
> 
> **Testing various behavior with external JSON writes**
> 
> I’m considering the `test_custom_converter_can_write_many2one`, where I need to verify that writing with `partnerExternalName` correctly sets the `partner_id`.
> 
> In `test_duplicate_mapped_keys_are_logged_and_first_value_is_kept`, I want to ensure that only the first value remains when duplicates are logged, and check for relevant entries in the log.
> 
> For `test_numeric_epoch_can_be_enabled_by_context`, writing a zero timestamp should give me the correct datetime.
> 
> Lastly, in `test_raw_payload_masks_sensitive_unknown_keys`, I need to check that sensitive keys like `api_token` are masked in the log, ensuring security practices are followed.
> 
> **Clarifying the source context in tests**
> 
> I see a potential issue with the `source` context in the safe write filters test. I need to verify that the log shows the correct values for `source` and `external_ref`. It's good that I can use `record.external_json_write` with `extra_context` keys like `external_json_source` and `external_json_external_ref`. 
> 
> Also, for the Odoo configuration, I should check whether the `test_enable` key exists before using it, which could help avoid issues when tests run without the test enable flag. 
> 
> I’ll need to clarify in my final notes that tests should avoid importing the test model directly into `tests/__init__.py` to ensure the model registry functions correctly.

可行。下面是一套**针对你上一版 `external.json.sync.mixin` 的 Odoo 18 后端测试用例**，覆盖：

1. 普通 `write()` 仍然保持 Odoo 原生行为；
2. `external_json_write()` 安全过滤未知字段；
3. 已存在但不允许外部写入的字段会被忽略并记录日志；
4. `field_map` 字段映射；
5. `Datetime` 自动转 UTC；
6. `Date` 不做 UTC 偏移；
7. 非法 Datetime 在宽松模式下记录日志并跳过；
8. 非法 Datetime 在严格模式下抛错；
9. `external_json_create()` 安全创建；
10. 自定义字段转换器，例如 `Many2one`；
11. 重复映射字段日志；
12. 敏感字段日志脱敏。

Odoo 18 官方推荐 Python 测试放到模块的 `tests` 子包中，测试文件以 `test_` 开头，并从 `tests/__init__.py` 导入；模型业务逻辑测试适合使用 `TransactionCase`。另外，`--test-tags` 会隐式启用 `--test-enable`。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html?utm_source=openai))  
因为你的 mixin 重点处理 `Datetime`，这里也按 Odoo ORM 的规则测试：`Datetime` 字段在数据库中按 UTC 存储。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html?utm_source=openai))

---

# 1. 修改 `models/__init__.py`

为了测试抽象模型，需要一个**具体测试模型**。不建议在生产环境注册这个测试模型，所以可以只在 `test_enable` 开启时导入。

```python
# -*- coding: utf-8 -*-

from odoo.tools import config

from . import external_json_sync

# 仅测试环境注册测试模型
if config.get("test_enable"):
    from . import external_json_sync_test_models
```

---

# 2. 新增测试专用模型

文件：

```text
external_json_sync/models/external_json_sync_test_models.py
```

内容：

```python
# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ExternalJsonSyncTestModel(models.Model):
    """
    仅用于 external.json.sync.mixin 的测试。

    注意：
    - 该模型只在 test_enable 时导入；
    - 生产环境不会注册；
    - 测试中使用 sudo()，因此不额外提供 ACL。
    """

    _name = "external.json.sync.test.model"
    _description = "External JSON Sync Mixin Test Model"
    _inherit = ["external.json.sync.mixin"]

    _external_json_allowed_fields = {
        "external_id",
        "name",
        "amount_total",
        "active",
        "state",
        "external_date",
        "external_created_at",
        "external_updated_at",
        "partner_id",
    }

    _external_json_field_map = {
        "id": "external_id",
        "createdAt": "external_created_at",
        "updatedAt": "external_updated_at",
        "partnerExternalName": "partner_id",
    }

    _external_json_source_tz = "Asia/Shanghai"

    external_id = fields.Char(index=True)
    name = fields.Char()
    amount_total = fields.Float()
    active = fields.Boolean(default=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )

    # 存在，但不在 _external_json_allowed_fields 中，用于测试 ignored field
    internal_note = fields.Text()

    external_date = fields.Date()
    external_created_at = fields.Datetime()
    external_updated_at = fields.Datetime()

    partner_id = fields.Many2one("res.partner")

    # 计算字段，无 inverse，用于测试不适合外部直接写入的字段
    computed_value = fields.Char(compute="_compute_computed_value")

    @api.depends("name")
    def _compute_computed_value(self):
        for record in self:
            record.computed_value = "%s-computed" % (record.name or "")

    def _external_json_convert_partner_id(self, value):
        """
        测试自定义字段转换器。

        外部传入 partnerExternalName，例如：
            {"partnerExternalName": "ABC Customer"}

        转换成 Odoo partner_id。
        """
        if not value:
            return False

        partner = self.env["res.partner"].sudo().search(
            [
                ("name", "=", value),
            ],
            limit=1,
        )

        if not partner:
            partner = self.env["res.partner"].sudo().create(
                {
                    "name": value,
                }
            )

        return partner.id
```

---

# 3. 新增 `tests/__init__.py`

文件：

```text
external_json_sync/tests/__init__.py
```

内容：

```python
# -*- coding: utf-8 -*-

from . import test_external_json_sync_mixin
```

---

# 4. 新增测试用例文件

文件：

```text
external_json_sync/tests/test_external_json_sync_mixin.py
```

内容：

```python
# -*- coding: utf-8 -*-

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("external_json_sync")
class TestExternalJsonSyncMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Model = cls.env["external.json.sync.test.model"].sudo()
        cls.Log = cls.env["external.json.issue.log"].sudo()
        cls.Partner = cls.env["res.partner"].sudo()

        cls.partner = cls.Partner.create(
            {
                "name": "External JSON Test Partner",
            }
        )

    def _create_record(self, **vals):
        default_vals = {
            "name": "Before",
            "external_id": "BEFORE",
            "amount_total": 1.0,
        }
        default_vals.update(vals)
        return self.Model.create(default_vals)

    def _last_log(self, record=None, res_ids=None):
        domain = [
            ("model_name", "=", self.Model._name),
        ]

        if record is not None:
            domain.append(("res_ids", "=", str(record.id)))
        elif res_ids is not None:
            domain.append(("res_ids", "=", res_ids))

        log = self.Log.search(domain, order="id desc", limit=1)
        self.assertTrue(log, "Expected an external JSON issue log.")
        return log

    def _dt_string(self, record, field_name):
        value = record[field_name]
        return fields.Datetime.to_string(value) if value else False

    def _date_string(self, record, field_name):
        value = record[field_name]
        return fields.Date.to_string(value) if value else False

    def test_plain_write_still_rejects_unknown_field(self):
        """
        没有开启 external_json_safe_write 时，write() 应保持 Odoo 原生行为。
        未知字段应该直接报错，而不是被静默过滤。
        """
        record = self._create_record()

        with self.assertRaises(ValueError):
            record.write(
                {
                    "api_new_field": "boom",
                }
            )

        self.assertEqual(record.name, "Before")

    def test_safe_write_filters_unknown_and_ignored_fields(self):
        """
        external_json_write 应该：
        - 写入允许字段；
        - 映射 id -> external_id；
        - 跳过未知字段；
        - 跳过已存在但不允许外部写入的字段；
        - 创建日志。
        """
        record = self._create_record()

        payload = {
            "id": "EXT-100",
            "name": "After",
            "amount_total": 99.5,
            "api_new_field": "new value from API",
            "internal_note": "should not be written",
            "create_date": "2026-06-05 00:00:00",
        }

        result = record.external_json_write(
            payload,
            source_tz="Asia/Shanghai",
            external_json_source="unit_test",
            external_json_external_ref="EXT-100",
        )

        self.assertTrue(result)
        self.assertEqual(record.external_id, "EXT-100")
        self.assertEqual(record.name, "After")
        self.assertEqual(record.amount_total, 99.5)

        # internal_note 是模型字段，但不在白名单中，因此不能被外部 JSON 写入
        self.assertFalse(record.internal_note)

        log = self._last_log(record)
        self.assertEqual(log.operation, "write")
        self.assertEqual(log.source, "unit_test")
        self.assertEqual(log.external_ref, "EXT-100")

        self.assertIn("api_new_field", log.unknown_keys or "")
        self.assertIn("internal_note", log.ignored_keys or "")
        self.assertIn("create_date", log.ignored_keys or "")

    def test_context_enabled_write_uses_same_pipeline(self):
        """
        除了 external_json_write()，直接用 context 开启安全写入也应该生效。
        """
        record = self._create_record()

        safe_record = record.with_context(
            external_json_safe_write=True,
            external_json_source_tz="Asia/Shanghai",
        )

        safe_record.write(
            {
                "id": "CTX-001",
                "api_new_field": "ignored",
            }
        )

        self.assertEqual(safe_record.external_id, "CTX-001")

        log = self._last_log(record)
        self.assertIn("api_new_field", log.unknown_keys or "")

    def test_datetime_fields_are_converted_to_utc(self):
        """
        Datetime 字段应该自动转换为 UTC 后写入。

        Asia/Shanghai:
            2026-06-05 12:30:00 +08:00
        转 UTC:
            2026-06-05 04:30:00
        """
        record = self._create_record()

        record.external_json_write(
            {
                "createdAt": "2026-06-05 12:30:00",
                "updatedAt": "2026-06-05T15:00:00+08:00",
            },
            source_tz="Asia/Shanghai",
        )

        self.assertEqual(
            self._dt_string(record, "external_created_at"),
            "2026-06-05 04:30:00",
        )
        self.assertEqual(
            self._dt_string(record, "external_updated_at"),
            "2026-06-05 07:00:00",
        )

        # 带 Z 的 ISO8601 时间应该被识别为 UTC，不应再次偏移
        record.external_json_write(
            {
                "updatedAt": "2026-06-05T04:30:00Z",
            },
            source_tz="Asia/Shanghai",
        )

        self.assertEqual(
            self._dt_string(record, "external_updated_at"),
            "2026-06-05 04:30:00",
        )

    def test_date_field_is_not_shifted_to_utc(self):
        """
        Date 字段没有时区语义，不应该做 UTC 偏移。

        如果错误地把 2026-01-01T00:30:00+14:00 转成 UTC 再取日期，
        可能会变成 2025-12-31。

        正确行为：仍然记录外部传入日期 2026-01-01。
        """
        record = self._create_record()

        record.external_json_write(
            {
                "external_date": "2026-01-01T00:30:00+14:00",
            },
            source_tz="Asia/Shanghai",
        )

        self.assertEqual(
            self._date_string(record, "external_date"),
            "2026-01-01",
        )

    def test_invalid_datetime_is_logged_and_skipped_in_lenient_mode(self):
        """
        宽松模式下：
        - 非法 Datetime 字段应该被跳过；
        - 其他合法字段继续写入；
        - invalid_keys / invalid_payload 写日志。
        """
        record = self._create_record(
            external_created_at="2026-01-01 00:00:00",
        )

        before_datetime = self._dt_string(record, "external_created_at")

        record.external_json_write(
            {
                "name": "After Invalid Datetime",
                "createdAt": "not-a-datetime",
            },
            strict_datetime=False,
        )

        self.assertEqual(record.name, "After Invalid Datetime")

        # 非法 Datetime 不应该覆盖原值
        self.assertEqual(
            self._dt_string(record, "external_created_at"),
            before_datetime,
        )

        log = self._last_log(record)
        self.assertIn("createdAt", log.invalid_keys or "")
        self.assertIn("not-a-datetime", log.invalid_payload or "")

    def test_invalid_datetime_raises_in_strict_mode_and_does_not_write(self):
        """
        严格模式下：
        - 非法 Datetime 应该抛 ValidationError；
        - 因为在 super().write() 前就抛错，所以其他字段也不应写入。
        """
        record = self._create_record(name="Before Strict")

        with self.assertRaises(ValidationError):
            record.external_json_write(
                {
                    "name": "After Strict",
                    "createdAt": "not-a-datetime",
                },
                strict_datetime=True,
            )

        self.assertEqual(record.name, "Before Strict")

    def test_safe_create_filters_and_logs(self):
        """
        external_json_create 应该同样支持：
        - 字段映射；
        - Datetime UTC 转换；
        - 未知字段日志。
        """
        record = self.Model.external_json_create(
            {
                "id": "EXT-CREATE-001",
                "name": "Created By External JSON",
                "createdAt": "2026-06-05T04:30:00Z",
                "unknown_on_create": "ignored",
            },
            source_tz="Asia/Shanghai",
            external_json_source="unit_test_create",
            external_json_external_ref="EXT-CREATE-001",
        )

        self.assertEqual(record.external_id, "EXT-CREATE-001")
        self.assertEqual(record.name, "Created By External JSON")
        self.assertEqual(
            self._dt_string(record, "external_created_at"),
            "2026-06-05 04:30:00",
        )

        log = self._last_log(record)
        self.assertEqual(log.operation, "create")
        self.assertEqual(log.source, "unit_test_create")
        self.assertEqual(log.external_ref, "EXT-CREATE-001")
        self.assertIn("unknown_on_create", log.unknown_keys or "")

    def test_safe_create_without_writable_fields_raises(self):
        """
        默认情况下，如果 create payload 完全没有可写字段，应该抛错。
        """
        with self.assertRaises(ValidationError):
            self.Model.external_json_create(
                {
                    "unknown_only": "value",
                }
            )

        log = self._last_log(res_ids=False)
        self.assertEqual(log.operation, "create")
        self.assertIn("unknown_only", log.unknown_keys or "")

    def test_custom_converter_can_write_many2one(self):
        """
        测试自定义字段转换器：

            partnerExternalName -> partner_id
        """
        record = self._create_record()

        record.external_json_write(
            {
                "partnerExternalName": self.partner.name,
            }
        )

        self.assertEqual(record.partner_id.id, self.partner.id)

    def test_duplicate_mapped_keys_are_logged_and_first_value_is_kept(self):
        """
        id 和 external_id 都映射到 external_id 时，应检测重复映射。

        当前 mixin 逻辑：
        - 第一个值写入；
        - 第二个重复映射字段写入 invalid 日志。
        """
        record = self._create_record()

        record.external_json_write(
            {
                "id": "EXT-FIRST",
                "external_id": "EXT-SECOND",
            }
        )

        self.assertEqual(record.external_id, "EXT-FIRST")

        log = self._last_log(record)
        self.assertIn("external_id", log.invalid_keys or "")
        self.assertIn("duplicate external keys", log.invalid_payload or "")

    def test_numeric_epoch_can_be_enabled_by_context(self):
        """
        如果开启 epoch_unit，数字时间戳应该可以被转换。

        0 seconds epoch -> 1970-01-01 00:00:00 UTC
        """
        record = self._create_record()

        record.external_json_write(
            {
                "createdAt": 0,
            },
            epoch_unit="seconds",
        )

        self.assertEqual(
            self._dt_string(record, "external_created_at"),
            "1970-01-01 00:00:00",
        )

    def test_raw_payload_masks_sensitive_unknown_keys(self):
        """
        日志中的 token / password / secret 等敏感字段应该脱敏。
        """
        record = self._create_record()
        secret_value = "super-secret-token-value"

        record.external_json_write(
            {
                "name": "Masked Payload",
                "api_token": secret_value,
            }
        )

        log = self._last_log(record)

        self.assertIn("api_token", log.unknown_keys or "")
        self.assertIn("***", log.raw_payload or "")
        self.assertNotIn(secret_value, log.raw_payload or "")
        self.assertNotIn(secret_value, log.unknown_payload or "")
```

---

# 5. 运行测试

首次安装模块并运行测试：

```bash
./odoo-bin \
  -d odoo18_test \
  -i external_json_sync \
  --test-enable \
  --stop-after-init
```

如果模块已经安装过，建议用 `-u` 更新模块。因为测试模型是 `test_enable` 下条件导入的，如果之前不是在测试模式下安装的，直接跑测试可能找不到 `external.json.sync.test.model`。

```bash
./odoo-bin \
  -d odoo18_test \
  -u external_json_sync \
  --test-tags /external_json_sync \
  --stop-after-init
```

只运行这个测试类：

```bash
./odoo-bin \
  -d odoo18_test \
  -u external_json_sync \
  --test-tags /external_json_sync:TestExternalJsonSyncMixin \
  --stop-after-init
```

只运行某个测试方法：

```bash
./odoo-bin \
  -d odoo18_test \
  -u external_json_sync \
  --test-tags /external_json_sync:TestExternalJsonSyncMixin.test_datetime_fields_are_converted_to_utc \
  --stop-after-init
```

Odoo 18 的 `--test-tags` 支持按模块、类、方法筛选测试；并且如果使用 `--test-tags`，不需要额外再写 `--test-enable`。([odoo.com](https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html?utm_source=openai))

---

# 6. 一个小建议

如果你不希望在主模块里放测试模型，也可以新建一个单独测试模块，例如：

```text
external_json_sync_test/
```

然后让它依赖：

```python
"depends": ["external_json_sync"]
```

把 `ExternalJsonSyncTestModel` 放到这个测试模块中。这样主模块更干净，CI 时安装两个模块即可。  
不过对大多数内部开发场景，上面这种 `config.get("test_enable")` 条件导入测试模型的方式已经够用了。

---
Learn more:
1. [Testing Odoo — Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html?utm_source=openai)
2. [ORM API — Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html?utm_source=openai)