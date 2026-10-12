(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  const saved = localStorage.getItem('rw10plus-site-theme');
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  root.dataset.theme = saved || (dark ? 'dark' : 'light');
  toggle?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('rw10plus-site-theme', next);
  });
})();
