const STEPS = ['Upload', 'Analyze', 'Insights', 'Dashboard'];

export default function WorkflowSteps() {
  return (
    <div className="workflow-steps">
      {STEPS.map((step, i) => (
        <div className="workflow-step" key={step}>
          <span className="workflow-num mono">{String(i + 1).padStart(2, '0')}</span>
          <span className="workflow-label">{step}</span>
          {i < STEPS.length - 1 && <span className="workflow-arrow">→</span>}
        </div>
      ))}
    </div>
  );
}
