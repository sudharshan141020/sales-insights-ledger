import { useCallback, useRef, useState } from 'react';

const ACCEPTED_EXTENSIONS = ['.csv', '.tsv', '.xlsx', '.xls'];

function CloudIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 27a7 7 0 0 1-1-13.94A9 9 0 0 1 28 15.1 6.5 6.5 0 0 1 27 27H12Z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"
      />
      <path d="M20 19v10m0-10 3.5 3.5M20 19l-3.5 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function UploadZone({ onFilesSelected, error, compact = false }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const valid = [];
    const rejected = [];
    for (const f of files) {
      const name = f.name.toLowerCase();
      if (ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
        valid.push(f);
      } else {
        rejected.push(f.name);
      }
    }

    const errorMsg = rejected.length
      ? `Skipped ${rejected.length} file(s) with unsupported type: ${rejected.join(', ')}`
      : null;

    if (valid.length) onFilesSelected(valid, errorMsg);
    else onFilesSelected([], errorMsg || 'Accepted formats: .csv, .tsv, .xlsx, .xls');
  }, [onFilesSelected]);

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className={compact ? 'upload-wrap-compact' : 'upload-wrap'}>
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''} ${compact ? 'compact' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.xlsx,.xls"
          multiple
          hidden
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
        {compact ? (
          <span className="upload-compact-label">+ New analysis</span>
        ) : (
          <>
            <div className="upload-icon"><CloudIcon /></div>
            <p className="upload-title">Drop your data files here</p>
            <p className="upload-or">or</p>
            <span className="upload-browse-btn">Browse Files</span>
            <p className="upload-formats mono">CSV &nbsp;•&nbsp; XLSX &nbsp;•&nbsp; XLS</p>
          </>
        )}
      </div>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
