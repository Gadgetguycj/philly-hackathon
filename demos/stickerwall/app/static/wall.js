const wall = document.getElementById('wall');
const empty = document.getElementById('empty');

async function refresh() {
  try {
    const response = await fetch('/api/stickers', {cache: 'no-store'});
    if (!response.ok) throw new Error(await response.text());
    const stickers = await response.json();
    empty.textContent = stickers.length ? '' : 'No stickers yet.';
    const known = new Map([...wall.children].map(card => [card.dataset.id, card]));
    for (const sticker of stickers) {
      let card = known.get(String(sticker.id));
      if (!card) {
        card = document.createElement('article'); card.className = 'sticker'; card.dataset.id = sticker.id;
        const image = document.createElement('img'); image.src = sticker.image_url; image.alt = sticker.prompt; image.loading = 'lazy';
        const team = document.createElement('strong'); team.textContent = sticker.team;
        card.append(image, team);
      }
      wall.appendChild(card); known.delete(String(sticker.id));
    }
    for (const stale of known.values()) stale.remove();
  } catch (error) { empty.textContent = error.message; }
}
refresh(); setInterval(refresh, 5000);

