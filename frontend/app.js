/**
 * Atelier Documentaire RAG — Projets Étudiants
 * Frontend Application Logic (Datasheet/Dataset Ingestion, Vector Index Telemetry, Qwen2.5-7B Chat & Citation Highlighting)
 */

const state = {
  documents: [],
  activeDocId: null,
  lastCitations: [],
  chatHistory: [],
  isSubmitting: false,
};

// DOM References
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const corpusCountLabel = document.getElementById('corpus-count-label');
const docListContainer = document.getElementById('doc-list-container');
const statTotalChunks = document.getElementById('stat-total-chunks');
const statVectorDim = document.getElementById('stat-vector-dim');
const statLlmName = document.getElementById('stat-llm-name');
const selectDocFilter = document.getElementById('select-doc-filter');
const selectTopK = document.getElementById('select-topk');

const uploadDropzone = document.getElementById('upload-dropzone');
const fileInput = document.getElementById('file-input');
const btnTriggerUpload = document.getElementById('btn-trigger-upload');
const btnReloadSamples = document.getElementById('btn-reload-samples');

const conversationStream = document.getElementById('conversation-stream');
const chatForm = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const btnSubmitQuestion = document.getElementById('btn-submit-question');
const btnClearChat = document.getElementById('btn-clear-chat');

const tabBtnCitations = document.getElementById('tab-btn-citations');
const tabBtnExplorer = document.getElementById('tab-btn-explorer');
const tabPanelCitations = document.getElementById('tab-panel-citations');
const tabPanelExplorer = document.getElementById('tab-panel-explorer');
const citationCountBadge = document.getElementById('citation-count-badge');

const configModal = document.getElementById('config-modal');
const btnOpenConfig = document.getElementById('btn-open-config');
const btnCloseConfig = document.getElementById('btn-close-config');
const configForm = document.getElementById('config-form');
const inputModelId = document.getElementById('input-model-id');
const inputHfToken = document.getElementById('input-hf-token');

/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHtml(raw) {
  if (raw === null || raw === undefined) return '';
  return String(raw)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Lightweight, safe Markdown-to-HTML renderer with interactive citation badges [Doc — Page/Ligne].
 */
function renderTechnicalMarkdown(mdText) {
  const escaped = escapeHtml(mdText);

  // Convert fenced code blocks ```lang ... ```
  let html = escaped.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  const lines = html.split('\n');
  const out = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('#### ')) {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<h4>${formatInlineTokens(line.slice(5))}</h4>`);
    } else if (line.startsWith('### ')) {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<h3>${formatInlineTokens(line.slice(4))}</h3>`);
    } else if (line.startsWith('## ')) {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<h3>${formatInlineTokens(line.slice(3))}</h3>`);
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) { out.push('<ul>'); inList = true; }
      const itemContent = line.replace(/^\s*[-*]\s+/, '');
      out.push(`<li>${formatInlineTokens(itemContent)}</li>`);
    } else if (line.trim() === '') {
      if (inList) { out.push('</ul>'); inList = false; }
    } else {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<p>${formatInlineTokens(line)}</p>`);
    }
  }
  if (inList) out.push('</ul>');
  return out.join('\n');
}

function formatInlineTokens(text) {
  // Bold **text**
  let t = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Inline code `code`
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Citation tags like [BME280_Datasheet_Technique_FR.pdf — Page 2] or [File - Ligne 6]
  t = t.replace(/\[([^\]]+?\s(?:—|-)\s(?:Page|Ligne|Lignes|Section|Schéma)[^\]]*?)\]/g, (match, inner) => {
    return `<span class="inline-citation" data-cite-ref="${inner}" title="Cliquer pour mettre en évidence la source dans le panneau de droite">[${inner}]</span>`;
  });
  return t;
}

/**
 * Switch right-hand inspector tabs ("citations" | "explorer")
 */
function switchInspectorTab(tabName) {
  if (tabName === 'citations') {
    tabBtnCitations.classList.add('active');
    tabBtnExplorer.classList.remove('active');
    tabPanelCitations.style.display = 'flex';
    tabPanelExplorer.style.display = 'none';
  } else {
    tabBtnExplorer.classList.add('active');
    tabBtnCitations.classList.remove('active');
    tabPanelExplorer.style.display = 'flex';
    tabPanelCitations.style.display = 'none';
  }
}

