function PairCard({ pair, label, tone }) {
  if (!pair) return null;
  return (
    <div className="corr-callout" style={{ borderColor: tone === 'positive' ? 'var(--teal-dim)' : 'var(--red-dim)' }}>
      <span className="corr-callout-label" style={{ color: tone === 'positive' ? 'var(--teal)' : 'var(--red)' }}>
        {label}
      </span>
      <p className="corr-callout-text">{pair.col1} ↔ {pair.col2}</p>
      <span className="corr-callout-r mono">r = {pair.r.toFixed(2)}</span>
    </div>
  );
}

export default function CorrelationCenter({ correlationCenter, tickNum }) {
  const { pairs, strongest_positive, strongest_negative } = correlationCenter;

  if (!pairs?.length) {
    return (
      <div className="panel">
        <div className="panel-head">
          <span className="tick">{tickNum}</span>
          <h3>Correlation Center</h3>
        </div>
        <p className="dim-sub" style={{ padding: '4px 0 16px' }}>
          Not enough numeric measures in this dataset to check for relationships between them.
        </p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="tick">{tickNum}</span>
        <div>
          <h3>Correlation Center</h3>
          <p className="dim-sub">Which measures actually move together</p>
        </div>
      </div>

      <div className="corr-callouts">
        <PairCard pair={strongest_positive} label="Strongest positive" tone="positive" />
        <PairCard pair={strongest_negative} label="Strongest negative" tone="negative" />
      </div>

      {pairs.length > 1 && (
        <div className="corr-list">
          <span className="dq-block-title">All notable relationships</span>
          {pairs.map((p, i) => (
            <div key={i} className="corr-list-row">
              <span className="corr-list-pair">{p.col1} ↔ {p.col2}</span>
              <span className="corr-list-r mono" style={{ color: p.r > 0 ? 'var(--teal)' : 'var(--red)' }}>
                {p.r.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
