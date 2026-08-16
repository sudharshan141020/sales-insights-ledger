import { useState, useEffect } from 'react';
import AnalysisChartV2 from './AnalysisChartV2';

const SECTION_ORDER = ['Trends', 'Distributions', 'Relationships', 'Correlations', 'Outliers'];

export default function AnalysisExplorerV2({ analyses, tickNum }) {
  const sections = SECTION_ORDER.filter((s) => analyses.some((a) => a.section === s));
  const [activeSection, setActiveSection] = useState(sections[0] || '');
  const sectionAnalyses = analyses.filter((a) => a.section === activeSection);
  const [selectedId, setSelectedId] = useState(sectionAnalyses[0]?.id || '');

  useEffect(() => {
    const stillValidSections = SECTION_ORDER.filter((s) => analyses.some((a) => a.section === s));
    if (!stillValidSections.includes(activeSection)) {
      setActiveSection(stillValidSections[0] || '');
    }
  }, [analyses]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const current = analyses.filter((a) => a.section === activeSection);
    if (!current.some((a) => a.id === selectedId)) {
      setSelectedId(current[0]?.id || '');
    }
  }, [activeSection, analyses]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!analyses?.length) return null;

  const active = sectionAnalyses.find((a) => a.id === selectedId) || sectionAnalyses[0];

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="tick">{tickNum}</span>
        <h3>Explore</h3>
      </div>

      <div className="explorer-tabs">
        {sections.map((s) => (
          <button
            key={s}
            className={`explorer-tab ${s === activeSection ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s}
            <span className="explorer-tab-count">{analyses.filter((a) => a.section === s).length}</span>
          </button>
        ))}
      </div>

      {sectionAnalyses.length > 1 && (
        <select
          className="breakdown-select explorer-select"
          value={active?.id || ''}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {sectionAnalyses.map((a) => (
            <option key={a.id} value={a.id}>{a.title}</option>
          ))}
        </select>
      )}

      {active && (
        <div style={{ marginTop: 16 }}>
          <AnalysisChartV2 analysis={active} />
          {active.reasoning && <p className="chart-reasoning">{active.reasoning}</p>}
          {active.forecast_note && <p className="forecast-note">↝ {active.forecast_note}</p>}
        </div>
      )}
    </div>
  );
}
