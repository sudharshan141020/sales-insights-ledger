const CURRENCY_HINTS = ['sale', 'revenue', 'price', 'cost', 'amount', 'fare', 'profit', 'value', 'income', 'pay', 'earning'];

function looksLikeCurrency(columnName) {
  if (!columnName) return false;
  const n = columnName.toLowerCase();
  return CURRENCY_HINTS.some((k) => n.includes(k));
}

function formatMetric(n, columnName) {
  if (n === undefined || n === null) return '—';
  const prefix = looksLikeCurrency(columnName) ? '$' : '';
  if (Math.abs(n) >= 1_000_000) return `${prefix}${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${prefix}${(n / 1_000).toFixed(1)}K`;
  return `${prefix}${n.toFixed(2)}`;
}

function formatPct(n) {
  if (n === undefined || n === null) return '—';
  return `${n.toFixed(1)}%`;
}

function formatInt(n) {
  if (n === undefined || n === null) return '—';
  return n.toLocaleString('en-US');
}

export default function KpiStrip({ kpis, mapping = {} }) {
  const metricName = mapping.revenue || 'metric';
  const profitName = mapping.profit;

  const cards = [
    // Generic — present for any dataset, sales or not
    { label: 'Records', value: formatInt(kpis.row_count) },
    { label: 'Columns', value: formatInt(kpis.column_count) },
    { label: 'Data completeness', value: formatPct(kpis.data_completeness_pct) },

    // Domain-specific — only show when the underlying data actually supports them
    { label: `Total ${metricName}`, value: formatMetric(kpis.total_revenue, metricName) },
    {
      label: `Total ${profitName || 'profit'}`,
      value: formatMetric(kpis.total_profit, profitName),
      accent: kpis.total_profit < 0 ? 'red' : 'teal',
    },
    {
      label: `${profitName || 'Profit'} margin`,
      value: formatPct(kpis.overall_profit_margin_pct),
      accent: kpis.overall_profit_margin_pct < 0 ? 'red' : null,
    },
    { label: `Avg ${metricName} per record`, value: formatMetric(kpis.avg_order_value, metricName) },
    { label: mapping.customer ? `Unique ${mapping.customer}` : 'Unique customers', value: formatInt(kpis.unique_customers) },
  ].filter((c) => c.value !== '—');

  return (
    <div className="kpi-strip">
      {cards.map((c) => (
        <div key={c.label} className="kpi-card">
          <span className="kpi-label">{c.label}</span>
          <span className={`kpi-value mono ${c.accent ? `kpi-${c.accent}` : ''}`}>{c.value}</span>
        </div>
      ))}
    </div>
  );
}