tabBtnCitations.addEventListener('click', () => switchInspectorTab('citations'));
tabBtnExplorer.addEventListener('click', () => switchInspectorTab('explorer'));

/**
 * Fetch and refresh corpus status and model telemetry.
 */
async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error('Erreur réseau lors de la lecture du statut.');
    const data = await res.json();

    // Update top status indicator
    if (data.hf_token_configured) {
      statusDot.classList.remove('local-mode');
      statusText.textContent = `Hugging Face API : ${data.model_id}`;
    } else {
      statusDot.classList.add('local-mode');
      statusText.textContent = `${data.model_id} (Synthèse Locale + Prêt HF_TOKEN)`;
    }

    inputModelId.value = data.model_id || 'Qwen/Qwen2.5-7B-Instruct';
    updateCorpusUI(data.corpus, data.model_id);
  } catch (err) {
    statusText.textContent = 'Erreur de connexion au serveur RAG';
    console.error(err);
  }
}

function updateCorpusUI(corpus, modelId) {
  state.documents = corpus.documents || [];
  const docCount = state.documents.length;
  corpusCountLabel.textContent = `${docCount} document${docCount > 1 ? 's' : ''}`;
  statTotalChunks.textContent = corpus.total_chunks || 0;
  statVectorDim.textContent = `${corpus.vector_dimension || 0} dim.`;
  statLlmName.textContent = (modelId || 'Qwen2.5-7B').split('/').pop();

  // Populate document filter dropdown
  const currentFilter = selectDocFilter.value;
  selectDocFilter.innerHTML = '<option value="all">Tous les documents indexés</option>';
  state.documents.forEach((doc) => {
    const opt = document.createElement('option');
    opt.value = doc.doc_id;
    opt.textContent = `${doc.filename} (${doc.doc_type.toUpperCase()})`;
    selectDocFilter.appendChild(opt);
  });
  if ([...selectDocFilter.options].some((o) => o.value === currentFilter)) {
    selectDocFilter.value = currentFilter;
  }

  // Render document cards in left sidebar
  if (state.documents.length === 0) {
    docListContainer.innerHTML = `
      <div class="empty-notice">
        Aucun document indexé. Importez une datasheet PDF ou un dataset CSV/JSON, ou cliquez sur « Banc BME280 ».
      </div>
    `;
    return;
  }

  docListContainer.innerHTML = '';
  state.documents.forEach((doc) => {
    const card = document.createElement('div');
    card.className = `doc-card ${state.activeDocId === doc.doc_id ? 'active' : ''}`;
    card.dataset.docId = doc.doc_id;

    // Extract summary tags (voltages, hex registers, or dataset columns)
    const chips = [];
    const stats = doc.summary_stats || {};
    if (doc.doc_type === 'datasheet') {
      (stats.tensions_detectees || []).slice(0, 2).forEach((v) => chips.push(v));
      (stats.registres_ou_adresses_hex || []).slice(0, 3).forEach((h) => chips.push(h));
    } else if (doc.doc_type === 'dataset') {
      (stats.colonnes || []).slice(0, 4).forEach((col) => chips.push(col));
    }

    const chipsHtml = chips.length
      ? `<div class="doc-tags">${chips.map((c) => `<span class="tech-chip">${escapeHtml(c)}</span>`).join('')}</div>`
      : '';

    card.innerHTML = `
      <div class="doc-card-top">
        <span class="doc-type-label ${escapeHtml(doc.doc_type)}">${escapeHtml(doc.doc_type)} · ${escapeHtml(doc.file_format)}</span>
        <button type="button" class="btn btn-ghost btn-remove-doc" data-doc-id="${escapeHtml(doc.doc_id)}" title="Retirer ce document de l'index" style="padding: 0.1rem 0.35rem; font-size: 0.72rem;">
          Retirer
        </button>
      </div>
      <div class="doc-name">${escapeHtml(doc.filename)}</div>
      <div class="doc-stats">
        <span>${doc.total_units} ${escapeHtml(doc.unit_label)}</span>
        <span>${doc.chunk_count} segments vectorisés</span>
      </div>
      ${chipsHtml}
    `;

    card.addEventListener('click', (e) => {
      if (e.target.closest('.btn-remove-doc')) return;
      inspectDocument(doc.doc_id);
    });

    const removeBtn = card.querySelector('.btn-remove-doc');
    removeBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await deleteDocument(doc.doc_id);
    });

    docListContainer.appendChild(card);
  });

  // Automatically inspect the first document if none selected yet
  if (!state.activeDocId && state.documents.length > 0) {
    inspectDocument(state.documents[0].doc_id, false);
  }
}

