# 数据字典

| 字段 | 含义 | 口径 |
|---|---|---|
| event_date | 事件日期 | `PARSE_DATE('%Y%m%d', event_date)` |
| event_timestamp | 事件时间 | `TIMESTAMP_MICROS`，用于漏斗顺序 |
| user_pseudo_id | 匿名用户标识 | 未配置 user_id 时采用官方建议口径 |
| session_id | 会话键 | `user_pseudo_id + ga_session_id`，避免跨用户碰撞 |
| event_name | GA4 事件类型 | page_view/view_item/add_to_cart/begin_checkout/purchase 等 |
| transaction_id | 交易编号 | 订单去重键 |
| purchase_revenue | 购买收入 | GA4 ecommerce.purchase_revenue，负值质量检查 |
| source/medium/campaign | 首次用户流量来源 | 来自 traffic_source，限制见 README |
| item_* | 商品属性 | `UNNEST(items)` 后独立商品粒度表 |

原始完整定义以 [GA4 BigQuery Export schema](https://support.google.com/analytics/answer/7029846) 为准。

