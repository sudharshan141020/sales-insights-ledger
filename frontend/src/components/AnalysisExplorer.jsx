import { useState, useEffect } from 'react';
import AnalysisChart from './AnalysisChart';

const TYPE_LABELS = {
  trend: 'Trend',
  histogram: 'Distribution',
  distribution_count: 'Count',
  distribution_sum: 'Breakdown',
};

export default function AnalysisExplorer({ analyses, tickNum, domain, domainConfidence }) {
  // Default to the first trend analysis if one exists (it's usually the
  // headline view), otherwise just the first analysis available.
  const defaultId = analyses?.find((a) => a.type === 'trend')?.id || analyses?.[0]?.id || '';
  const [selectedId, setSelectedId] = useState(defaultId);

  useEffect(() => {
    if (analyses?.length && !analyses.some((a) => a.id === selectedId)) {
      setSelectedId(analyses.find((a) => a.type === 'trend')?.id || analyses[0].id);
    }
  }, [analyses]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!analyses?.length) return null;

  const active = analyses.find((a) => a.id === selectedId) || analyses[0];

  return (
    <div className="panel">
      <div className="panel-head breakdown-head">
        <span className="tick">{tickNum}</span>
        <div>
          <h3>Explore</h3>
          {domain && domain !== 'generic' && (
            <p className="dim-sub" style={{ marginTop: 2 }}>
              Detected as {domain} data ({Math.round((domainConfidence || 0) * 100)}% confidence)
            </p>
          )}
        </div>
        <select
          className="breakdown-select"
          value={active.id}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {analyses.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title} — {TYPE_LABELS[a.type] || a.type}
            </option>
          ))}
        </select>
      </div>
      <AnalysisChart analysis={active} />
    </div>
  );
}
