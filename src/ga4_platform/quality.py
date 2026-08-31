from __future__ import annotations

import json

import duckdb

from .config import Settings


RULES = [
    ("事件非空", "select count(*) from dwd.events having count(*)=0"),
    ("时间范围", "select count(*) from dwd.events where event_date not between date '2020-11-01' and date '2021-01-31'"),
    ("用户标识非空", "select count(*) from dwd.events where user_pseudo_id is null"),
    ("事件名非空", "select count(*) from dwd.events where event_name is null"),
    ("事件去重", "select count(*)-count(distinct (event_timestamp,event_name,user_pseudo_id,coalesce(transaction_id,''))) from dwd.events"),
    ("收入非负", "select count(*) from dwd.events where purchase_revenue<0"),
    ("购买收入口径", "select count(*) from dwd.events where purchase_revenue>0 and event_name<>'purchase'"),
    ("日汇总行数", "select abs((select count(*) from ads.daily_kpi)-(select count(distinct event_date) from dwd.events))"),
    ("日事件对账", "select abs((select sum(events) from ads.daily_kpi)-(select count(*) from dwd.events))"),
    ("漏斗单调", "select count(*) from (select users,lag(users) over(order by step_order) prev from ads.funnel) where prev is not null and users>prev"),
    ("队列0周完整", "select count(*) from ads.cohort_retention where week_number=0 and retention_rate_pct<>100"),
    ("订单ID非空", "select count(*) from dwd.events where event_name='purchase' and transaction_id is null"),
]


def run(settings: Settings) -> dict:
    con = duckdb.connect(str(settings.database), read_only=True)
    checks=[]
    for name, sql in RULES:
        value=con.execute(sql).fetchone(); failures=int(value[0] or 0) if value else 0
        checks.append({"name":name,"failures":failures,"status":"passed" if failures==0 else "failed"})
    con.close()
    result={"mode":"fixture" if settings.fixture_mode else "official_bigquery_export","rules":len(checks),"passed":sum(x["status"]=="passed" for x in checks),"failed":sum(x["status"]=="failed" for x in checks),"checks":checks}
    target="fixture_quality_report.json" if settings.fixture_mode else "quality_report.json"
    (settings.root/"artifacts"/target).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

