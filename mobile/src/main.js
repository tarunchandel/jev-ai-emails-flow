import dataset from './dataset.json';

// Mobile App State
let state = {
  items: dataset,
  selectedId: dataset[0]?.id || null,
  activeTab: 'queue', // 'queue' | 'detail' | 'pipeline' | 'info'
  filter: 'ALL',      // 'ALL' | 'ACTIONABLE' | 'OCR' | 'HITL'
  isProcessing: false,
  processProgress: 100,
};

function getSelectedItem() {
  return state.items.find((item) => item.id === state.selectedId) || state.items[0];
}

function getUrgencyBadge(score) {
  if (score >= 8) {
    return `<span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 badge-glow-red">⚡ Urgency ${score}/10</span>`;
  }
  if (score >= 5) {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 badge-glow-amber">⏱ Urgency ${score}/10</span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">Urgency ${score}/10</span>`;
}

function getEventTypeBadge(eventType) {
  const map = {
    Cash_Dividend: '💵 Cash Dividend',
    Stock_Dividend: '📈 Stock Dividend',
    Merger_Acquisition: '🤝 M&A Tender',
    Ticker_Change: '🏷️ Ticker Change',
    Spam_Or_Irrelevant: '🚫 Spam / Non-CA',
  };
  return map[eventType] || eventType;
}

function render() {
  const app = document.getElementById('app');
  if (!app) return;

  const current = getSelectedItem();
  const sortedItems = [...state.items].sort((a, b) => {
    // High Urgency shifts items to top of queue
    return b.decision.urgency_score - a.decision.urgency_score;
  });

  const filteredItems = sortedItems.filter((item) => {
    if (state.filter === 'ACTIONABLE') return item.decision.is_actionable;
    if (state.filter === 'OCR') return item.ocr_applied;
    if (state.filter === 'HITL') return item.routing.route === 'HUMAN_IN_THE_LOOP';
    return true;
  });

  app.innerHTML = `
    <!-- Top App Bar -->
    <header class="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
          ⚡
        </div>
        <div>
          <h1 class="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
            Jev AI Corporate Actions
            <span class="px-1.5 py-0.5 text-[10px] font-medium bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">Mobile</span>
          </h1>
          <p class="text-[10px] text-slate-400">TypeSafe AI System One & Gemini Vision</p>
        </div>
      </div>
      <button id="run-pipeline-btn" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-95 transition text-white shadow-md shadow-indigo-600/30 flex items-center gap-1">
        <span>🔄</span> Re-run
      </button>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 pb-20 overflow-y-auto">
      ${
        state.activeTab === 'queue'
          ? renderQueueTab(filteredItems)
          : state.activeTab === 'detail'
          ? renderDetailTab(current)
          : state.activeTab === 'pipeline'
          ? renderPipelineTab(current)
          : renderInfoTab()
      }
    </main>

    <!-- Bottom Navigation Bar -->
    <nav class="fixed bottom-0 inset-x-0 bg-slate-900/95 backdrop-blur-lg border-t border-slate-800 z-50 px-4 py-2 flex justify-around">
      <button class="nav-btn flex flex-col items-center gap-0.5 text-xs transition ${
        state.activeTab === 'queue' ? 'text-indigo-400 font-semibold' : 'text-slate-400'
      }" data-tab="queue">
        <span class="text-lg">📥</span>
        <span>Queue (${state.items.length})</span>
      </button>
      <button class="nav-btn flex flex-col items-center gap-0.5 text-xs transition ${
        state.activeTab === 'detail' ? 'text-indigo-400 font-semibold' : 'text-slate-400'
      }" data-tab="detail">
        <span class="text-lg">🔍</span>
        <span>Inspection</span>
      </button>
      <button class="nav-btn flex flex-col items-center gap-0.5 text-xs transition ${
        state.activeTab === 'pipeline' ? 'text-indigo-400 font-semibold' : 'text-slate-400'
      }" data-tab="pipeline">
        <span class="text-lg">⚙️</span>
        <span>4-Stage Flow</span>
      </button>
      <button class="nav-btn flex flex-col items-center gap-0.5 text-xs transition ${
        state.activeTab === 'info' ? 'text-indigo-400 font-semibold' : 'text-slate-400'
      }" data-tab="info">
        <span class="text-lg">ℹ️</span>
        <span>Specs</span>
      </button>
    </nav>
  `;

  bindEvents();
}

function renderQueueTab(items) {
  return `
    <div class="p-3 space-y-3">
      <!-- Fast Filter Pills -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
        <button class="filter-btn px-2.5 py-1 rounded-full border transition whitespace-nowrap ${
          state.filter === 'ALL'
            ? 'bg-slate-700 text-white border-slate-500'
            : 'bg-slate-900/60 text-slate-400 border-slate-800'
        }" data-filter="ALL">All Items</button>
        <button class="filter-btn px-2.5 py-1 rounded-full border transition whitespace-nowrap ${
          state.filter === 'ACTIONABLE'
            ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500'
            : 'bg-slate-900/60 text-slate-400 border-slate-800'
        }" data-filter="ACTIONABLE">Actionable Notice</button>
        <button class="filter-btn px-2.5 py-1 rounded-full border transition whitespace-nowrap ${
          state.filter === 'OCR'
            ? 'bg-cyan-600/30 text-cyan-300 border-cyan-500'
            : 'bg-slate-900/60 text-slate-400 border-slate-800'
        }" data-filter="OCR">OCR Triggered</button>
        <button class="filter-btn px-2.5 py-1 rounded-full border transition whitespace-nowrap ${
          state.filter === 'HITL'
            ? 'bg-amber-600/30 text-amber-300 border-amber-500'
            : 'bg-slate-900/60 text-slate-400 border-slate-800'
        }" data-filter="HITL">HITL Exceptions</button>
      </div>

      <!-- Queue List -->
      <div class="space-y-2">
        ${items
          .map(
            (item) => `
          <div class="item-card glass-panel p-3 rounded-xl cursor-pointer active:scale-[0.98] transition border ${
            state.selectedId === item.id ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-slate-800'
          }" data-id="${item.id}">
            <div class="flex items-start justify-between gap-2 mb-1.5">
              <span class="text-xs font-semibold text-indigo-300">${getEventTypeBadge(
                item.decision.event_type
              )}</span>
              ${getUrgencyBadge(item.decision.urgency_score)}
            </div>
            <div class="font-medium text-xs text-white line-clamp-1 mb-1">${item.subject}</div>
            <div class="text-[11px] text-slate-400 line-clamp-2 mb-2 leading-relaxed">${item.body}</div>
            
            <div class="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-800/80 pt-2">
              <span class="flex items-center gap-1">
                ${
                  item.ocr_applied
                    ? '<span class="text-cyan-400 font-semibold">👁️ Gemini OCR</span>'
                    : '<span class="text-slate-400">📄 Text Envelope</span>'
                }
              </span>
              <span>
                ${
                  item.routing.route === 'GEMINI_CLIENT_NOTICE'
                    ? '<span class="text-emerald-400 font-semibold">📨 Draft Notice</span>'
                    : '<span class="text-amber-400 font-semibold">⚠️ HITL Desk</span>'
                }
              </span>
            </div>
          </div>
        `
          )
          .join('')}
      </div>
    </div>
  `;
}

function renderDetailTab(item) {
  if (!item) return `<div class="p-4 text-center text-slate-400">No item selected</div>`;

  return `
    <div class="p-3 space-y-3">
      <!-- Overview Card -->
      <div class="glass-panel p-4 rounded-xl space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-indigo-300">${getEventTypeBadge(item.decision.event_type)}</span>
          ${getUrgencyBadge(item.decision.urgency_score)}
        </div>
        <h2 class="text-sm font-semibold text-white leading-snug">${item.subject}</h2>
        <p class="text-xs text-slate-400 font-mono">From: ${item.sender}</p>
      </div>

      <!-- Action / Routing Destination Card -->
      ${
        item.routing.client_notice
          ? `
        <div class="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-emerald-300 flex items-center gap-1">
              ✨ Gemini Client Notice Generated
            </span>
            <span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Actionable</span>
          </div>
          <div class="text-xs font-medium text-white">${item.routing.client_notice.subject}</div>
          <div class="text-[11px] text-emerald-200/80 bg-black/30 p-2.5 rounded-lg border border-emerald-500/20 whitespace-pre-wrap leading-relaxed font-sans">
${item.routing.client_notice.full_email_body}
          </div>
          <div class="text-[10px] text-slate-400 flex justify-between">
            <span>Deadline: ${item.routing.client_notice.deadline}</span>
            <span>Options: ${item.routing.client_notice.election_options.length} choices</span>
          </div>
        </div>
      `
          : item.routing.hitl_item
          ? `
        <div class="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-amber-300 flex items-center gap-1">
              ⚠️ Routed to Human-in-the-Loop Desk
            </span>
            <span class="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded">Risk: ${item.routing.hitl_item.risk_level}</span>
          </div>
          <p class="text-xs text-slate-200"><strong class="text-amber-200">Reason:</strong> ${item.routing.hitl_item.reason}</p>
          <p class="text-xs text-slate-300"><strong class="text-amber-200">Suggested Action:</strong> ${item.routing.hitl_item.suggested_action}</p>
        </div>
      `
          : ''
      }

      <!-- Stage 1 & 2 Execution Metrics -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="glass-panel p-3 rounded-xl space-y-1">
          <div class="text-[10px] text-slate-400 uppercase tracking-wider">Ingestion Gate (Noul)</div>
          <div class="font-bold text-sm ${item.gate.requires_heavy_ocr ? 'text-cyan-400' : 'text-slate-200'}">
            ${item.gate.requires_heavy_ocr ? 'OCR Required' : 'Raw Text Envelope'}
          </div>
          <div class="text-[10px] text-slate-400">Prob: ${(item.gate.ocr_probability * 100).toFixed(1)}%</div>
        </div>
        <div class="glass-panel p-3 rounded-xl space-y-1">
          <div class="text-[10px] text-slate-400 uppercase tracking-wider">Actionable (Noul)</div>
          <div class="font-bold text-sm ${item.decision.is_actionable ? 'text-emerald-400' : 'text-slate-300'}">
            ${item.decision.is_actionable ? 'Action Required' : 'Informational Only'}
          </div>
          <div class="text-[10px] text-slate-400">Prob: ${(item.decision.is_actionable_probability * 100).toFixed(1)}%</div>
        </div>
      </div>

      <!-- Raw Email & Normalized Text Accordion -->
      <div class="glass-panel p-3 rounded-xl space-y-2">
        <h3 class="text-xs font-bold text-slate-200">Normalized Text Envelope Matrix</h3>
        <pre class="text-[10px] font-mono text-slate-300 bg-black/40 p-2.5 rounded-lg border border-slate-800 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-48">${
          item.normalized_preview || item.body
        }</pre>
      </div>
    </div>
  `;
}

function renderPipelineTab(item) {
  return `
    <div class="p-3 space-y-3">
      <div class="glass-panel p-3.5 rounded-xl space-y-1.5">
        <h2 class="text-xs font-bold text-indigo-300 uppercase tracking-wider">Corporate Actions 4-Stage Architecture</h2>
        <p class="text-[11px] text-slate-400 leading-relaxed">
          Ultra-fast TypeSafe AI Jev System One decision engine combined with Gemini Vision OCR.
        </p>
      </div>

      <!-- Pipeline Steps -->
      <div class="space-y-2 text-xs">
        <!-- Stage 1 -->
        <div class="glass-panel p-3 rounded-xl border-l-4 border-l-indigo-500 space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-bold text-white">Stage 1: Jev Ingestion Gate</span>
            <span class="text-[10px] font-mono text-indigo-400">Noul Evaluation</span>
          </div>
          <p class="text-[11px] text-slate-400">Evaluates Subject, Body & Meta to decide if heavy OCR/Vision is required.</p>
          <div class="text-[10px] text-slate-300 font-mono bg-black/30 p-1.5 rounded">
            requires_heavy_ocr: ${item.gate.requires_heavy_ocr} (${(item.gate.ocr_probability * 100).toFixed(1)}%)
          </div>
        </div>

        <!-- Stage 2 -->
        <div class="glass-panel p-3 rounded-xl border-l-4 border-l-cyan-500 space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-bold text-white">Stage 2: Conditional OCR</span>
            <span class="text-[10px] font-mono text-cyan-400">Gemini Vision</span>
          </div>
          <p class="text-[11px] text-slate-400">Extracts text and tables from attached PDFs/Images into a normalized envelope matrix.</p>
          <div class="text-[10px] text-slate-300 font-mono bg-black/30 p-1.5 rounded">
            OCR Executed: ${item.ocr_applied ? 'Yes (Flattened Attachment)' : 'No (Direct Raw Text)'}
          </div>
        </div>

        <!-- Stage 3 -->
        <div class="glass-panel p-3 rounded-xl border-l-4 border-l-amber-500 space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-bold text-white">Stage 3: Jev Core Decision</span>
            <span class="text-[10px] font-mono text-amber-400">Choice + Noul + Score</span>
          </div>
          <p class="text-[11px] text-slate-400">Classifies Event Type (Choice), Actionability (Noul), and Urgency 1-10 (Score).</p>
          <div class="text-[10px] text-slate-300 font-mono bg-black/30 p-1.5 rounded flex justify-between">
            <span>Event: ${item.decision.event_type}</span>
            <span>Urgency: ${item.decision.urgency_score}/10</span>
          </div>
        </div>

        <!-- Stage 4 -->
        <div class="glass-panel p-3 rounded-xl border-l-4 border-l-emerald-500 space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-bold text-white">Stage 4: Router Execution</span>
            <span class="text-[10px] font-mono text-emerald-400">Gemini / HITL</span>
          </div>
          <p class="text-[11px] text-slate-400">Actionable items get Gemini client notices; informational/exceptions route to HITL desk.</p>
          <div class="text-[10px] text-slate-300 font-mono bg-black/30 p-1.5 rounded">
            Route: ${item.routing.route}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderInfoTab() {
  return `
    <div class="p-3 space-y-3 text-xs">
      <div class="glass-panel p-4 rounded-xl space-y-2">
        <h2 class="text-sm font-bold text-white">⚡ About Jev AI Mobile Demo</h2>
        <p class="text-slate-300 leading-relaxed">
          This Android application provides a live mobile interface for testing and demonstrating the Corporate Actions Email Decision Engine.
        </p>
        <div class="border-t border-slate-800 pt-2 space-y-1 text-slate-400">
          <div>• <strong>Engine:</strong> TypeSafe AI Jev (System One)</div>
          <div>• <strong>OCR & Drafting:</strong> Gemini 2.5 Flash / Vision</div>
          <div>• <strong>Platform:</strong> Android (Capacitor Native)</div>
          <div>• <strong>Package:</strong> com.genaiapps.jevaiflow</div>
          <div>• <strong>Release Track:</strong> Internal & Closed Testing</div>
        </div>
      </div>

      <div class="glass-panel p-4 rounded-xl space-y-2">
        <h3 class="text-xs font-bold text-white">Demo Instructions for Presenters</h3>
        <ol class="list-decimal list-inside space-y-1.5 text-slate-300">
          <li>Browse the queue sorted automatically by <strong>Urgency Score (1-10)</strong>.</li>
          <li>Tap on <strong>Urgent Merger (Proxy attached)</strong> to showcase automatic OCR triggering.</li>
          <li>Tap on <strong>Voluntary Tender Offer</strong> to view the Gemini structured client notice draft.</li>
          <li>Tap on <strong>Custodian Reconciliation Break</strong> to demonstrate human-in-the-loop exception safety.</li>
        </ol>
      </div>
    </div>
  `;
}

function bindEvents() {
  // Navigation tabs
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const tab = e.currentTarget.getAttribute('data-tab');
      if (tab) {
        state.activeTab = tab;
        render();
      }
    });
  });

  // Filter pills
  document.querySelectorAll('.filter-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const filter = e.currentTarget.getAttribute('data-filter');
      if (filter) {
        state.filter = filter;
        render();
      }
    });
  });

  // Select item from queue
  document.querySelectorAll('.item-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      if (id) {
        state.selectedId = id;
        state.activeTab = 'detail';
        render();
      }
    });
  });

  // Rerun button
  const rerunBtn = document.getElementById('run-pipeline-btn');
  if (rerunBtn) {
    rerunBtn.addEventListener('click', () => {
      rerunBtn.classList.add('animate-spin');
      setTimeout(() => {
        rerunBtn.classList.remove('animate-spin');
      }, 500);
    });
  }
}

// Initial mount
render();
