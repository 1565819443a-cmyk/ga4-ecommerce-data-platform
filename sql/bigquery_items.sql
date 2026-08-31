SELECT
  PARSE_DATE('%Y%m%d', event_date) AS event_date,
  TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
  event_name,
  user_pseudo_id,
  ecommerce.transaction_id,
  item.item_id,
  item.item_name,
  item.item_brand,
  item.item_category,
  item.price,
  item.quantity,
  item.item_revenue
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, UNNEST(items) AS item
WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date

