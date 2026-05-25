(function () {
  const body = document.body;
  const THEME_KEY = 'sf_theme';

  function byId(id) { return document.getElementById(id); }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'default';
    applyTheme(saved);
  }

  function applyTheme(name) {
    body.classList.remove('theme-dark', 'theme-tokyo');
    if (name === 'dark') body.classList.add('theme-dark');
    else if (name === 'light') { }
    else { body.classList.add('theme-tokyo'); }
    localStorage.setItem(THEME_KEY, name);
  }

  window.setTheme = function (name) { applyTheme(name); showToast('Theme set to ' + name); };

  window.toggleDropdown = function (id) { const el = byId(id); if (!el) return; closeAllDropdowns(); el.classList.toggle('show'); };
  window.closeAllDropdowns = function () { document.querySelectorAll('.dropdown-menu.show').forEach(d => d.classList.remove('show')); };

  window.toggleHistory = function () { const p = byId('history-panel'); if (!p) return; p.classList.toggle('-translate-x-full'); };

  window.toggleHookPanel = function () { const p = byId('hook-panel'); if (!p) return; if (p.style.transform === 'translateX(0%)') p.style.transform = 'translateX(100%)'; else p.style.transform = 'translateX(0%)'; };

  function showModal(id) { const m = byId(id); if (m) { m.classList.add('active'); } }
  function hideModal(id) { const m = byId(id); if (m) { m.classList.remove('active'); } }
  window.openFolderModal = function () { showModal('folder-modal'); }
  window.closeFolderModal = function () { hideModal('folder-modal'); }
  window.openSettingsModal = function () { showModal('settings-modal'); }
  window.closeSettingsModal = function () { hideModal('settings-modal'); }

  window.submitFolderCreation = function () { const val = (byId('fm-input') || { value: '' }).value.trim(); if (!val) { showToast('Please enter a folder name'); return; } showToast('Created folder: ' + val); closeFolderModal(); };

  let _confirmCb = null;
  function showConfirm(title, msg, cb) { const t = byId('confirm-title'); const m = byId('confirm-msg'); t && (t.textContent = title || 'Are you sure?'); m && (m.textContent = msg || 'This action cannot be undone.'); _confirmCb = cb; showModal('confirm-modal'); }
  byId('btn-cancel-confirm')?.addEventListener('click', () => { hideModal('confirm-modal'); _confirmCb = null; });
  byId('btn-do-confirm')?.addEventListener('click', () => { hideModal('confirm-modal'); if (typeof _confirmCb === 'function') _confirmCb(); _confirmCb = null; });

  window.toggleSelectMode = function () { showToast('Toggled select mode'); };

  window.openMergePanel = function () { showModal('merge-panel'); };
  window.closeMergePanel = function () { hideModal('merge-panel'); };
  window.saveEditedReport = function () { showToast('Saved edited report'); };
  window.smartPushHooks = function () { showToast('Pushed hooks into report'); };
  window.deleteAllHooks = function () { showConfirm('Delete hooks', 'Delete all hooks?', () => showToast('All hooks deleted')); };

  let toastTimer = null;
  window.showToast = function (msg, timeout = 2500) { const t = byId('toast-notification'); const m = byId('toast-message'); if (!t || !m) return console.log('Toast:', msg); m.textContent = msg; t.classList.remove('translate-y-full'); t.style.transform = 'translateY(0)'; clearTimeout(toastTimer); toastTimer = setTimeout(() => { hideToast(); }, timeout); };
  window.hideToast = function () { const t = byId('toast-notification'); if (t) { t.style.transform = 'translateY(100%)'; } };

  window.resetDatabase = function () { showConfirm('Reset Database', 'This will reset local database. Continue?', () => showToast('Database reset (stub)')); };

  window.triggerGlobalDownload = function (fmt) { const form = byId('dl-helper-form'); if (!form) { showToast('Download form not found'); return; } byId('hlp-format').value = fmt; byId('hlp-content').value = (document.querySelector('#merge-report-content') || { value: '' }).value; form.submit(); showToast('Preparing download: ' + fmt); hideGlobalMenu(); };
  window.hideGlobalMenu = function () { const g = byId('global-download-menu'); if (g) g.classList.add('hidden'); };

  document.addEventListener('click', (e) => { if (!e.target.closest('.dropdown-menu') && !e.target.closest('[onclick*="toggleDropdown"]')) closeAllDropdowns(); });
  document.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); const btn = byId('sidebar-search-btn'); if (btn) btn.click(); } if (e.key === 'Escape') { closeAllDropdowns(); hideModal('settings-modal'); hideModal('folder-modal'); } });

  document.addEventListener('DOMContentLoaded', () => { initTheme(); });

  window.toggleCustomSelect = function (id) {
    const opts = document.getElementById(id + '-options');
    if (opts) opts.classList.toggle('hidden');
  };

  window.selectCustomOption = function (value, text, inputId, changeCb) {
    const hidden = document.getElementById(inputId);
    const trigger = document.getElementById(inputId + '-trigger-text');
    if (hidden) hidden.value = value;
    if (trigger) trigger.textContent = text;
    document.getElementById(inputId + '-options')?.classList.add('hidden');
    if (changeCb && typeof window[changeCb] === 'function') window[changeCb](value);
    else if (changeCb === 'handleFormatChange' && typeof handleFormatChange === 'function') handleFormatChange(value);
  };

  window.handleFormatChange = function (val) {
    const el = document.getElementById('custom-format-container');
    if (val === 'custom') el?.classList.remove('hidden');
    else el?.classList.add('hidden');
  };

  window.updateFileName = function (el) {
    const fname = (el.files && el.files.length > 0) ? el.files[0].name : 'Upload Knowledge Base';
    const display = document.getElementById('file-name');
    if (display) display.textContent = fname;
  };

  window.copyToClipboard = function () { const text = document.getElementById('report-output')?.innerText || ''; navigator.clipboard?.writeText(text).then(() => showToast('Copied to clipboard')); };

  window.downloadFile = function (fmt) { showToast('Downloading ' + fmt + ' (stub)'); };

  window.resetView = function () {
    document.getElementById('report-output').innerHTML = '';
    document.getElementById('results-container')?.classList.add('hidden');
    document.getElementById('input-section')?.classList.remove('hidden');
    byId('progress-section')?.classList.add('hidden');
    document.querySelectorAll('.progress-step').forEach(el => { el.style.opacity = '0'; el.classList.remove('scale-100'); el.classList.add('scale-95'); });
    byId('progress-line-fill').style.height = '0';
    showToast('Ready for new report');
  };

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('report-form');
    form?.addEventListener('submit', function (e) {
      e.preventDefault();
      startResearchSequence();
    });

    document.addEventListener('click', function (e) {
      if (!e.target.closest('.relative.group')) {
        document.querySelectorAll('[id$="-options"]').forEach(el => el.classList.add('hidden'));
      }
    });
  });

  function startResearchSequence() {
    const form = document.getElementById('report-form');
    if (!form) return;

    const inputSec = document.getElementById('input-section');
    const progSec = document.getElementById('progress-section');
    const submitBtn = document.getElementById('submit-btn');
    const useCouncil = document.getElementById('council-toggle')?.checked; // Check toggle status

    if (!inputSec || !progSec) return showToast('Error: UI sections missing');

    if (submitBtn) { submitBtn.disabled = true; submitBtn.style.opacity = '0.7'; }

    const formData = new FormData(form);

    inputSec.classList.add('hidden');
    progSec.classList.remove('hidden');

    // Toggle View Mode
    if (useCouncil) {
      document.getElementById('standard-progress')?.classList.add('hidden');
      document.getElementById('council-animation-container')?.classList.remove('hidden');
      updateCouncilAnim('Initializing Council...');
    } else {
      document.getElementById('standard-progress')?.classList.remove('hidden');
      document.getElementById('council-animation-container')?.classList.add('hidden');
      document.getElementById('std-progress-bar').style.width = '5%';
      animateStep(1);
    }

    fetch(window.START_REPORT_URL, {
      method: 'POST',
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        if (data.task_id) {
          connectWebSocketProgress(data.task_id, useCouncil);
        } else {
          throw new Error('No task ID returned');
        }
      })
      .catch(e => {
        console.error(e);
        showToast('Failed to start: ' + e.message);
        setTimeout(resetView, 2000);
      });
  }

  function animateStep(num) {
    // Update progress bar width
    const bar = document.getElementById('std-progress-bar');
    if (bar) bar.style.width = (num * 25) + '%';

    const checkSVG = '<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>';
    const spinSVG = '<svg class="w-3 h-3 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';

    for (let i = 1; i <= 4; i++) {
      const step = document.getElementById('std-step-' + i);
      const icon = document.getElementById('std-icon-' + i);
      const label = document.getElementById('std-label-' + i);
      if (!step || !icon) continue;

      if (i < num) {
        // Completed
        icon.className = 'w-5 h-5 flex-shrink-0 rounded-full flex items-center justify-center bg-emerald-500';
        icon.innerHTML = checkSVG;
        if (label) label.classList.add('text-[var(--text-main)]');
        step.style.opacity = '1';
      } else if (i === num) {
        // Active / Processing
        icon.className = 'w-5 h-5 flex-shrink-0 rounded-full flex items-center justify-center border-2 border-blue-400';
        icon.innerHTML = spinSVG;
        if (label) {
          label.classList.add('text-[var(--text-main)]', 'font-semibold');
        }
        step.style.opacity = '1';
      } else {
        // Pending
        icon.className = 'std-step-icon w-5 h-5 flex-shrink-0 rounded-full border-2 border-[var(--border-color)] flex items-center justify-center';
        icon.innerHTML = '';
        if (label) {
          label.classList.remove('text-[var(--text-main)]', 'font-semibold');
        }
        step.style.opacity = '0.5';
      }
    }
  }

  // --- Council Animation Helpers ---
  function updateCouncilAnim(msg) {
    const statusText = document.getElementById('council-status-text');
    const phaseTitle = document.getElementById('council-phase-title');
    if (!statusText || !phaseTitle) return;

    statusText.textContent = msg.length > 50 ? msg.substring(0, 47) + '...' : msg;
    const fill = document.getElementById('council-flow-fill');
    
    function resetNodes() {
        ['legion', 'nexus', 'inquisitor', 'artisan'].forEach(node => {
            const el = document.getElementById('agent-node-' + node);
            const circle = document.getElementById('agent-circle-' + node);
            if (el) el.className = "flex flex-col items-center text-center z-10 opacity-30 transition-all duration-500";
            if (circle) circle.className = "w-14 h-14 rounded-full bg-[var(--bg-panel)] border-2 border-[var(--border-color)] flex items-center justify-center shadow-lg transition-all duration-500 text-[var(--text-muted)]";
        });
    }

    function highlightNode(node, colorClass) {
        resetNodes();
        const el = document.getElementById('agent-node-' + node);
        const circle = document.getElementById('agent-circle-' + node);
        if (el) el.className = "flex flex-col items-center text-center z-10 opacity-100 scale-110 transition-all duration-500";
        if (circle) circle.className = `w-14 h-14 rounded-full bg-[var(--bg-panel)] border-2 ${colorClass} flex items-center justify-center shadow-lg transition-all duration-500`;
    }

    if (msg.includes('Step 1') || msg.includes('Step 2') || msg.includes('Processing') || msg.includes('Inputs')) {
      phaseTitle.textContent = "Processing Raw Context";
      if (fill) fill.style.width = '0%';
    }
    else if (msg.includes('Step 3') || msg.includes('Search') || msg.includes('Synthesizing') || msg.includes('Summary')) {
      phaseTitle.textContent = "Synthesizing Fact-Base";
      if (fill) fill.style.width = '12%';
    }
    else if (msg.includes('Legion') || msg.includes('variants')) {
      phaseTitle.textContent = "Council: Agent Legion";
      highlightNode('legion', 'border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)] animate-pulse');
      if (fill) fill.style.width = '25%';
    }
    else if (msg.includes('Nexus') || msg.includes('merging') || msg.includes('Outline') || msg.includes('Step 5')) {
      phaseTitle.textContent = "Council: Agent Nexus";
      highlightNode('nexus', 'border-purple-500 text-purple-500 shadow-[0_0_15px_rgba(139,92,246,0.5)] animate-pulse');
      if (fill) fill.style.width = '50%';
    }
    else if (msg.includes('Review') || msg.includes('Inquisitor') || msg.includes('Cycle') || msg.includes('Score') || msg.includes('critique')) {
      phaseTitle.textContent = "Council: Inquisitor Audit";
      highlightNode('inquisitor', 'border-rose-500 text-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.5)] animate-pulse');
      if (fill) fill.style.width = '75%';
    }
    else if (msg.includes('Artisan') || msg.includes('Formatting') || msg.includes('Polish') || msg.includes('Step 6') || msg.includes('Writing')) {
      phaseTitle.textContent = "Council: Artisan Publisher";
      highlightNode('artisan', 'border-emerald-500 text-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)] animate-pulse');
      if (fill) fill.style.width = '90%';
    }
    else if (msg.includes('Step 7') || msg.includes('Finalizing')) {
      phaseTitle.textContent = "Compiling Artifact";
      if (fill) fill.style.width = '100%';
    }
  }

  function finishCouncilAnim() {
    const fill = document.getElementById('council-flow-fill');
    if (fill) fill.style.width = '100%';
    ['legion', 'nexus', 'inquisitor', 'artisan'].forEach(node => {
        const el = document.getElementById('agent-node-' + node);
        const circle = document.getElementById('agent-circle-' + node);
        if (el) el.className = "flex flex-col items-center text-center z-10 opacity-100 scale-100 transition-all duration-500";
        if (circle) circle.className = "w-14 h-14 rounded-full bg-[var(--bg-panel)] border-2 border-emerald-500 text-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.4)] flex items-center justify-center shadow-lg transition-all duration-500";
    });
  }

  function connectWebSocketProgress(taskId, useCouncil = false) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + window.location.host + '/ws/progress/' + taskId;
    const socket = new WebSocket(wsUrl);

    socket.onopen = function () {
      console.log('WebSocket connected for task:', taskId);
    };

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);

      if (data.status === 'SUCCESS') {
        if (useCouncil) {
          updateCouncilAnim('Finalizing manuscript...');
          finishCouncilAnim();
          setTimeout(() => {
            displayResults(data);
            socket.close();
          }, 1200);
        } else {
          animateStep(4);
          setTimeout(() => {
            displayResults(data);
            socket.close();
          }, 1000);
        }
      } else if (data.status === 'FAILURE') {
        showToast('Error: ' + (data.error || 'Research failed'));
        setTimeout(() => {
          resetView();
          socket.close();
        }, 3000);
      } else {
        const msg = data.message || '';
        if (useCouncil) {
          updateCouncilAnim(msg);
        } else {
          if (msg.includes('Step 1') || msg.includes('Step 2')) animateStep(1);
          else if (msg.includes('Step 3') || msg.includes('Search')) animateStep(1);
          else if (msg.includes('Step 4') || msg.includes('Visuals')) animateStep(2);
          else if (msg.includes('Step 5') || msg.includes('Structure')) animateStep(2);
          else if (msg.includes('Step 6') || msg.includes('Writing')) animateStep(3);
          else if (msg.includes('Step 7')) animateStep(4);
        }
      }
    };

    socket.onerror = function (error) {
      console.error('WebSocket error:', error);
    };

    socket.onclose = function () {
      console.log('WebSocket connection closed');
    };
  }

  function displayResults(data) {
    const progSec = document.getElementById('progress-section');
    const resSec = document.getElementById('results-container');

    progSec.classList.add('hidden');
    if (resSec) {
      resSec.classList.remove('hidden');
      resSec.style.opacity = '0';
      setTimeout(() => resSec.style.opacity = '1', 50);

      let content = data.report_content || '';

      // Use Marked for full Markdown rendering including tables
      if (typeof marked !== 'undefined') {
        content = marked.parse(content);
      } else {
        // Fallback if marked not loaded
        content = content.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        content = content.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        content = content.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/^\* (.*$)/gim, '<ul><li>$1</li></ul>');
        content = content.replace(/<\/ul>\s*<ul>/g, '');
        content = content.replace(/\n\n/g, '<br><br>');
      }

      // Convert [1], [2] to interactive badges
      content = content.replace(/\[(\d+)\]/g, (match, num) => {
        return `<span class="citation-badge bg-blue-500/10 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/20 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold inline-flex items-center justify-center cursor-pointer transition-all duration-300 shadow-sm" data-citation="${num}">[${num}]</span>`;
      });

      if (data.chart_path) {
        content = `<div class="mb-8 p-4 bg-white/5 rounded-xl border border-white/10 flex justify-center"><img src="/${data.chart_path}" class="max-w-full rounded-lg shadow-lg" alt="Analysis Chart"></div>` + content;
      }

      document.getElementById('report-output').innerHTML = content;

      // Bind smooth scroll and highlight handlers for citation clicks
      document.getElementById('report-output').querySelectorAll('.citation-badge').forEach(badge => {
        badge.addEventListener('click', function(e) {
          e.preventDefault();
          const num = this.getAttribute('data-citation');
          const outputEl = document.getElementById('report-output');
          const allEls = outputEl.querySelectorAll('p, li, div');
          let targetEl = null;
          for (let el of allEls) {
            const text = el.textContent.trim();
            if (text.startsWith('[' + num + ']') && !el.classList.contains('citation-badge')) {
              targetEl = el;
              break;
            }
          }
          if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            targetEl.style.transition = 'background-color 0.5s ease';
            targetEl.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
            setTimeout(() => {
              targetEl.style.backgroundColor = 'transparent';
            }, 2000);
          } else {
            showToast('Reference [' + num + '] is detailed at the bottom of the report.');
          }
        });
      });

      document.getElementById('result-topic-display').textContent = document.getElementById('query').value;

      document.getElementById('dl-content').value = data.report_content;
      document.getElementById('dl-topic').value = document.getElementById('query').value;
      document.getElementById('dl-format').value = document.getElementById('format-select').value;
      document.getElementById('dl-chart-path').value = data.chart_path || '';

      // Refresh history
      if (typeof window.loadHistory === 'function') window.loadHistory();
    }
  }

  window.downloadFile = function (fmt) {
    const form = document.getElementById('download-form');
    if (form) {
      document.getElementById('dl-format').value = fmt;
      form.submit();
      showToast('Downloading ' + fmt.toUpperCase() + '...');
    }
  };

  window.viewReport = function (id) {
    if (window.innerWidth < 768) toggleHistory(); // Close panel on mobile

    resetView();
    // Show loading state
    document.getElementById('input-section')?.classList.add('hidden');
    document.getElementById('progress-section')?.classList.add('hidden');
    const resSec = document.getElementById('results-container');
    if (resSec) resSec.classList.remove('hidden');
    document.getElementById('report-output').innerHTML = '<div class="p-8 text-center text-[var(--text-muted)]">Loading report...</div>';

    fetch('/api/report/' + id)
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        displayResults({ report_content: data.content, chart_path: null }); // Assuming stored reports are just text for now
        // Update title override
        document.getElementById('result-topic-display').textContent = data.topic;
        document.getElementById('dl-topic').value = data.topic;
      })
      .catch(e => {
        showToast('Error loading report: ' + e.message);
        resetView();
      });
  };

  document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.loadHistory === 'function') window.loadHistory();
    
    // Check if ?report_id=X is present in the URL on load
    const urlParams = new URLSearchParams(window.location.search);
    const reportId = urlParams.get('report_id');
    if (reportId) {
      setTimeout(() => {
        window.viewReport(parseInt(reportId));
        // Clean URL parameters without reloading
        window.history.replaceState({}, document.title, "/");
      }, 300);
    }
  });

})();
