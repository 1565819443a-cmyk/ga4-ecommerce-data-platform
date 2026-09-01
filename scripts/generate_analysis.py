from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/processed/ga4.duckdb"


def rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    frame = connection.execute(sql).fetchdf()
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def main() -> None:
    connection = duckdb.connect(str(DATABASE), read_only=True)
    try:
        summary = rows(
            connection,
            """
            SELECT count(*) events,
              count(DISTINCT user_pseudo_id) users,
              count(DISTINCT session_id) sessions,
              count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='first_visit') new_users,
              count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='purchase') purchasers,
              count(DISTINCT transaction_id) FILTER (WHERE event_name='purchase') orders,
              round(sum(purchase_revenue),2) revenue,
              round(100.0*count(DISTINCT session_id) FILTER (WHERE event_name='purchase')
                /nullif(count(DISTINCT session_id),0),2) session_conversion_pct,
              min(event_date) start_date,max(event_date) end_date
            FROM dwd.events
            """,
        )[0]
        retention = rows(
            connection,
            """
            SELECT week_number,sum(retained_users) retained_users,sum(cohort_size) eligible_users,
              round(100.0*sum(retained_users)/nullif(sum(cohort_size),0),2) weighted_retention_pct
            FROM ads.cohort_retention WHERE week_number BETWEEN 0 AND 4
            GROUP BY week_number ORDER BY week_number
            """,
        )
        result = {
            "source": "Google official GA4 BigQuery Sample Ecommerce",
            "summary": summary,
            "funnel": rows(connection, "SELECT step_order,step,users FROM ads.funnel ORDER BY step_order"),
            "retention_weeks_0_to_4": retention,
            "top_channels": rows(
                connection,
                "SELECT source,medium,sessions,users,orders,revenue,session_conversion_pct FROM ads.channel_summary ORDER BY revenue DESC LIMIT 10",
            ),
            "top_products": rows(
                connection,
                "SELECT item_id,item_name,item_category,quantity,item_revenue FROM ads.product_summary ORDER BY item_revenue DESC LIMIT 10",
            ),
            "anomaly_dates": rows(
                connection,
                "SELECT event_date,users,user_zscore FROM ads.daily_anomaly WHERE is_anomaly ORDER BY event_date",
            ),
        }
    finally:
        connection.close()
    output = ROOT / "artifacts/analysis_summary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
