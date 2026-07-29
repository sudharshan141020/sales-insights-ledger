import { useState } from 'react';

const ROLE_LABELS = {
  date: 'Date', revenue: 'Revenue', profit: 'Profit', cost: 'Cost',
  quantity: 'Quantity', discount: 'Discount', customer: 'Customer',
  category: 'Category', region: 'Region',
};

export default function MappingSummary({ result }) {
  const [open, setOpen] = useState(false);
  const { detected_columns, detection_confidence, unmapped_columns } = result;
  const roles = Object.keys(ROLE_LABELS).filter((r) => detected_columns[r]);
  const inferredCount = roles.filter((r) => detection_confidence[r] === 'inferred').length;

  return (
    <div className="mapping-summary">
      <button className="mapping-toggle" onClick={() => setOpen((o) => !o)}>
        <span className="tick">02</span>
        <span className="mapping-toggle-label">Column mapping</span>
        {inferredCount > 0 && (
          <span className="mapping-flag">{inferredCount} inferred — worth a check</span>
        )}
        <span className="mapping-chevron">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="mapping-body">
          <div className="mapping-grid">
            {roles.map((role) => (
              <div key={role} className="mapping-row">
                <span className="mapping-role">{ROLE_LABELS[role]}</span>
                <span className="mapping-arrow">→</span>
                <span className="mapping-col mono">{detected_columns[role]}</span>
                <span className={`mapping-badge ${detection_confidence[role]}`}>
                  {detection_confidence[role] === 'name' ? 'matched'
                    : detection_confidence[role] === 'combined' ? 'merged'
                    : 'inferred'}
                </span>
              </div>
            ))}
          </div>
          {unmapped_columns?.length > 0 && (
            <div className="mapping-unused">
              <span className="dim-sub">Not used in analysis: </span>
              <span className="mono unused-list">{unmapped_columns.join(', ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
