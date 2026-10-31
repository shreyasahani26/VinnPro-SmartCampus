(() => {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  const icon = document.getElementById('themeIcon');
  const text = document.getElementById('themeText');
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    try { localStorage.setItem('vinnpro-theme', theme); } catch (_) {}
    if (icon) icon.textContent = theme === 'dark' ? '☀' : '☾';
    if (text) text.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
  };
  let saved = 'dark';
  try { saved = localStorage.getItem('vinnpro-theme') || 'dark'; } catch (_) {}
  applyTheme(saved);
  if (toggle) toggle.addEventListener('click', () => applyTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));

  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const menu = document.getElementById('menuToggle');
  const closeMenu = () => { sidebar?.classList.remove('sidebar-open'); overlay?.classList.remove('visible'); };
  menu?.addEventListener('click', () => { sidebar?.classList.toggle('sidebar-open'); overlay?.classList.toggle('visible'); });
  overlay?.addEventListener('click', closeMenu);
  window.addEventListener('resize', () => { if (window.innerWidth > 900) closeMenu(); });

  const search = document.getElementById('tableSearch');
  search?.addEventListener('input', () => {
    const table = document.getElementById('searchTable');
    if (!table) return;
    const term = search.value.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.hidden = !row.textContent.toLowerCase().includes(term);
    });
  });

  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      const textarea = document.getElementById('question');
      if (textarea) { textarea.value = button.dataset.prompt || ''; textarea.focus(); }
    });
  });
  document.querySelectorAll('.flash').forEach(flash => {
    window.setTimeout(() => { if (flash.isConnected) { flash.classList.add('flash-out'); window.setTimeout(() => flash.remove(), 250); } }, 6500);
  });
})();
