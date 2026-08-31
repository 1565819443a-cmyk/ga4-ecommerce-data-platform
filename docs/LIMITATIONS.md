# 数据限制

- 官方样例为脱敏数据，只覆盖 2020-11-01 至 2021-01-31，部分字段是 `<Other>`、空值或占位值，内部一致性有限。
- 该数据不能与 Google Analytics Demo Account 直接对账。
- 当前 `traffic_source` 是首次用户获取来源，不等同于完整的会话级 last-click 归因。
- user_pseudo_id 受设备与 Cookie 影响，不是稳定的跨设备真实用户。
- 本地 fixture 仅用于自动化测试，绝不能作为真实分析结论。

