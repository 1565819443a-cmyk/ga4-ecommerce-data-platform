# 数据与结论限制

- 官方样例经过混淆，只覆盖 2020-11-01 至 2021-01-31，部分字段出现 `<Other>`、`(data deleted)`、空值或占位值，不能代表当前真实商户。
- 正式质量检查发现 23 条 purchase 缺少 transaction_id、448 条 purchase 商品记录的 quantity 为空或非正；它们以 warning 保留，订单指标只统计非空 transaction_id。
- 数据不能与 Google Analytics Demo Account 直接对账；GA4 UI 还可能使用不同身份空间、归因、时区、建模和阈值。
- `traffic_source` 是用户首次获取来源，不是完整的会话级 last-click 归因，因此渠道结论只按本项目口径解释。
- `user_pseudo_id` 受设备和 Cookie 影响，不是稳定的跨设备真实用户或会员 ID。
- 顺序漏斗使用每位用户各步骤首次时间，适合统一比较，但不能替代路径级、会话级或实验分析。
- 异常检测使用前 7 日滚动均值与样本标准差，三处异常仅提示进一步排查，不证明活动、故障或季节性原因。
- 本地 fixture 只验证代码边界，独立输出到 `data/platform_fixture/`，绝不能作为真实分析结论。
- DuckDB 本地实现适合作品展示和分析交付；生产环境还需要调度、分区写入、权限、数据目录、告警与 SLA。
