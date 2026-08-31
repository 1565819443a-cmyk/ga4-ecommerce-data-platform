# 指标字典

唯一配置源为 `configs/metrics.yaml`。关键差异：用户数使用 `user_pseudo_id`；会话键必须拼接匿名用户；订单按非空 transaction_id 去重；收入使用 purchase 事件的 ecommerce.purchase_revenue；漏斗要求同一用户各步骤首次时间单调递增，不能只比较各事件总人数。

