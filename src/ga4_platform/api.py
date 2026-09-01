from __future__ import annotations

import json

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings

app = FastAPI(title="GA4 Ecommerce Analytics & Data Platform", version="1.0.0")
ROOT = Settings.load().root
app.mount("/dashboard", StaticFiles(directory=ROOT / "dashboard"), name="dashboard-assets")


def query(sql: str) -> list[dict]:
    settings = Settings.load()
    if not settings.database.exists():
        raise HTTPException(503, "尚未构建官方 GA4 导出")
    con = duckdb.connect(str(settings.database), read_only=True)
    try:
        frame = con.execute(sql).fetchdf()
        return json.loads(frame.to_json(orient="records", date_format="iso"))
    finally:
        con.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "source": "Google official GA4 BigQuery sample"}


@app.get("/api/summary")
def summary():
    rows = query("""SELECT count(*) events,count(DISTINCT user_pseudo_id) users,
      count(DISTINCT session_id) sessions,
      count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='first_visit') new_users,
      count(DISTINCT user_pseudo_id) FILTER (WHERE event_name='purchase') purchasers,
      count(DISTINCT transaction_id) FILTER (WHERE event_name='purchase') orders,
      round(sum(purchase_revenue),2) revenue,
      round(100.0*count(DISTINCT session_id) FILTER (WHERE event_name='purchase')/nullif(count(DISTINCT session_id),0),2) session_conversion_pct,
      min(event_date) start_date,max(event_date) end_date,
      (select data_mode from ads.build_metadata) data_mode FROM dwd.events""")
    return rows[0]


@app.get("/api/trend")
def trend():
    return query("SELECT * FROM ads.daily_kpi ORDER BY event_date")


@app.get("/api/funnel")
def funnel():
    return query("SELECT * FROM ads.funnel ORDER BY step_order")


@app.get("/api/retention")
def retention():
    return query("SELECT * FROM ads.cohort_retention ORDER BY cohort_week,week_number")


@app.get("/api/channels")
def channels():
    return query("SELECT * FROM ads.channel_summary ORDER BY revenue DESC")


@app.get("/api/segments")
def segments():
    return query("SELECT segment,count(*) users,round(avg(revenue),2) avg_revenue FROM ads.user_value GROUP BY segment ORDER BY users DESC")


@app.get("/api/anomalies")
def anomalies():
    return query("SELECT * FROM ads.daily_anomaly WHERE is_anomaly ORDER BY event_date")


@app.get("/api/products")
def products():
    return query("SELECT * FROM ads.product_summary ORDER BY item_revenue DESC LIMIT 50")


@app.get("/")
def dashboard():
    return RedirectResponse("/dashboard/index.html")
