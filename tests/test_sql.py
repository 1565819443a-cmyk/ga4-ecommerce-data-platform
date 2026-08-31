import pytest

from ga4_platform.sql import render_extract_sql


def test_extract_sql_uses_official_table_and_nested_fields():
    sql = render_extract_sql()
    assert "bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*" in sql
    assert "UNNEST(event_params)" in sql
    assert "ecommerce.purchase_revenue" in sql
    assert "20201101" in sql and "20210131" in sql


@pytest.mark.parametrize("start,end", [("20200101", "20201102"), ("20210131", "20201101"), ("bad", "20210131")])
def test_extract_sql_rejects_invalid_ranges(start, end):
    with pytest.raises(ValueError):
        render_extract_sql(start, end)

