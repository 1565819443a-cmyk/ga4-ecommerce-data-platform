-- 官方源：bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*
-- 一次展开 event_params，items 在独立 SQL 中展开，防止事件与商品笛卡尔积。
SELECT
  PARSE_DATE('%Y%m%d', event_date) AS event_date,
  TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
  event_name,
  user_pseudo_id,
  CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key='ga_session_id') AS STRING)) AS session_id,
  COALESCE(traffic_source.source, '(direct)') AS source,
  COALESCE(traffic_source.medium, '(none)') AS medium,
  COALESCE(traffic_source.name, '(not set)') AS campaign,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key='page_location') AS page_location,
  ecommerce.transaction_id,
  ecommerce.purchase_revenue AS purchase_revenue,
  ecommerce.total_item_quantity AS total_item_quantity,
  device.category AS device_category,
  geo.country AS country,
  EXISTS(SELECT 1 FROM UNNEST(event_params) WHERE key='entrances' AND value.int_value=1) AS is_entrance
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '{{ start_date }}' AND '{{ end_date }}'
  AND user_pseudo_id IS NOT NULL

