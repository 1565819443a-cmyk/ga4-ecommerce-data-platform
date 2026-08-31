from __future__ import annotations

import json

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .config import Settings

app = FastAPI(title="GA4 Ecommerce Analytics & Data Platform", version="1.0.0")


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
    rows = query("SELECT sum(events) events,max(users) max_daily_users,sum(orders) orders,round(sum(revenue),2) revenue,min(event_date) start_date,max(event_date) end_date,(select data_mode from ads.build_metadata) data_mode FROM ads.daily_kpi")
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


@app.get("/")
def dashboard():
    return FileResponse(Settings.load().root / "dashboard/index.html")
