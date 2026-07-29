const TYPE_META = {
  trend: { label: 'Trend', color: 'var(--teal)' },
  concentration: { label: 'Concentration', color: 'var(--amber)' },
  margin_risk: { label: 'Margin risk', color: 'var(--red)' },
  discount_risk: { label: 'Discount risk', color: 'var(--red)' },
  customer_concentration: { label: 'Customer concentration', color: 'var(--amber)' },
  correlation: { label: 'Correlation', color: 'var(--teal)' },
  outlier: { label: 'Outlier', color: 'var(--amber)' },
  data_quality: { label: 'Data quality', color: 'var(--red)' },
};

export default function InsightsPanel({ insights, tickNum }) {
  if (!insights?.length) {
    return (
      <div className="panel">
        <div className="panel-head">
          <span className="tick">{tickNum}</span>
          <h3>Findings</h3>
        </div>
        <p className="dim-sub" style={{ padding: '8px 0 20px' }}>
          Nothing stood out strongly enough to surface — the data looks evenly
          distributed across segments and time.
        </p>
      </div>
    );
  }

  const maxScore = Math.max(...insights.map((i) => i.score), 1);

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="tick">{tickNum}</span>
        <div>
          <h3>Findings</h3>
          <p className="dim-sub">Ranked by signal strength — how far each finding sits from an expected baseline</p>
        </div>
      </div>

      <div className="insights-list">
        {insights.map((insight, i) => {
          const meta = TYPE_META[insight.type] || { label: insight.type, color: 'var(--text-muted)' };
          const barWidth = Math.max(8, (insight.score / maxScore) * 100);
          return (
            <div key={i} className="insight-card">
              <div className="insight-top">
                <span className="insight-type" style={{ color: meta.color }}>{meta.label}</span>
                <span className="insight-rank mono">#{i + 1}</span>
              </div>
              <p className="insight-text">{insight.text}</p>
              {insight.recommendation && (
                <p className="insight-recommendation">
                  <span className="rec-label">Suggestion —</span> {insight.recommendation}
                </p>
              )}
              <div className="signal-track">
                <div
                  className="signal-fill"
                  style={{ width: `${barWidth}%`, background: meta.color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
