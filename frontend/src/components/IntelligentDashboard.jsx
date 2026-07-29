import AnalysisChartV2 from './AnalysisChartV2';

export default function IntelligentDashboard({ topAnalyses, tickNum }) {
  if (!topAnalyses?.length) return null;

  return (
    <div className="intelligent-dashboard">
      <div className="panel-head" style={{ marginBottom: 4 }}>
        <span className="tick">{tickNum}</span>
        <div>
          <h3>Key Analyses</h3>
          <p className="dim-sub">The most important views into this dataset, chosen automatically</p>
        </div>
      </div>
      <div className="dashboard-3col">
        {topAnalyses.map((a) => (
          <div key={a.id} className="panel top-analysis-panel">
            <h4 className="top-analysis-title">{a.title}</h4>
            <AnalysisChartV2 analysis={a} />
            {a.reasoning && <p className="chart-reasoning">{a.reasoning}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
