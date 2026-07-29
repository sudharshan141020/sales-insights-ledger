import { useState, useEffect } from 'react';
import BreakdownChart from './BreakdownChart';

export default function BreakdownExplorer({ breakdowns, metricName, tickNum }) {
  const [selected, setSelected] = useState(breakdowns?.[0]?.column || '');

  // Keep selection valid when switching between sessions/files with
  // different columns available.
  useEffect(() => {
    if (breakdowns?.length && !breakdowns.some((b) => b.column === selected)) {
      setSelected(breakdowns[0].column);
    }
  }, [breakdowns]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!breakdowns?.length) return null;

  const active = breakdowns.find((b) => b.column === selected) || breakdowns[0];

  return (
    <div className="panel">
      <div className="panel-head breakdown-head">
        <span className="tick">{tickNum}</span>
        <h3>{metricName || 'Value'} by…</h3>
        <select
          className="breakdown-select"
          value={active.column}
          onChange={(e) => setSelected(e.target.value)}
        >
          {breakdowns.map((b) => (
            <option key={b.column} value={b.column}>{b.column}</option>
          ))}
        </select>
      </div>
      <BreakdownChart
        title=""
        data={active.data}
        tickNum={null}
        metricName={metricName}
        hideHeader
      />
    </div>
  );
}
