import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const CURRENCY_HINTS = ['sale', 'revenue', 'price', 'cost', 'amount', 'fare', 'profit', 'value', 'income', 'pay', 'earning'];
function looksLikeCurrency(name) {
  if (!name) return false;
  const n = name.toLowerCase();
  return CURRENCY_HINTS.some((k) => n.includes(k));
}

function CustomTooltip({ active, payload, metricName }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const prefix = looksLikeCurrency(metricName) ? '$' : '';
  return (
    <div className="chart-tooltip">
      <p className="tooltip-label mono">{d.label}</p>
      <p className="mono" style={{ color: 'var(--teal)' }}>
        {metricName}: {prefix}{d.revenue.toLocaleString('en-US', { maximumFractionDigits: 0 })}
      </p>
      {d.margin_pct !== undefined && d.margin_pct !== null && (
        <p className="mono" style={{ color: d.margin_pct < 0 ? 'var(--red)' : 'var(--amber)' }}>
          Margin: {d.margin_pct.toFixed(1)}%
        </p>
      )}
    </div>
  );
}

export default function BreakdownChart({ title, data, tickNum, metricName = 'Value', hideHeader = false }) {
  if (!data?.length) return null;

  const chart = (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border-soft)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-body)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
        <YAxis stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} />
        <Tooltip content={<CustomTooltip metricName={metricName} />} cursor={{ fill: 'var(--surface-raised)' }} />
        <Bar dataKey="revenue" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.margin_pct !== undefined && entry.margin_pct < 0 ? 'var(--red)' : 'var(--teal)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );

  if (hideHeader) return chart;

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="tick">{tickNum}</span>
        <h3>{title}</h3>
      </div>
      {chart}
    </div>
  );
}
