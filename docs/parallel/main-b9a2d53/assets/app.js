(() => {
  const target = document.querySelector('[data-feed]');
  if (!target) return;
  fetch('data/feed.json')
    .then((response) => {
      if (!response.ok) throw new Error('feed unavailable');
      return response.json();
    })
    .then((feed) => {
      target.textContent = `Evidence frozen ${feed.generated_utc.replace('T', ' ').replace('+00:00', ' UTC')}`;
    })
    .catch(() => {
      target.textContent = 'Evidence date: 2026-10-26';
    });
})();
