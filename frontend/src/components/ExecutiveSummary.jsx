import { Database, Columns3, CheckCircle2, LayoutGrid, Lightbulb, AlertTriangle } from 'lucide-react';

function StatCard({ icon, iconColor, iconBg, label, value, warn }) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon" style={{ background: iconBg, color: iconColor }}>
        {icon}
      </div>
      <div className="stat-card-body">
        <span className="stat-card-label">{label}</span>
        <span className={`stat-card-value mono ${warn ? 'stat-card-value-warn' : ''}`}>{value}</span>
      </div>
    </div>
  );
}

export default function ExecutiveSummary({ fileName, v2 }) {
  const { profile, findings, weak_points, top_analyses } = v2;

  return (
    <div className="exec-summary">
      <div className="exec-summary-head">
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
        <StatCard
          icon={<Database size={16} />} iconColor="var(--teal)" iconBg="var(--teal-dim)"
          label="Records" value={profile.row_count.toLocaleString()}
        />
        <StatCard
          icon={<Columns3 size={16} />} iconColor="var(--text-muted)" iconBg="var(--border-soft)"
          label="Columns" value={profile.column_count}
        />
        <StatCard
          icon={<CheckCircle2 size={16} />} iconColor="var(--green)" iconBg="var(--green-dim)"
          label="Completeness" value={`${profile.data_completeness_pct}%`}
        />
        <StatCard
          icon={<LayoutGrid size={16} />} iconColor="var(--teal)" iconBg="var(--teal-dim)"
          label="Key analyses" value={top_analyses.length}
        />
        <StatCard
          icon={<Lightbulb size={16} />} iconColor="var(--amber)" iconBg="var(--amber-dim)"
          label="Findings" value={findings.length}
        />
        <StatCard
          icon={<AlertTriangle size={16} />}
          iconColor={weak_points.length > 0 ? 'var(--red)' : 'var(--text-faint)'}
          iconBg={weak_points.length > 0 ? 'var(--red-dim)' : 'var(--border-soft)'}
          label="Weak points" value={weak_points.length} warn={weak_points.length > 0}
        />
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
