from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ga4_platform.sql import render_extract_sql


MAX_BYTES_BILLED = 20_000_000_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_query(client: Any, sql: str, job_config: Any, output: Path) -> dict[str, Any]:
    """Run one bounded query and stream Arrow batches to a single Parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from google.cloud import bigquery_storage

    job = client.query(sql, job_config=job_config)
    rows = job.result(page_size=50_000)
    row_count = 0
    writer = None
    storage_client = bigquery_storage.BigQueryReadClient()
    try:
        for batch in rows.to_arrow_iterable(
            bqstorage_client=storage_client,
            max_queue_size=1,
            max_stream_count=1,
        ):
            table = pa.Table.from_batches([batch])
            if writer is None:
                writer = pq.ParquetWriter(output, table.schema, compression="zstd")
            writer.write_table(table)
            row_count += table.num_rows
    finally:
        if writer is not None:
            writer.close()
        close = getattr(storage_client, "close", None)
        if close is not None:
            close()

    if writer is None:
        raise RuntimeError(f"BigQuery query returned no rows; job_id={job.job_id}")

    return {
        "job_id": job.job_id,
        "location": job.location,
        "cache_hit": bool(job.cache_hit),
        "total_bytes_processed": int(job.total_bytes_processed or 0),
        "total_bytes_billed": int(job.total_bytes_billed or 0),
        "slot_millis": int(job.slot_millis or 0),
        "rows": row_count,
        "output": output.as_posix(),
        "file_bytes": output.stat().st_size,
        "sha256": _sha256(output),
    }


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
    job_config = bigquery.QueryJobConfig(use_query_cache=True, maximum_bytes_billed=MAX_BYTES_BILLED)
    events_result = _stream_query(client, render_extract_sql(start, end), job_config, output)
    items_sql = (Path(__file__).resolve().parents[1] / "sql/bigquery_items.sql").read_text(encoding="utf-8")
    items_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("start_date", "STRING", start), bigquery.ScalarQueryParameter("end_date", "STRING", end)],
        use_query_cache=True, maximum_bytes_billed=MAX_BYTES_BILLED,
    )
    items_output = output.with_name("ga4_items.parquet")
    items_result = _stream_query(client, items_sql, items_config, items_output)
    manifest = {
        "source": "bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*",
        "query_project": project,
        "date_range": {"start": start, "end": end},
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_bytes_billed_per_query": MAX_BYTES_BILLED,
        "events": events_result,
        "items": items_result,
    }
    manifest_path = Path(__file__).resolve().parents[1] / "artifacts/extraction_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"official BigQuery export: {events_result['rows']:,} events -> {output}; "
        f"{items_result['rows']:,} item rows -> {items_output}; manifest -> {manifest_path}"
    )


if __name__ == "__main__": main()
