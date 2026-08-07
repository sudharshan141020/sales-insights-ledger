import { Fragment } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, ScatterChart, Scatter,
  Treemap, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';

const CURRENCY_HINTS = ['sale', 'revenue', 'price', 'cost', 'amount', 'fare', 'profit', 'value', 'income', 'pay', 'earning', 'billing', 'salary'];
function looksLikeCurrency(name) {
  if (!name) return false;
  return CURRENCY_HINTS.some((k) => name.toLowerCase().includes(k));
}

function formatAxisValue(v) {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(0)}K`;
  return v;
}

const PALETTE = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)', 'var(--chart-6)', 'var(--chart-7)', 'var(--chart-8)'];

function ChartTooltip({ active, payload, label, valueLabel, isCurrency }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="chart-tooltip">
      <p className="tooltip-label mono">{label}</p>
      <p className="mono" style={{ color: 'var(--teal)' }}>
        {valueLabel}: {isCurrency ? '$' : ''}{typeof v === 'number' ? v.toLocaleString('en-US', { maximumFractionDigits: 1 }) : v}
      </p>
    </div>
  );
}

function LineView({ analysis, isCurrency }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={analysis.data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border-soft)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
        <YAxis stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={formatAxisValue} />
        <Tooltip content={<ChartTooltip valueLabel={analysis.metric_column || 'Value'} isCurrency={isCurrency} />} cursor={{ stroke: 'var(--border)' }} />
        <Line type="monotone" dataKey="value" stroke="var(--teal)" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function BarView({ analysis, isCurrency, horizontal }) {
  const valueLabel = analysis.type === 'distribution_count' ? 'Count'
    : analysis.aggregation === 'avg' ? `Avg ${analysis.metric_column || ''}`
    : analysis.metric_column || 'Value';
  return (
    <ResponsiveContainer width="100%" height={Math.max(260, analysis.data.length * (horizontal ? 28 : 0))}>
      <BarChart
        data={analysis.data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 10, right: 24, left: horizontal ? 40 : 0, bottom: horizontal ? 0 : 40 }}
      >
        <CartesianGrid stroke="var(--border-soft)" horizontal={!horizontal} vertical={horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={formatAxisValue} />
            <YAxis type="category" dataKey="label" stroke="var(--text-faint)" fontSize={11} fontFamily="var(--font-body)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} width={110} />
          </>
        ) : (
          <>
            <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={11} fontFamily="var(--font-body)" tickLine={false} axisLine={{ stroke: 'var(--border)' }} angle={-20} textAnchor="end" height={50} />
            <YAxis stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} tickFormatter={formatAxisValue} />
          </>
        )}
        <Tooltip content={<ChartTooltip valueLabel={valueLabel} isCurrency={isCurrency} />} cursor={{ fill: 'var(--surface-raised)' }} />
        <Bar dataKey="value" radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]}>
          {analysis.data.map((_, i) => <Cell key={i} fill="var(--teal)" />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function DonutTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  const total = p.payload.__total || 1;
  const pct = ((p.value / total) * 100).toFixed(1);
  return (
    <div className="chart-tooltip">
      <p className="tooltip-label mono">{p.name}</p>
      <p className="mono" style={{ color: p.payload.fill }}>
        {p.value.toLocaleString()} ({pct}%)
      </p>
    </div>
  );
}

function DonutView({ analysis }) {
  const total = analysis.data.reduce((sum, d) => sum + d.value, 0);
  const dataWithTotal = analysis.data.map((d) => ({ ...d, __total: total }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie data={dataWithTotal} dataKey="value" nameKey="label" innerRadius={55} outerRadius={90} paddingAngle={2}>
          {dataWithTotal.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip content={<DonutTooltip />} />
        <Legend
          layout="horizontal"
          verticalAlign="bottom"
          align="center"
          wrapperStyle={{ fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--text-muted)', paddingTop: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function ScatterView({ analysis }) {
  const hasGroups = analysis.data.some((d) => d.group !== undefined);
  const groups = hasGroups ? [...new Set(analysis.data.map((d) => d.group))] : [];
  const groupColor = (g) => PALETTE[groups.indexOf(g) % PALETTE.length];

  return (
    <ResponsiveContainer width="100%" height={hasGroups ? 350 : 300}>
      <ScatterChart margin={{ top: hasGroups ? 30 : 10, right: 24, left: 16, bottom: 40 }}>
        <CartesianGrid stroke="var(--border-soft)" />
        <XAxis type="number" dataKey="x" name={analysis.x_label} stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickFormatter={formatAxisValue}
          label={{ value: analysis.x_label, position: 'bottom', offset: 18, fill: 'var(--text-muted)', fontSize: 12.5, fontFamily: 'var(--font-body)' }} />
        <YAxis type="number" dataKey="y" name={analysis.y_label} stroke="var(--text-faint)" fontSize={12} fontFamily="var(--font-mono)" tickFormatter={formatAxisValue} width={60}
          label={{ value: analysis.y_label, angle: -90, position: 'insideLeft', offset: -6, fill: 'var(--text-muted)', fontSize: 12.5, fontFamily: 'var(--font-body)', style: { textAnchor: 'middle' } }} />
        <ZAxis range={[20, 20]} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
          if (!active || !payload?.length) return null;
          const p = payload[0].payload;
          return (
            <div className="chart-tooltip">
              {p.group !== undefined && <p className="mono" style={{ color: groupColor(p.group) }}>{p.group}</p>}
              <p className="mono">{analysis.x_label}: {p.x.toLocaleString()}</p>
              <p className="mono">{analysis.y_label}: {p.y.toLocaleString()}</p>
            </div>
          );
        }} />
        {hasGroups ? (
          <>
            {groups.map((g) => (
              <Scatter
                key={g}
                name={g}
                data={analysis.data.filter((d) => d.group === g)}
                fill={groupColor(g)}
                fillOpacity={0.65}
              />
            ))}
            <Legend
              verticalAlign="top"
              align="right"
              height={26}
              wrapperStyle={{ fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--text-muted)' }}
            />
          </>
        ) : (
          <Scatter data={analysis.data} fill="var(--teal)" fillOpacity={0.6} />
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function RelationshipInfo({ analysis }) {
  if (analysis.r === undefined || analysis.r === null) return null;
  const rColor = Math.abs(analysis.r) >= 0.4 ? (analysis.r > 0 ? 'var(--teal)' : 'var(--red)') : 'var(--text-faint)';
  return (
    <div className="relationship-info">
      <div className="relationship-row">
        <span className="relationship-key">X-axis</span>
        <span className="relationship-val mono">{analysis.x_label}</span>
      </div>
      <div className="relationship-row">
        <span className="relationship-key">Y-axis</span>
        <span className="relationship-val mono">{analysis.y_label}</span>
      </div>
      {analysis.color_by && (
        <div className="relationship-row">
          <span className="relationship-key">Colored by</span>
          <span className="relationship-val mono">{analysis.color_by}</span>
        </div>
      )}
      <div className="relationship-row">
        <span className="relationship-key">Correlation</span>
        <span className="relationship-val mono" style={{ color: rColor }}>r = {analysis.r.toFixed(2)}</span>
      </div>
      <div className="relationship-row">
        <span className="relationship-key">Interpretation</span>
        <span className="relationship-val">{analysis.interpretation}</span>
      </div>
    </div>
  );
}

function TreemapView({ analysis }) {
  const data = analysis.data.map((d) => ({ name: d.label, size: Math.abs(d.value) }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <Treemap data={data} dataKey="size" stroke="var(--ink)" fill="var(--teal)">
        {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
      </Treemap>
    </ResponsiveContainer>
  );
}

function HeatmapView({ analysis }) {
  const cols = [...new Set(analysis.data.map((d) => d.x))];
  const getCell = (x, y) => analysis.data.find((d) => d.x === x && d.y === y);
  const colorFor = (r) => {
    if (r === null || r === undefined) return 'var(--surface-raised)';
    const abs = Math.abs(r);
    if (r > 0) return `rgba(79, 166, 155, ${0.15 + abs * 0.7})`;
    return `rgba(217, 99, 107, ${0.15 + abs * 0.7})`;
  };
  return (
    <div className="heatmap-wrap">
      <div className="heatmap-grid" style={{ gridTemplateColumns: `100px repeat(${cols.length}, 1fr)` }}>
        <div />
        {cols.map((c) => <div key={c} className="heatmap-label mono">{c}</div>)}
        {cols.map((rowLabel) => (
          <Fragment key={rowLabel}>
            <div className="heatmap-label mono">{rowLabel}</div>
            {cols.map((colLabel) => {
              const cell = getCell(colLabel, rowLabel);
              return (
                <div
                  key={rowLabel + colLabel}
                  className="heatmap-cell mono"
                  style={{ background: colorFor(cell?.value) }}
                  title={`${rowLabel} vs ${colLabel}: ${cell?.value?.toFixed(2)}`}
                >
                  {cell?.value?.toFixed(2)}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function BoxplotView({ analysis }) {
  const d = analysis.data;
  if (!d || d.min === undefined) return null;
  const range = d.max - d.min || 1;
  const pct = (v) => ((v - d.min) / range) * 100;

  return (
    <div className="boxplot-wrap">
      <div className="boxplot-track">
        <div className="boxplot-whisker" style={{ left: `${pct(d.lower_fence)}%`, width: `${pct(d.q1) - pct(d.lower_fence)}%` }} />
        <div className="boxplot-box" style={{ left: `${pct(d.q1)}%`, width: `${pct(d.q3) - pct(d.q1)}%` }}>
          <div className="boxplot-median" style={{ left: `${((d.median - d.q1) / (d.q3 - d.q1 || 1)) * 100}%` }} />
        </div>
        <div className="boxplot-whisker" style={{ left: `${pct(d.q3)}%`, width: `${pct(d.upper_fence) - pct(d.q3)}%` }} />
      </div>
      <div className="boxplot-stats mono">
        <span>Min: {d.min.toFixed(1)}</span>
        <span>Q1: {d.q1.toFixed(1)}</span>
        <span>Median: {d.median.toFixed(1)}</span>
        <span>Q3: {d.q3.toFixed(1)}</span>
        <span>Max: {d.max.toFixed(1)}</span>
      </div>
      {d.outlier_count > 0 && (
        <p className="dim-sub" style={{ marginTop: 10 }}>
          {d.outlier_count} outlier{d.outlier_count === 1 ? '' : 's'} beyond the whiskers
          (outside {d.lower_fence.toFixed(1)}–{d.upper_fence.toFixed(1)})
        </p>
      )}
    </div>
  );
}

export default function AnalysisChartV2({ analysis }) {
  if (!analysis) return null;
  const isCurrency = looksLikeCurrency(analysis.metric_column) && analysis.type !== 'distribution_count';

  switch (analysis.chart_type) {
    case 'line':
      if (!analysis.data?.length) return null;
      return <LineView analysis={analysis} isCurrency={isCurrency} />;
    case 'histogram':
      if (!analysis.data?.length) return null;
      return <BarView analysis={analysis} isCurrency={isCurrency} horizontal={false} />;
    case 'horizontal_bar':
      if (!analysis.data?.length) return null;
      return <BarView analysis={analysis} isCurrency={isCurrency} horizontal />;
    case 'donut':
      if (!analysis.data?.length) return null;
      return <DonutView analysis={analysis} />;
    case 'scatter':
      if (!analysis.data?.length) return null;
      return (
        <div>
          <ScatterView analysis={analysis} />
          <RelationshipInfo analysis={analysis} />
        </div>
      );
    case 'treemap':
      if (!analysis.data?.length) return null;
      return <TreemapView analysis={analysis} />;
    case 'heatmap':
      if (!analysis.data?.length) return null;
      return <HeatmapView analysis={analysis} />;
    case 'boxplot':
      return <BoxplotView analysis={analysis} />;
    default:
      return null;
  }
}
