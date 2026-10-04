const form = document.querySelector('#diagnosis-form');
const search = document.querySelector('#symptom-search');
const suggestions = document.querySelector('#symptom-options');
const chosenEl = document.querySelector('#selected-symptoms');
const countEl = document.querySelector('#selected-count');
const submitButton = document.querySelector('#submit-button');
const errorEl = document.querySelector('#form-error');
const results = document.querySelector('#results');
let allSymptoms = [];
let selected = [];

const titleCase = (value) => value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

async function init() {
  try {
    const response = await fetch('/api/options', {cache:'no-store'});
    if (!response.ok) throw new Error('The model symptom list could not be loaded.');
    const data = await response.json();
    allSymptoms = data.symptoms;
    document.querySelector('#search-count').textContent = `${allSymptoms.length} symptoms`;
  } catch (error) {
    showError(error.message || 'The local model server is unavailable.');
    search.disabled = true;
    submitButton.disabled = true;
  }
}

function renderSelected() {
  countEl.textContent = `${selected.length} added`;
  if (!selected.length) {
    chosenEl.className = 'chips-empty';
    chosenEl.textContent = 'Your selected symptoms will appear here.';
    return;
  }
  chosenEl.className = 'chip-list';
  chosenEl.replaceChildren(...selected.map(symptom => {
    const chip = document.createElement('span');
    chip.className = 'symptom-chip';
    chip.append(document.createTextNode(titleCase(symptom)));
    const remove = document.createElement('button');
    remove.type = 'button'; remove.setAttribute('aria-label', `Remove ${titleCase(symptom)}`); remove.textContent = '×';
    remove.addEventListener('click', () => { selected = selected.filter(value => value !== symptom); renderSelected(); });
    chip.append(remove);
    return chip;
  }));
}

function renderSuggestions() {
  const query = search.value.trim().toLowerCase().replaceAll(' ', '_');
  if (!query) { suggestions.hidden = true; return; }
  const matches = allSymptoms.filter(name => name.includes(query) && !selected.includes(name)).slice(0, 9);
  suggestions.replaceChildren();
  if (!matches.length) {
    const empty = document.createElement('div'); empty.className = 'suggest-empty'; empty.textContent = 'No matching symptom. Try another search.'; suggestions.append(empty);
  } else {
    for (const name of matches) {
      const option = document.createElement('button'); option.type = 'button'; option.className = 'suggestion'; option.setAttribute('role', 'option');
      const label = document.createElement('span'); label.textContent = titleCase(name);
      const add = document.createElement('small'); add.textContent = '+ Add';
      option.append(label, add);
      option.addEventListener('click', () => {
        if (selected.length >= 20) { showError('You can compare up to 20 symptoms at a time.'); return; }
        selected.push(name); renderSelected(); search.value = ''; suggestions.hidden = true; clearError(); search.focus();
      });
      suggestions.append(option);
    }
  }
  suggestions.hidden = false;
}

function showError(message) { errorEl.textContent = message; errorEl.hidden = false; }
function clearError() { errorEl.hidden = true; errorEl.textContent = ''; }

function renderResult(data) {
  const picked = data.selected;
  document.querySelector('#selected-result').innerHTML = `
    <div class="result-copy"><div class="selected-overline">SELECTED MODEL · ${escapeHtml(picked.id)} — ${escapeHtml(picked.name)}</div>
      <div class="selected-disease">${escapeHtml(picked.disease)}</div></div>`;
  results.hidden = false;
}

search.addEventListener('input', () => { clearError(); renderSuggestions(); });
search.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') suggestions.hidden = true;
  if (event.key === 'Enter' && !suggestions.hidden) { event.preventDefault(); suggestions.querySelector('button')?.click(); }
});
document.addEventListener('click', event => { if (!event.target.closest('.search-wrap')) suggestions.hidden = true; });

form.addEventListener('submit', async (event) => {
  event.preventDefault(); clearError();
  if (!selected.length) { showError('Choose at least one symptom before comparing the models.'); return; }
  submitButton.disabled = true;
  submitButton.querySelector('span:first-child').textContent = 'Checking models…';
  submitButton.querySelector('.button-arrow').textContent = '· · ·';
  try {
    const response = await fetch('/api/diagnose', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symptoms:selected})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The models could not complete this comparison.');
    renderResult(data);
    results.scrollIntoView({behavior:'smooth',block:'start'});
  } catch (error) {
    showError(error.message || 'The local model server is unavailable. Please try again.');
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector('span:first-child').textContent = 'Get result';
    submitButton.querySelector('.button-arrow').textContent = '↗';
  }
});

document.querySelector('#reset-button').addEventListener('click', () => {
  selected = []; renderSelected(); clearError(); results.hidden = true; search.value = '';
  document.querySelector('#checker').scrollIntoView({behavior:'smooth',block:'start'});
});

init();
