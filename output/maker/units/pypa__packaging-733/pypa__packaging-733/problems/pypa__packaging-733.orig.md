# Inconsistent (and broken) behavior for Optional Metadata values

Currently the `Metadata` class is inconsistent and in some cases broken in how it handles optional metadata values that don't currently have a value.

I added a quick test to the test suite that looks like:

```python
    .mark.parametrize(
        "field_name",
        sorted(metadata._RAW_TO_EMAIL_MAPPING.keys() - metadata._REQUIRED_ATTRS),
    )
    def test_can_access_omitted_optional_value(self, field_name):
        # Create a minimal metadata that has only the required fields.
        meta = metadata.Metadata.from_raw(
            {
                "metadata_version": metadata._VALID_METADATA_VERSIONS[-1],
                "name": "foo",
                "version": "1.0",
            }
        )

        # Accessing any optional field should be fine, and should return the
        # "zero" value for that field.
        value = getattr(meta, field_name)
        if isinstance(value, str):
            assert value == ""
        elif isinstance(value, list):
            assert value == []
        elif isinstance(value, dict):
            assert value == {}
        else:
            assert False, "unknown type"
```

And I ended up with 3 errors:

```
======================================================= FAILURES =======================================================
____________________ TestMetadata.test_can_access_omitted_optional_value[description_content_type] _____________________

self = <tests.test_metadata.TestMetadata object at 0x7f2fd1242090>, field_name = 'description_content_type'

    .mark.parametrize(
        "field_name",
        sorted(metadata._RAW_TO_EMAIL_MAPPING.keys() - metadata._REQUIRED_ATTRS),
    )
    def test_can_access_omitted_optional_value(self, field_name):
        # Create a minimal metadata that has only the required fields.
        meta = metadata.Metadata.from_raw(
            {
                "metadata_version": metadata._VALID_METADATA_VERSIONS[-1],
                "name": "foo",