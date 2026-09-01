from __future__ import annotations

import json

import duckdb

from .config import Settings


RULES = [
    ("事件非空", "critical", "select count(*) from dwd.events having count(*)=0"),
    ("时间范围", "critical", "select count(*) from dwd.events where event_date not between date '2020-11-01' and date '2021-01-31'"),
    ("数据覆盖结束日", "critical", "select (max(event_date)<>date '2021-01-31')::int from dwd.events"),
    ("用户标识非空", "critical", "select count(*) from dwd.events where user_pseudo_id is null"),
    ("事件名非空", "critical", "select count(*) from dwd.events where event_name is null"),
    ("事件去重", "critical", "select count(*)-count(distinct (event_timestamp,event_name,user_pseudo_id,coalesce(transaction_id,''))) from dwd.events"),
    ("收入非负", "critical", "select count(*) from dwd.events where purchase_revenue<0"),
    ("购买收入口径", "critical", "select count(*) from dwd.events where purchase_revenue>0 and event_name<>'purchase'"),
    ("日汇总行数", "critical", "select abs((select count(*) from ads.daily_kpi)-(select count(distinct event_date) from dwd.events))"),
    ("日事件对账", "critical", "select abs((select sum(events) from ads.daily_kpi)-(select count(*) from dwd.events))"),
    ("日收入对账", "critical", "select (abs((select sum(revenue) from ads.daily_kpi)-(select sum(purchase_revenue) from dwd.events))>0.01)::int"),
    ("会话主题行数对账", "critical", "select abs((select count(*) from dws.session_summary)-(select count(distinct session_id) from dwd.events))"),
    ("用户分层行数对账", "critical", "select abs((select count(*) from ads.user_value)-(select count(distinct user_pseudo_id) from dwd.events))"),
    ("漏斗单调", "critical", "select count(*) from (select users,lag(users) over(order by step_order) prev from ads.funnel) where prev is not null and users>prev"),
    ("队列0周完整", "critical", "select count(*) from ads.cohort_retention where week_number=0 and retention_rate_pct<>100"),
    ("商品展开非空", "critical", "select count(*) from dwd.items having count(*)=0"),
    ("订单ID非空", "warning", "select count(*) from dwd.events where event_name='purchase' and transaction_id is null"),
    ("购买商品数量为正", "warning", "select count(*) from dwd.items where event_name='purchase' and (quantity is null or quantity<=0)"),
    ("商品收入非负", "critical", "select count(*) from dwd.items where item_revenue<0"),
]


def run(settings: Settings) -> dict:
    con = duckdb.connect(str(settings.database), read_only=True)
    checks=[]
    for name, severity, sql in RULES:
        if settings.fixture_mode and name == "数据覆盖结束日":
            checks.append({"name":name,"severity":severity,"failures":0,"status":"not_applicable","reason":"fixture 仅覆盖 5 个测试日期"})
            continue
        value=con.execute(sql).fetchone(); failures=int(value[0] or 0) if value else 0
        status = "passed" if failures == 0 else ("warning" if severity == "warning" else "failed")
        checks.append({"name":name,"severity":severity,"failures":failures,"status":status})
    con.close()
    result={"mode":"fixture" if settings.fixture_mode else "official_bigquery_export","rules":len(checks),"passed":sum(x["status"]=="passed" for x in checks),"warnings":sum(x["status"]=="warning" for x in checks),"failed":sum(x["status"]=="failed" for x in checks),"not_applicable":sum(x["status"]=="not_applicable" for x in checks),"checks":checks}
    target="fixture_quality_report.json" if settings.fixture_mode else "quality_report.json"
    (settings.root/"artifacts"/target).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
