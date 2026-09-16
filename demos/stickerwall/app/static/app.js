const form = document.getElementById('draw-form');
const button = document.getElementById('draw-button');
const statusLine = document.getElementById('status');
const image = document.getElementById('result');
const usageLine = document.getElementById('usage');

async function loadUsage() {
  try {
    const response = await fetch('/api/usage');
    if (!response.ok) throw new Error('Could not load usage.');
    const usage = await response.json();
    usageLine.textContent = `Generations remaining: ${usage.remaining}`;
  } catch (error) {
    usageLine.textContent = 'Generations remaining: unavailable';
  }
}

loadUsage();

form.addEventListener('submit', async event => {
  event.preventDefault(); button.disabled = true; image.hidden = true; statusLine.textContent = 'GPU is working';
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 180000);
  try {
    const response = await fetch('/api/stickers', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, signal: controller.signal,
      body: JSON.stringify({team: document.getElementById('team').value, prompt: document.getElementById('prompt').value})
    });
    if (!response.ok) throw new Error(await response.text());
    const sticker = await response.json(); image.src = sticker.image_url; image.alt = sticker.prompt; image.hidden = false;
    statusLine.textContent = 'Sticker added to the wall';
    await loadUsage();
  } catch (error) {
    statusLine.textContent = error.name === 'AbortError' ? 'The request timed out after 3 minutes.' : error.message;
  } finally { clearTimeout(timeout); button.disabled = false; }
});
