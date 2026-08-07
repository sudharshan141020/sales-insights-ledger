import { useEffect, useState } from 'react';

const STORAGE_KEY = 'datalens-theme';

function getInitialTheme() {
  const saved = document.documentElement.dataset.theme;
  if (saved === 'light' || saved === 'dark') return saved;
  return 'dark';
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* private browsing / storage disabled — theme just won't persist */
    }
  }, [theme]);

  const isLight = theme === 'light';

  return (
    <button
      type="button"
      className={`theme-toggle ${isLight ? 'is-light' : 'is-dark'}`}
      role="switch"
      aria-checked={isLight}
      aria-label={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
      title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
      onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
    >
      <svg className="theme-toggle-art" viewBox="0 0 64 32" xmlns="http://www.w3.org/2000/svg">
        {/* stars — only visible in dark mode */}
        <g className="theme-toggle-stars">
          <circle cx="9" cy="8" r="1.3" />
          <circle cx="17" cy="16" r="1" />
          <circle cx="8" cy="21" r="1.1" />
          <circle cx="21" cy="6" r="0.9" />
          <circle cx="14" cy="24" r="0.9" />
        </g>
        {/* clouds — only visible in light mode */}
        <g className="theme-toggle-clouds">
          <ellipse cx="44" cy="21" rx="9" ry="4.5" />
          <ellipse cx="51" cy="18" rx="6.5" ry="4" />
          <ellipse cx="38" cy="17.5" rx="5.5" ry="3.5" />
        </g>
      </svg>
      <span className="theme-toggle-thumb">
        <svg viewBox="0 0 24 24" className="theme-toggle-thumb-icon">
          {isLight ? (
            <circle cx="12" cy="12" r="9" className="theme-toggle-sun" />
          ) : (
            <path
              className="theme-toggle-moon"
              d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z"
            />
          )}
          {!isLight && (
            <>
              <circle cx="9.5" cy="9" r="1.1" className="theme-toggle-moon-crater" />
              <circle cx="13.5" cy="14.5" r="0.8" className="theme-toggle-moon-crater" />
              <circle cx="8.5" cy="14" r="0.6" className="theme-toggle-moon-crater" />
            </>
          )}
        </svg>
      </span>
    </button>
  );
}
