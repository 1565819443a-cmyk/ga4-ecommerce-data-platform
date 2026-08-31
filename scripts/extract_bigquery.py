from __future__ import annotations

import os
from pathlib import Path

from ga4_platform.sql import render_extract_sql


def main() -> None:
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise SystemExit("请先 pip install -r requirements.txt") from exc
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise SystemExit("请设置 GOOGLE_CLOUD_PROJECT；BigQuery Sandbox/免费额度即可")
    start, end = os.getenv("GA4_START_DATE", "20201101"), os.getenv("GA4_END_DATE", "20210131")
    output = Path(os.getenv("GA4_EXPORT_URI", "data/raw/ga4_events.parquet"))
    output.parent.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=project)
    job_config = bigquery.QueryJobConfig(use_query_cache=True, maximum_bytes_billed=20_000_000_000)
    frame = client.query(render_extract_sql(start, end), job_config=job_config).result().to_dataframe(create_bqstorage_client=True)
    frame.to_parquet(output, index=False)
    items_sql = (Path(__file__).resolve().parents[1] / "sql/bigquery_items.sql").read_text(encoding="utf-8")
    items_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("start_date", "STRING", start), bigquery.ScalarQueryParameter("end_date", "STRING", end)],
        use_query_cache=True, maximum_bytes_billed=20_000_000_000,
    )
    items = client.query(items_sql, job_config=items_config).result().to_dataframe(create_bqstorage_client=True)
    items_output = output.with_name("ga4_items.parquet")
    items.to_parquet(items_output, index=False)
    print(f"official BigQuery export: {len(frame):,} events -> {output}; {len(items):,} item rows -> {items_output}")


if __name__ == "__main__": main()
