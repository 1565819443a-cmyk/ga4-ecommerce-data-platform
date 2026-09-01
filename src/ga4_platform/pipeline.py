from __future__ import annotations

import json

import duckdb

from .config import Settings


def build(settings: Settings | None = None) -> dict:
    s = settings or Settings.load()
    if not s.source_file.exists():
        raise FileNotFoundError(f"缺少 BigQuery 官方导出：{s.source_file}")
    s.database.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(s.database))
    con.execute("PRAGMA threads=4")
    for schema in ["ods", "dwd", "dws", "ads"]:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    reader = "read_csv_auto(?, header=true)" if s.source_file.suffix == ".csv" else "read_parquet(?)"
    con.execute("DROP TABLE IF EXISTS ods.events")
    con.execute(f"CREATE TABLE ods.events AS SELECT * FROM {reader}", [str(s.source_file)])
    con.execute("DROP TABLE IF EXISTS dwd.events")
    con.execute("""
      CREATE TABLE dwd.events AS
      SELECT cast(event_date AS DATE) event_date, cast(event_timestamp AS TIMESTAMP) event_timestamp,
        event_name, user_pseudo_id, session_id,
        coalesce(source,'(direct)') source, coalesce(medium,'(none)') medium,
        coalesce(campaign,'(not set)') campaign, transaction_id,
        greatest(coalesce(try_cast(purchase_revenue AS DOUBLE),0),0) purchase_revenue,
        device_category, country
      FROM ods.events WHERE user_pseudo_id IS NOT NULL AND event_name IS NOT NULL
      QUALIFY row_number() OVER (PARTITION BY event_timestamp,event_name,user_pseudo_id,coalesce(transaction_id,'') ORDER BY event_timestamp)=1
    """)
    items_file = s.source_file.parent / ("items_fixture.csv" if s.fixture_mode else "ga4_items.parquet")
    con.execute("DROP TABLE IF EXISTS dwd.items")
    if items_file.exists():
        items_reader = "read_csv_auto(?, header=true)" if items_file.suffix == ".csv" else "read_parquet(?)"
        con.execute(f"""
          CREATE TABLE dwd.items AS SELECT cast(event_date AS DATE) event_date,
            cast(event_timestamp AS TIMESTAMP) event_timestamp,event_name,user_pseudo_id,transaction_id,
            item_id,item_name,item_brand,item_category,try_cast(price AS DOUBLE) price,
            try_cast(quantity AS BIGINT) quantity,greatest(coalesce(try_cast(item_revenue AS DOUBLE),0),0) item_revenue
          FROM {items_reader}
        """, [str(items_file)])
    else:
        con.execute("""CREATE TABLE dwd.items(event_date DATE,event_timestamp TIMESTAMP,event_name VARCHAR,user_pseudo_id VARCHAR,transaction_id VARCHAR,item_id VARCHAR,item_name VARCHAR,item_brand VARCHAR,item_category VARCHAR,price DOUBLE,quantity BIGINT,item_revenue DOUBLE)""")
    con.execute("DROP TABLE IF EXISTS dws.session_summary")
    con.execute("""
      CREATE TABLE dws.session_summary AS
      SELECT session_id, user_pseudo_id, min(event_timestamp) session_start,
        any_value(source) source, any_value(medium) medium, any_value(campaign) campaign,
        count(*) events, max((event_name='purchase')::INT) purchased,
        sum(purchase_revenue) revenue
      FROM dwd.events WHERE session_id IS NOT NULL GROUP BY session_id,user_pseudo_id
    """)
    con.execute("DROP TABLE IF EXISTS ads.daily_kpi")
    con.execute("""
      CREATE TABLE ads.daily_kpi AS
      SELECT event_date, count(*) events, count(DISTINCT user_pseudo_id) users,
        count(DISTINCT session_id) sessions,
        count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='first_visit') new_users,
        count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='purchase') purchasers,
        count(DISTINCT transaction_id) FILTER (WHERE event_name='purchase') orders,
        round(sum(purchase_revenue),2) revenue
      FROM dwd.events GROUP BY event_date ORDER BY event_date
    """)
    con.execute("DROP TABLE IF EXISTS ads.funnel")
    con.execute("""
      CREATE TABLE ads.funnel AS WITH user_steps AS (
        SELECT user_pseudo_id,
          min(event_timestamp) FILTER (WHERE event_name='page_view') t1,
          min(event_timestamp) FILTER (WHERE event_name='view_item') t2,
          min(event_timestamp) FILTER (WHERE event_name='add_to_cart') t3,
          min(event_timestamp) FILTER (WHERE event_name='begin_checkout') t4,
          min(event_timestamp) FILTER (WHERE event_name='purchase') t5
        FROM dwd.events GROUP BY user_pseudo_id)
      SELECT * FROM (VALUES
        (1,'浏览', (SELECT count(*) FROM user_steps WHERE t1 IS NOT NULL)),
        (2,'查看商品',(SELECT count(*) FROM user_steps WHERE t2>=t1)),
        (3,'加购',(SELECT count(*) FROM user_steps WHERE t3>=t2 AND t2>=t1)),
        (4,'开始结账',(SELECT count(*) FROM user_steps WHERE t4>=t3 AND t3>=t2 AND t2>=t1)),
        (5,'购买',(SELECT count(*) FROM user_steps WHERE t5>=t4 AND t4>=t3 AND t3>=t2 AND t2>=t1))
      ) t(step_order,step,users)
    """)
    con.execute("DROP TABLE IF EXISTS ads.cohort_retention")
    con.execute("""
      CREATE TABLE ads.cohort_retention AS WITH activity AS (
        SELECT user_pseudo_id, date_trunc('week',event_date)::DATE active_week FROM dwd.events GROUP BY 1,2),
      cohort AS (SELECT user_pseudo_id,min(active_week) cohort_week FROM activity GROUP BY 1)
      SELECT cohort_week, date_diff('week',cohort_week,active_week) week_number,
        count(DISTINCT activity.user_pseudo_id) retained_users,
        first_value(count(DISTINCT activity.user_pseudo_id)) OVER (PARTITION BY cohort_week ORDER BY week_number) cohort_size,
        round(100.0*count(DISTINCT activity.user_pseudo_id)/first_value(count(DISTINCT activity.user_pseudo_id)) OVER (PARTITION BY cohort_week ORDER BY week_number),2) retention_rate_pct
      FROM activity JOIN cohort USING(user_pseudo_id) GROUP BY cohort_week,week_number
    """)
    con.execute("DROP TABLE IF EXISTS ads.channel_summary")
    con.execute("""
      CREATE TABLE ads.channel_summary AS
      SELECT source,medium,count(DISTINCT session_id) sessions,count(DISTINCT user_pseudo_id) users,
        count(DISTINCT transaction_id) FILTER (WHERE event_name='purchase') orders,
        round(sum(purchase_revenue),2) revenue,
        round(100.0*count(DISTINCT session_id) FILTER (WHERE event_name='purchase')/nullif(count(DISTINCT session_id),0),2) session_conversion_pct
      FROM dwd.events GROUP BY source,medium ORDER BY revenue DESC
    """)
    con.execute("DROP TABLE IF EXISTS ads.user_value")
    con.execute("""
      CREATE TABLE ads.user_value AS WITH base AS (
        SELECT user_pseudo_id,max(event_date) last_active,count(DISTINCT session_id) sessions,
          count(DISTINCT transaction_id) FILTER (WHERE event_name='purchase') orders,
          round(sum(purchase_revenue),2) revenue
        FROM dwd.events GROUP BY user_pseudo_id), scored AS (
        SELECT *,date_diff('day',last_active,(SELECT max(last_active) FROM base)) recency_days,
          ntile(5) over(order by date_diff('day',last_active,(SELECT max(last_active) FROM base)) desc) r_score,
          ntile(5) over(order by orders) f_score,ntile(5) over(order by revenue) m_score FROM base)
      SELECT *,CASE WHEN r_score>=4 AND f_score>=4 AND m_score>=4 THEN '高价值'
        WHEN r_score>=4 AND orders=0 THEN '活跃未购' WHEN r_score<=2 AND orders>0 THEN '待唤回'
        WHEN orders>0 THEN '已购用户' ELSE '普通访客' END segment FROM scored
    """)
    con.execute("DROP TABLE IF EXISTS ads.daily_anomaly")
    con.execute("""
      CREATE TABLE ads.daily_anomaly AS WITH stats AS (
        SELECT *,avg(users) OVER (ORDER BY event_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) avg_7d,
          stddev_samp(users) OVER (ORDER BY event_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) sd_7d
        FROM ads.daily_kpi)
      SELECT *,CASE WHEN sd_7d>0 THEN round((users-avg_7d)/sd_7d,2) END user_zscore,
        CASE WHEN abs((users-avg_7d)/nullif(sd_7d,0))>=3 THEN true ELSE false END is_anomaly
      FROM stats
    """)
    con.execute("DROP TABLE IF EXISTS ads.build_metadata")
    con.execute("CREATE TABLE ads.build_metadata AS SELECT ? data_mode,current_timestamp built_at", ["fixture" if s.fixture_mode else "official_bigquery_export"])
    con.execute("DROP TABLE IF EXISTS ads.product_summary")
    con.execute("""
      CREATE TABLE ads.product_summary AS SELECT coalesce(item_id,'(missing)') item_id,
        coalesce(item_name,'(not set)') item_name,coalesce(item_category,'(not set)') item_category,
        count(*) item_event_rows,sum(coalesce(quantity,0)) quantity,round(sum(item_revenue),2) item_revenue
      FROM dwd.items GROUP BY item_id,item_name,item_category ORDER BY item_revenue DESC
    """)
    platform_dir = s.root / ("data/platform_fixture" if s.fixture_mode else "data/platform")
    platform_dir.mkdir(parents=True, exist_ok=True)
    for table, file in [("dwd.events","ga4_events"),("dwd.items","ga4_items"),("ads.daily_kpi","ga4_daily_kpi"),("ads.funnel","ga4_funnel"),("ads.channel_summary","ga4_channel_summary"),("ads.user_value","ga4_user_value"),("ads.product_summary","ga4_product_summary")]:
        path = (platform_dir / f"{file}.parquet").as_posix().replace("'", "''")
        con.execute(f"COPY {table} TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    result = {"mode": "fixture" if s.fixture_mode else "official_bigquery_export", "events": con.execute("select count(*) from dwd.events").fetchone()[0], "item_rows": con.execute("select count(*) from dwd.items").fetchone()[0], "users": con.execute("select count(distinct user_pseudo_id) from dwd.events").fetchone()[0], "days": con.execute("select count(distinct event_date) from dwd.events").fetchone()[0], "orders": con.execute("select count(distinct transaction_id) from dwd.events where event_name='purchase'").fetchone()[0], "revenue": con.execute("select round(sum(purchase_revenue),2) from dwd.events").fetchone()[0]}
    (s.root / "artifacts").mkdir(exist_ok=True)
    target = "fixture_pipeline_summary.json" if s.fixture_mode else "pipeline_summary.json"
    (s.root / "artifacts" / target).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    return result
