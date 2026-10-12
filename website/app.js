(() => {
  const root = document.documentElement;
  const toggleThemeButton = document.querySelector('[data-theme-toggle]');
  const navToggle = document.querySelector('[data-nav-toggle]');
  const navPanel = document.querySelector('[data-nav-panel]');
  const navLinks = document.querySelectorAll('.nav-links a');
  const yearTarget = document.querySelector('[data-year]');

  const storageKey = 'rw10plus-site-theme';
  const savedTheme = localStorage.getItem(storageKey);
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  root.dataset.theme = savedTheme || (systemDark ? 'dark' : 'light');

  toggleThemeButton?.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = nextTheme;
    localStorage.setItem(storageKey, nextTheme);
  });

  const closeNav = () => {
    if (!navPanel || !navToggle) return;
    navPanel.classList.remove('is-open');
    navToggle.setAttribute('aria-expanded', 'false');
  };

  navToggle?.addEventListener('click', () => {
    if (!navPanel) return;
    const isOpen = navPanel.classList.toggle('is-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 820) closeNav();
    });
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 820) closeNav();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeNav();
  });

  yearTarget.textContent = new Date().getFullYear();
})();