/**
 * Load full details and chunks of a document into the right-hand Document Inspector tab.
 */
async function inspectDocument(docId, switchTab = true) {
  state.activeDocId = docId;
  document.querySelectorAll('.doc-card').forEach((el) => {
    el.classList.toggle('active', el.dataset.docId === docId);
  });

  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(docId)}`);
    if (!res.ok) return;
    const data = await res.json();
    const meta = data.meta;
    const chunks = data.chunks || [];

    let statsBlock = '';
    const s = meta.summary_stats || {};
    if (meta.doc_type === 'datasheet') {
      const voltages = (s.tensions_detectees || []).join(', ') || 'Non spécifié';
      const hexList = (s.registres_ou_adresses_hex || []).join(', ') || 'Aucun';
      const temps = (s.plages_thermiques || []).join(', ') || 'Non spécifié';
      statsBlock = `
        <div class="citation-card">
          <div class="citation-header">
            <span class="citation-ref-badge">Télémesure Datasheet</span>
            <span class="citation-score">${meta.total_units} ${escapeHtml(meta.unit_label)}</span>
          </div>
          <div class="citation-section">${escapeHtml(meta.filename)}</div>
          <div class="citation-excerpt">Tensions détectées : ${escapeHtml(voltages)}\nRegistres / Adresses Hex : ${escapeHtml(hexList)}\nPlages thermiques : ${escapeHtml(temps)}</div>
        </div>
      `;
    } else {
      const cols = (s.colonnes || []).join(', ');
      const numStats = s.statistiques_numeriques || {};
      const numLines = Object.entries(numStats)
        .map(([k, v]) => `${k} : min=${v.min}, max=${v.max}, moy=${v.moyenne}`)
        .join('\n');
      statsBlock = `
        <div class="citation-card">
          <div class="citation-header">
            <span class="citation-ref-badge">Schéma &amp; Statistiques Dataset</span>
            <span class="citation-score">${meta.total_units} entrées</span>
          </div>
          <div class="citation-section">${escapeHtml(meta.filename)}</div>
          <div class="citation-excerpt">Colonnes : ${escapeHtml(cols)}\n\n${escapeHtml(numLines)}</div>
        </div>
      `;
    }

    const chunksHtml = chunks
      .map(
        (c, idx) => `
        <div class="citation-card">
          <div class="citation-header">
            <span class="citation-ref-badge">${escapeHtml(c.source_ref)}</span>
            <span class="citation-score">Segment #${idx + 1}</span>
          </div>
          <div class="citation-section">${escapeHtml(c.section_title)}</div>
          <div class="citation-excerpt">${escapeHtml(c.content)}</div>
        </div>
      `
      )
      .join('');

    tabPanelExplorer.innerHTML = statsBlock + chunksHtml;
    if (switchTab) {
      switchInspectorTab('explorer');
    }
  } catch (err) {
    console.error('Erreur inspection document:', err);
  }
}

async function deleteDocument(docId) {
  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
    });
    if (res.ok) {
      if (state.activeDocId === docId) {
        state.activeDocId = null;
      }
      await refreshStatus();
    }
  } catch (err) {
    console.error('Erreur suppression document:', err);
  }
}

/**
 * File Upload (Datasheet PDF / Dataset CSV, JSON, XLSX)
 */
btnTriggerUpload.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async (e) => {
  if (e.target.files && e.target.files[0]) {
    await handleFileUpload(e.target.files[0]);
    fileInput.value = '';
  }
});

uploadDropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadDropzone.classList.add('dragover');
});

uploadDropzone.addEventListener('dragleave', () => {
  uploadDropzone.classList.remove('dragover');
});

uploadDropzone.addEventListener('drop', async (e) => {
  e.preventDefault();
  uploadDropzone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    await handleFileUpload(e.dataTransfer.files[0]);
  }
});

async function handleFileUpload(file) {
  const formData = new FormData();
  formData.append('file', file);

  const originalText = btnTriggerUpload.textContent;
  btnTriggerUpload.disabled = true;
  btnTriggerUpload.textContent = 'Extraction & Vectorisation...';

  try {
    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Erreur lors de l'importation du fichier.");
      return;
    }
    state.activeDocId = data.document.doc_id;
    await refreshStatus();
    await inspectDocument(data.document.doc_id, true);
  } catch (err) {
    alert("Erreur réseau lors de l'envoi du fichier.");
    console.error(err);
  } finally {
    btnTriggerUpload.disabled = false;
    btnTriggerUpload.textContent = originalText;
  }
}

btnReloadSamples.addEventListener('click', async () => {
  btnReloadSamples.disabled = true;
  try {
    const res = await fetch('/api/documents/load-samples', { method: 'POST' });
    if (res.ok) {
      await refreshStatus();
    }
  } finally {
    btnReloadSamples.disabled = false;
  }
});

/**
 * Render Retrieved Citations in the Right Panel
 */
function renderCitationsPanel(citations) {
  state.lastCitations = citations || [];
  citationCountBadge.textContent = state.lastCitations.length;

  if (state.lastCitations.length === 0) {
    tabPanelCitations.innerHTML = `
      <div class="empty-notice">
        Aucun segment documentaire n'a dépassé le seuil de pertinence pour cette requête.
      </div>
    `;
    return;
  }

  tabPanelCitations.innerHTML = state.lastCitations
    .map(
      (c) => `
      <div class="citation-card" id="citation-card-${c.rank}" data-cite-key="${escapeHtml(c.doc_name)} — ${escapeHtml(c.source_ref)}">
        <div class="citation-header">
          <span class="citation-ref-badge">#${c.rank} · ${escapeHtml(c.source_ref)}</span>
          <span class="citation-score">Similarité : ${(c.similarity_score * 100).toFixed(1)} %</span>
        </div>
        <div class="citation-doc-title">${escapeHtml(c.doc_name)} (${escapeHtml(c.doc_type.toUpperCase())})</div>
        <div class="citation-section">${escapeHtml(c.section_title)}</div>
        <div class="citation-excerpt">${escapeHtml(c.content)}</div>
      </div>
    `
    )
    .join('');

  switchInspectorTab('citations');
}

/**
 * Submit a student technical question to the RAG pipeline
 */
async function submitQuestion(questionText) {
  const trimmed = questionText.trim();
  if (!trimmed || state.isSubmitting) return;

  state.isSubmitting = true;
  btnSubmitQuestion.disabled = true;
  btnSubmitQuestion.textContent = 'Analyse RAG...';

  // Append student message
  const studentArticle = document.createElement('article');
  studentArticle.className = 'message-entry student';
  studentArticle.innerHTML = `
    <div class="message-meta">
      <span class="message-author student">Étudiant — Projet</span>
      <span>Requête soumise</span>
    </div>
    <div class="message-body"><p>${escapeHtml(trimmed)}</p></div>
  `;
  conversationStream.appendChild(studentArticle);

  // Append loading placeholder for assistant
  const assistantArticle = document.createElement('article');
  assistantArticle.className = 'message-entry assistant';
  assistantArticle.innerHTML = `
    <div class="message-meta">
      <span class="message-author assistant">Ingénieur-Encadrant RAG (Qwen2.5-7B)</span>
      <span>Recherche vectorielle &amp; synthèse en cours...</span>
    </div>
    <div class="message-body">
      <p>Extraction des segments pertinents de la datasheet et du dataset en cours...</p>
    </div>
  `;
  conversationStream.appendChild(assistantArticle);
  conversationStream.scrollTop = conversationStream.scrollHeight;

  const docFilterVal = selectDocFilter.value;
  const payload = {
    question: trimmed,
    top_k: parseInt(selectTopK.value, 10) || 4,
    doc_filter: docFilterVal === 'all' ? null : [docFilterVal],
    history: state.chatHistory.slice(-4),
  };

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      assistantArticle.querySelector('.message-body').innerHTML = `<p><strong>Erreur :</strong> ${escapeHtml(data.detail || 'Impossible de générer la réponse.')}</p>`;
      return;
    }

    const trace = data.pipeline_trace || {};
    const renderedAnswer = renderTechnicalMarkdown(data.answer);

    assistantArticle.innerHTML = `
      <div class="message-meta">
        <span class="message-author assistant">Ingénieur-Encadrant RAG</span>
        <span>${escapeHtml(data.model_used)} · ${data.latency_ms} ms</span>
      </div>
      <div class="message-body">
        ${renderedAnswer}
        <div class="pipeline-trace-bar">
          <span>Vectorisation : ${escapeHtml(trace.etape_2_vectorisation || '')}</span>
          <span>·</span>
          <span>Récupération : ${escapeHtml(trace.etape_3_recuperation || '')}</span>
        </div>
      </div>
    `;

    // Bind inline citation click to highlight corresponding card in right panel
    assistantArticle.querySelectorAll('.inline-citation').forEach((badge) => {
      badge.addEventListener('click', () => {
        const ref = badge.getAttribute('data-cite-ref') || '';
        switchInspectorTab('citations');
        document.querySelectorAll('#tab-panel-citations .citation-card').forEach((card) => {
          const key = card.getAttribute('data-cite-key') || '';
          const isMatch = key && (ref.includes(key) || key.includes(ref));
          card.classList.toggle('highlighted', Boolean(isMatch));
          if (isMatch) {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        });
      });
    });

    // Save in conversation history
    state.chatHistory.push({ role: 'user', content: trimmed });
    state.chatHistory.push({ role: 'assistant', content: data.answer });

    // Update right panel with citations
    renderCitationsPanel(data.citations || []);
    conversationStream.scrollTop = conversationStream.scrollHeight;
  } catch (err) {
    assistantArticle.querySelector('.message-body').innerHTML = `<p><strong>Erreur réseau :</strong> Impossible de joindre le serveur RAG.</p>`;
    console.error(err);
  } finally {
    state.isSubmitting = false;
    btnSubmitQuestion.disabled = false;
    btnSubmitQuestion.textContent = 'Interroger le RAG';
  }
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = questionInput.value;
  questionInput.value = '';
  await submitQuestion(q);
});

questionInput.addEventListener('keydown', async (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const q = questionInput.value;
    questionInput.value = '';
    await submitQuestion(q);
  }
});

// Guided Student Project Prompt Pills
document.querySelectorAll('.prompt-pill').forEach((pill) => {
  pill.addEventListener('click', async () => {
    const q = pill.getAttribute('data-question');
    if (q) {
      await submitQuestion(q);
    }
  });
});

// Clear conversation
btnClearChat.addEventListener('click', () => {
  state.chatHistory = [];
  conversationStream.innerHTML = `
    <article class="message-entry assistant">
      <div class="message-meta">
        <span class="message-author assistant">Ingénieur-Encadrant RAG (Qwen2.5-7B)</span>
        <span>Historique réinitialisé</span>
      </div>
      <div class="message-body">
        <p>L'historique de conversation a été effacé. Les documents de votre corpus restent indexés et prêts à être interrogés.</p>
      </div>
    </article>
  `;
});

/**
 * Configuration Modal for Hugging Face Token & Qwen2.5-7B Model ID
 */
btnOpenConfig.addEventListener('click', () => {
  configModal.classList.add('open');
});

btnCloseConfig.addEventListener('click', () => {
  configModal.classList.remove('open');
});

configModal.addEventListener('click', (e) => {
  if (e.target === configModal) {
    configModal.classList.remove('open');
  }
});

configForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btnSave = document.getElementById('btn-save-config');
  btnSave.disabled = true;
  btnSave.textContent = 'Mise à jour...';

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_id: inputModelId.value.trim(),
        hf_token: inputHfToken.value.trim(),
      }),
    });
    if (res.ok) {
      configModal.classList.remove('open');
      await refreshStatus();
    }
  } finally {
    btnSave.disabled = false;
    btnSave.textContent = 'Enregistrer et Ré-indexer';
  }
});

// Initialize on load
refreshStatus();
