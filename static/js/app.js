// ── Tab switching ────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// ── Dictionary filter & search ──────────────────────────────────
const dictSearch = document.getElementById('dictSearch');
const dictPosFilter = document.getElementById('dictPosFilter');
const dictRows = document.querySelectorAll('#dictTable tbody tr');

function filterDict() {
    const query = dictSearch.value.toLowerCase().trim();
    const pos = dictPosFilter.value;

    dictRows.forEach(row => {
        const lemma = row.dataset.lemma || '';
        const rowPos = row.dataset.pos || '';
        const matchSearch = !query || lemma.includes(query);
        const matchPos = pos === 'all' || rowPos === pos;
        row.style.display = (matchSearch && matchPos) ? '' : 'none';
    });
}

if (dictSearch) dictSearch.addEventListener('input', filterDict);
if (dictPosFilter) dictPosFilter.addEventListener('change', filterDict);

// ── Noun → Adjective search (API call) ──────────────────────────
function searchNoun() {
    const input = document.getElementById('nounInput');
    const container = document.getElementById('searchResults');
    const noun = input.value.trim();

    if (!noun) {
        container.innerHTML = '<p class="search-empty">Введите существительное</p>';
        return;
    }

    container.innerHTML = '<p class="search-loading">Поиск…</p>';

    fetch(`/api/search?noun=${encodeURIComponent(noun)}&limit=30`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                container.innerHTML = `<p class="search-error">${data.error}</p>`;
                return;
            }
            if (!data.adjectives || data.adjectives.length === 0) {
                container.innerHTML = `
                    <div class="search-empty-state">
                        <p>Существительное «<strong>${data.noun}</strong>» не найдено в словосочетаниях.</p>
                        <p class="search-tip">Попробуйте ввести слово в начальной форме (именительный падеж, ед. число).</p>
                    </div>`;
                return;
            }

            let html = `
                <div class="search-result-card">
                    <h4 class="search-result-noun">${data.noun}</h4>
                    <div class="search-adj-list">`;

            data.adjectives.forEach(a => {
                const exHtml = a.examples && a.examples.length
                    ? `<span class="search-example">«${a.examples[0]}»</span>`
                    : '';
                html += `
                    <div class="search-adj-item">
                        <span class="search-adj-word">${a.adj}</span>
                        <span class="search-adj-count">×${a.count}</span>
                        ${exHtml}
                    </div>`;
            });

            html += '</div></div>';
            container.innerHTML = html;
        })
        .catch(err => {
            container.innerHTML = `<p class="search-error">Ошибка: ${err.message}</p>`;
        });
}

// Enter key triggers search
const nounInput = document.getElementById('nounInput');
if (nounInput) {
    nounInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') searchNoun();
    });
}

// ── Collocations alphabet navigation ────────────────────────────
const collAlphabet = document.getElementById('collAlphabet');
const collGrid = document.getElementById('collGrid');

if (collAlphabet && collGrid) {
    // Build set of letters that have words
    const lettersWithWords = new Set();
    collGrid.querySelectorAll('.coll-card[data-letter]').forEach(card => {
        const letter = card.dataset.letter;
        if (letter) lettersWithWords.add(letter);
    });

    // Mark letters without words as disabled
    collAlphabet.querySelectorAll('.alphabet-letter').forEach(btn => {
        if (!lettersWithWords.has(btn.dataset.letter)) {
            btn.classList.add('alphabet-letter--empty');
            btn.disabled = true;
        }
    });

    // Click: scroll to first word starting with that letter
    collAlphabet.addEventListener('click', (e) => {
        const btn = e.target.closest('.alphabet-letter');
        if (!btn || btn.disabled) return;
        const letter = btn.dataset.letter;
        const target = document.getElementById('coll-letter-' + letter);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
}

// ── Save to Supabase ────────────────────────────────────────────
function saveToSupabase() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Сохранение…';

    fetch('/api/save', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert('Ошибка: ' + data.error);
                btn.textContent = '💾 В Supabase';
            } else {
                btn.textContent = '✅ Сохранено';
                setTimeout(() => { btn.textContent = '💾 В Supabase'; }, 3000);
            }
            btn.disabled = false;
        })
        .catch(err => {
            alert('Ошибка: ' + err.message);
            btn.textContent = '💾 В Supabase';
            btn.disabled = false;
        });
}
