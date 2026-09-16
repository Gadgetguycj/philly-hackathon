async function loadSites() {
  const list = document.getElementById('sites');
  const empty = document.getElementById('empty');
  try {
    const response = await fetch('/api/sites');
    if (!response.ok) throw new Error(`The server returned HTTP ${response.status}.`);
    const sites = await response.json();
    if (!sites.length) { empty.textContent = 'No pages yet.'; return; }
    empty.hidden = true;
    for (const site of sites) {
      const item = document.createElement('li');
      const thumb = document.createElement('img');
      thumb.src = site.sketch_url;
      thumb.alt = 'The sketch for this page';
      const text = document.createElement('div');
      const link = document.createElement('a');
      link.href = site.url;
      link.textContent = site.url;
      text.append(link);
      const when = document.createElement('p');
      when.className = 'hint';
      when.textContent = new Date(site.created_at).toLocaleString();
      text.append(when);
      if (site.notes) {
        const notes = document.createElement('p');
        notes.textContent = site.notes;
        text.append(notes);
      }
      item.append(thumb, text);
      list.append(item);
    }
  } catch (error) {
    empty.textContent = error.message;
  }
}

loadSites();
