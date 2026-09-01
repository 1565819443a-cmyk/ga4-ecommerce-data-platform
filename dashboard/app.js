const formatNumber = (value, digits = 0) => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value || 0);
const api = (path) => fetch(path).then((response) => {
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
});

Promise.all([
  api('/api/summary'), api('/api/trend'), api('/api/funnel'), api('/api/channels'),
  api('/api/retention'), api('/api/products'), api('/api/anomalies'),
]).then(([summary, trend, funnel, channels, retention, products, anomalies]) => {
  if (summary.data_mode === 'fixture') {
    document.querySelector('#mode').innerHTML = '<span class="badge">TEST FIXTURE · 仅用于自动化验证，不代表真实业务结论</span>';
  }
  const cardData = [
    ['用户', formatNumber(summary.users), '匿名 user_pseudo_id'],
    ['会话', formatNumber(summary.sessions), '用户 + ga_session_id'],
    ['新用户', formatNumber(summary.new_users), '发生 first_visit'],
    ['订单', formatNumber(summary.orders), '去重 transaction_id'],
    ['收入', `$${formatNumber(summary.revenue)}`, 'purchase_revenue'],
    ['会话转化率', `${formatNumber(summary.session_conversion_pct, 2)}%`, '购买会话 / 全部会话'],
  ];
  document.querySelector('#cards').innerHTML = cardData.map(([label, value, note]) => `<article class="card"><div class="card-label">${label}</div><div class="value">${value}</div><div class="card-sub">${note}</div></article>`).join('');

  echarts.init(document.querySelector('#trend')).setOption({
    tooltip: { trigger: 'axis' }, legend: { data: ['用户', '会话'], right: 8 },
    grid: { left: 48, right: 20, top: 52, bottom: 42 },
    xAxis: { type: 'category', boundaryGap: false, data: trend.map((x) => x.event_date.slice(0, 10)), axisLabel: { interval: 14 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf1f5' } } },
    series: [
      { name: '用户', type: 'line', smooth: true, showSymbol: false, data: trend.map((x) => x.users), lineStyle: { color: '#07866f', width: 3 }, areaStyle: { color: '#d8f1eb' } },
      { name: '会话', type: 'line', smooth: true, showSymbol: false, data: trend.map((x) => x.sessions), lineStyle: { color: '#405cf5', width: 2 } },
    ],
  });
  echarts.init(document.querySelector('#funnel')).setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 用户' },
    series: [{ type: 'funnel', top: 30, bottom: 10, minSize: '18%', maxSize: '92%', gap: 3, itemStyle: { borderColor: '#fff', borderWidth: 2 }, color: ['#0b806e', '#19a58c', '#50bea9', '#8bd4c6', '#c4ebe3'], data: funnel.map((x) => ({ name: x.step, value: x.users })), label: { formatter: ({ name, value }) => `${name}  ${formatNumber(value)}`, color: '#233249' } }],
  });
  const topChannels = channels.slice(0, 7).reverse();
  echarts.init(document.querySelector('#channels')).setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, grid: { left: 138, right: 28, top: 25, bottom: 30 },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf1f5' } } },
    yAxis: { type: 'category', data: topChannels.map((x) => `${x.source} / ${x.medium}`), axisLabel: { width: 128, overflow: 'truncate' } },
    series: [{ type: 'bar', data: topChannels.map((x) => x.revenue), itemStyle: { color: '#405cf5', borderRadius: [0, 5, 5, 0] } }],
  });
  const weekRows = retention.filter((x) => x.week_number <= 8);
  const cohorts = [...new Set(weekRows.map((x) => x.cohort_week.slice(0, 10)))].slice(-8);
  const weighted = cohorts.map((cohort) => {
    const values = weekRows.filter((x) => x.cohort_week.slice(0, 10) === cohort && x.week_number === 1);
    return values.length ? values[0].retention_rate_pct : null;
  });
  echarts.init(document.querySelector('#retention')).setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${v}%` }, grid: { left: 48, right: 22, top: 34, bottom: 56 },
    xAxis: { type: 'category', data: cohorts, axisLabel: { rotate: 28 } }, yAxis: { type: 'value', name: '次周留存 %', splitLine: { lineStyle: { color: '#edf1f5' } } },
    series: [{ type: 'bar', data: weighted, itemStyle: { color: '#14a88a', borderRadius: [5, 5, 0, 0] } }],
  });
  document.querySelector('#products').innerHTML = products.slice(0, 8).map((x) => `<tr><td>${x.item_name}</td><td>${x.item_category}</td><td>$${formatNumber(x.item_revenue)}</td></tr>`).join('');
  document.querySelector('#anomalies').innerHTML = anomalies.length
    ? anomalies.map((x) => `<div class="anomaly"><div><strong>${x.event_date.slice(0, 10)}</strong><div class="card-sub">${formatNumber(x.users)} 位用户</div></div><div class="z">Z = ${x.user_zscore}</div></div>`).join('')
    : '<div class="anomaly">未发现阈值以上异常</div>';
}).catch((error) => {
  document.querySelector('#mode').innerHTML = `<span class="badge">加载失败：${error.message}</span>`;
});
