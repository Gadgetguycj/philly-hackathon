const form = document.getElementById('sketch-form');
const photo = document.getElementById('photo');
const fileName = document.getElementById('file-name');
const preview = document.getElementById('preview');
const notes = document.getElementById('notes');
const buildButton = document.getElementById('build');
const statusLine = document.getElementById('status');
const result = document.getElementById('result');
const pageLink = document.getElementById('page-link');

async function refreshUsage() {
  try {
    const response = await fetch('/api/usage');
    if (!response.ok) return;
    const usage = await response.json();
    document.getElementById('usage').textContent = `${usage.remaining} of ${usage.limit} generations left this hour.`;
  } catch (error) {
    document.getElementById('usage').textContent = '';
  }
}

photo.addEventListener('change', () => {
  const file = photo.files[0];
  if (!file) { preview.hidden = true; fileName.textContent = ''; return; }
  fileName.textContent = file.name;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
});

async function readResponse(response, onWriting) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let text = '';
  let writing = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    // Newlines are the keep-alive bytes sent while the GPU wakes. The space means the model started writing.
    if (!writing && text.includes(' ')) { writing = true; onWriting(); }
  }
  return JSON.parse(text + decoder.decode());
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!photo.files[0]) return;
  buildButton.disabled = true;
  result.hidden = true;
  statusLine.textContent = 'GPU is waking up';
  const body = new FormData();
  body.append('image', photo.files[0]);
  body.append('notes', notes.value);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 300000);
  try {
    const response = await fetch('/api/sketch', { method: 'POST', body, signal: controller.signal });
    if (!response.ok) {
      const failure = await response.json().catch(() => ({}));
      throw new Error(failure.detail || `The server returned HTTP ${response.status}.`);
    }
    const data = await readResponse(response, () => { statusLine.textContent = 'Writing your page'; });
    if (!data.url) throw new Error(data.detail || 'The server did not return a page.');
    const address = new URL(data.url, window.location.href).href;
    pageLink.href = address;
    pageLink.textContent = address;
    QR.draw(document.getElementById('qr'), address, 8);
    result.hidden = false;
    statusLine.textContent = `Your page took ${data.elapsed_seconds} seconds.`;
  } catch (error) {
    statusLine.textContent = error.name === 'AbortError' ? 'The request timed out after 5 minutes.' : error.message;
  } finally {
    clearTimeout(timeout);
    buildButton.disabled = false;
    refreshUsage();
  }
});

refreshUsage();
