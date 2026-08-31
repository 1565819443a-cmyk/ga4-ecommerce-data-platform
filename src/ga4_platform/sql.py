from __future__ import annotations

from pathlib import Path


def render_extract_sql(start_date: str = "20201101", end_date: str = "20210131") -> str:
    if not (start_date.isdigit() and end_date.isdigit() and len(start_date) == len(end_date) == 8):
        raise ValueError("日期必须为 YYYYMMDD")
    if start_date > end_date or start_date < "20201101" or end_date > "20210131":
        raise ValueError("日期必须位于官方样例 20201101-20210131")
    template = (Path(__file__).resolve().parents[2] / "sql" / "bigquery_extract.sql").read_text(encoding="utf-8")
    return template.replace("{{ start_date }}", start_date).replace("{{ end_date }}", end_date)

