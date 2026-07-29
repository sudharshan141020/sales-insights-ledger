export default function ExecutiveSummary({ fileName, v2 }) {
  const { profile, findings, weak_points, top_analyses } = v2;

  return (
    <div className="exec-summary">
      <div className="exec-summary-head">
        <span className="tick">01</span>
        <div>
          <h2 className="exec-title">{fileName}</h2>
          {profile.domain !== 'generic' ? (
            <p className="exec-domain">
              Detected as <strong>{profile.domain}</strong> data
              <span className="exec-confidence"> ({Math.round(profile.domain_confidence * 100)}% confidence)</span>
              {' '}— analyzing by {profile.primary_entity.toLowerCase()}
            </p>
          ) : (
            <p className="exec-domain">Domain not confidently identified — analyzing generically</p>
          )}
        </div>
      </div>

      <div className="exec-stats">
        <div className="exec-stat">
          <span className="exec-stat-value mono">{profile.row_count.toLocaleString()}</span>
          <span className="exec-stat-label">Records</span>
        </div>
        <div className="exec-stat">
          <span className="exec-stat-value mono">{profile.column_count}</span>
          <span className="exec-stat-label">Columns</span>
        </div>
        <div className="exec-stat">
          <span className="exec-stat-value mono">{profile.data_completeness_pct}%</span>
          <span className="exec-stat-label">Completeness</span>
        </div>
        <div className="exec-stat">
          <span className="exec-stat-value mono">{top_analyses.length}</span>
          <span className="exec-stat-label">Key analyses</span>
        </div>
        <div className="exec-stat">
          <span className="exec-stat-value mono">{findings.length}</span>
          <span className="exec-stat-label">Findings</span>
        </div>
        <div className="exec-stat">
          <span className={`exec-stat-value mono ${weak_points.length > 0 ? 'exec-stat-warn' : ''}`}>
            {weak_points.length}
          </span>
          <span className="exec-stat-label">Weak points</span>
        </div>
      </div>

      {profile.key_kpis?.length > 0 && (
        <div className="exec-domain-kpis">
          <span className="dim-sub">This domain typically tracks: </span>
          <span className="exec-kpi-list">{profile.key_kpis.join(' · ')}</span>
        </div>
      )}
    </div>
  );
}
