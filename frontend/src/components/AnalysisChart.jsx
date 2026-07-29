import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const CURRENCY_HINTS = ['sale', 'revenue', 'price', 'cost', 'amount', 'fare', 'profit', 'value', 'income', 'pay', 'earning', 'billing', 'salary'];
function looksLikeCurrency(name) {
  if (!name) return false;
  const n = name.toLowerCase();
  return CURRENCY_HINTS.some((k) => n.includes(k));
}

function formatAxisValue(v) {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(0)}K`;
  return v;
}

function CustomTooltip({ active, payload, label, valueLabel, isCurrency }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="chart-tooltip">
      <p className="tooltip-label mono">{label}</p>
      <p className="mono" style={{ color: 'var(--teal)' }}>
        {valueLabel}: {isCurrency ? '$' : ''}{v.toLocaleString('en-US', { maximumFractionDigits: 1 })}
      </p>
    </div>
  );
}

export default function AnalysisChart({ analysis }) {
  if (!analysis?.data?.length) return null;

  const isTrend = analysis.type === 'trend';
  const isCurrency = looksLikeCurrency(analysis.metric_column) && analysis.type !== 'distribution_count';
  const valueLabel = analysis.type === 'distribution_count' ? 'Count'
    : analysis.aggregation === 'avg' ? `Avg ${analysis.metric_column || ''}`
    : analysis.metric_column || 'Value';

  if (isTrend) {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={analysis.data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--border-soft)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
          <YAxis stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={formatAxisValue} />
          <Tooltip content={<CustomTooltip valueLabel={valueLabel} isCurrency={isCurrency} />} cursor={{ stroke: 'var(--border)' }} />
          <Line type="monotone" dataKey="value" stroke="var(--teal)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={analysis.data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border-soft)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={11} fontFamily="var(--font-body)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} angle={-20} textAnchor="end" height={50} />
        <YAxis stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={formatAxisValue} />
        <Tooltip content={<CustomTooltip valueLabel={valueLabel} isCurrency={isCurrency} />} cursor={{ fill: 'var(--surface-raised)' }} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {analysis.data.map((_, i) => <Cell key={i} fill="var(--teal)" />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
