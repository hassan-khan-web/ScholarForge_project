(function () {
    const body = document.body;
    const THEME_KEY = 'sf_theme';
    let _confirmCb = null;  // For custom confirm modal

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

    window.toggleDropdown = function (id) {
        const el = byId(id);
        if (!el) return;
        const key = el.classList.contains('show');
        closeAllDropdowns();
        if (!key) el.classList.add('show');
    };
    window.closeAllDropdowns = function () { document.querySelectorAll('.dropdown-menu.show').forEach(d => d.classList.remove('show')); };

    window.toggleHistory = function () {
        const p = byId('history-panel');
        if (!p) return;
        p.classList.toggle('-translate-x-full');
        if (!p.classList.contains('-translate-x-full')) {
            if (typeof window.loadHistory === 'function') window.loadHistory();
        }
    };

    window.toggleHookPanel = function () { const p = byId('hook-panel'); if (!p) return; if (p.style.transform === 'translateX(0%)') { p.style.transform = 'translateX(100%)'; } else { p.style.transform = 'translateX(0%)'; if (window.fetchHooks) window.fetchHooks(); } };

    function showModal(id) { const m = byId(id); if (m) { m.classList.add('active'); if (id === 'folder-modal') setTimeout(() => byId('fm-input')?.focus(), 100); } }
    function hideModal(id) { const m = byId(id); if (m) { m.classList.remove('active'); } }
    window.openFolderModal = function () { showModal('folder-modal'); }
    window.closeFolderModal = function () { hideModal('folder-modal'); }
    window.openSettingsModal = function () { showModal('settings-modal'); }
    window.closeSettingsModal = function () { hideModal('settings-modal'); }

    let toastTimer = null;
    window.showToast = function (msg, timeout = 2500) {
        const toastEl = byId('toast-notification');
        if (!toastEl) return;
        
        clearTimeout(toastTimer);
        toastEl.textContent = msg;
        toastEl.classList.remove('hidden');
        toastEl.classList.add('show');
        
        toastTimer = setTimeout(() => {
            toastEl.classList.remove('show');
            setTimeout(() => {
                toastEl.classList.add('hidden');
            }, 300);
        }, timeout);
    };
    window.hideToast = function () {
        const toastEl = byId('toast-notification');
        if (toastEl) {
            clearTimeout(toastTimer);
            toastEl.classList.remove('show');
            toastEl.classList.add('hidden');
        }
    };

    let currentFolders = [];

    document.addEventListener('DOMContentLoaded', () => {
        initTheme();
        fetchFolders();
        if (typeof window.loadHistory === 'function') window.loadHistory();

        // Attach confirm modal event listeners
        byId('btn-cancel-confirm')?.addEventListener('click', () => {
            hideModal('confirm-modal');
            _confirmCb = null;
        });

        byId('btn-do-confirm')?.addEventListener('click', () => {
            hideModal('confirm-modal');
            if (typeof _confirmCb === 'function') _confirmCb();
            _confirmCb = null;
        });
    });

    window.submitFolderCreation = async function () {
        const input = byId('fm-input');
        const name = (input?.value || '').trim();
        if (!name) { showToast('Please enter a folder name'); return; }

        try {
            const res = await fetch('/api/folders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Created project: ' + name);
                closeFolderModal();
                input.value = '';
                await createSession(data.folder.id, "New Research", true);
            } else {
                showToast(data.error || 'Failed to create folder');
            }
        } catch (e) {
            console.error(e);
            showToast('Error creating folder');
        }
    };

    async function fetchFolders() {
        try {
            const res = await fetch('/api/folders');
            currentFolders = await res.json();
            renderFolderTree();

            // Check if we need to reset to welcome state (only on chat page)
            if (window.resetToWelcomeState && typeof window.resetToWelcomeState === 'function') {
                const currentSessionId = localStorage.getItem('currentChatSessionId');
                if (currentSessionId) {
                    let sessionExists = false;
                    // Deep search for session in folders
                    for (const folder of currentFolders) {
                        if (folder.sessions && folder.sessions.some(s => s.id.toString() === currentSessionId.toString())) {
                            sessionExists = true;
                            break;
                        }
                    }

                    if (!sessionExists) {
                        window.resetToWelcomeState();
                        showToast('Session closed or deleted');
                    }
                } else {
                    // No session selected, ensure we are in welcome state
                    // This handles the case where user manually cleared storage or landed on page fresh
                    const welcome = document.getElementById('welcome-state');
                    if (welcome && welcome.classList.contains('hidden')) {
                        window.resetToWelcomeState();
                    }
                }
            }
        } catch (e) { console.error('Error fetching folders:', e); }
    }
    window.refreshFolders = fetchFolders;

    function renderFolderTree() {
        const container = byId('folder-tree-container');
        if (!container) return;

        container.classList.remove('hidden');
        container.innerHTML = '';

        if (currentFolders.length === 0) return;

        currentFolders.forEach(folder => {
            const folderEl = document.createElement('div');
            folderEl.className = 'mb-1';

            const header = document.createElement('div');
            header.className = 'group flex items-center justify-between px-3 py-2 hover:bg-[var(--hover-bg)] rounded-lg cursor-pointer transition-colors';

            header.onclick = (e) => {
                if (!e.target.closest('.folder-action')) toggleFolder(folder.id);
            };

            header.innerHTML = `
                <div class="flex items-center gap-2 overflow-hidden">
                    <svg id="arrow-${folder.id}" class="w-3 h-3 text-[var(--text-muted)] transition-transform duration-200 transform -rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                    <span class="text-sm font-medium text-[var(--text-main)] whitespace-nowrap overflow-hidden text-ellipsis">${folder.name}</span>
                </div>
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="createSession(${folder.id}, 'New Chat')" class="folder-action p-1 hover:bg-blue-100 text-[var(--text-muted)] hover:text-blue-600 rounded" title="New Chat">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                    </button>
                    <button onclick="showFolderOptions(event, ${folder.id}, '${folder.name}')" class="folder-action p-1 hover:bg-gray-200 text-[var(--text-muted)] rounded" title="Options">
                         <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path></svg>
                    </button>
                </div>
            `;

            const children = document.createElement('div');
            children.id = `folder-content-${folder.id}`;
            children.className = 'hidden ml-3 border-l border-[var(--border-color)] mt-1 space-y-0.5';

            folder.sessions.forEach(session => {
                const sessEl = document.createElement('div');
                sessEl.className = 'group flex items-center justify-between px-3 py-1.5 hover:bg-[var(--hover-bg)] rounded-r-lg cursor-pointer text-xs text-[var(--text-muted)] hover:text-[var(--text-main)]';
                sessEl.onclick = (e) => {
                    if (!e.target.closest('.sess-action')) loadSessionGlobal(session.id);
                };

                sessEl.innerHTML = `
                    <span class="truncate pr-2">${session.title}</span>
                    <button onclick="showSessionOptions(event, ${session.id}, '${session.title}')" class="sess-action opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-200 rounded">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path></svg>
                    </button>
                `;
                children.appendChild(sessEl);
            });

            folderEl.appendChild(header);
            folderEl.appendChild(children);
            container.appendChild(folderEl);
        });
    }

    window.toggleFolder = function (id) {
        const content = byId(`folder-content-${id}`);
        const arrow = byId(`arrow-${id}`);
        if (content.classList.contains('hidden')) {
            content.classList.remove('hidden');
            arrow.classList.remove('-rotate-90');
        } else {
            content.classList.add('hidden');
            arrow.classList.add('-rotate-90');
        }
    };

    window.createSession = async function (folderId, title = "New Chat", redirect = false) {
        try {
            const res = await fetch('/api/sessions', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_id: folderId, title: title })
            });
            const data = await res.json();
            if (data.status === 'success') {
                await fetchFolders();
                if (redirect || window.location.pathname === '/chat') {
                    if (window.loadSession) window.loadSession(data.session.id);
                    else window.location.href = '/chat?session_id=' + data.session.id;
                } else {
                    window.location.href = '/chat';
                }

                setTimeout(() => {
                    const content = byId(`folder-content-${folderId}`);
                    if (content && content.classList.contains('hidden')) toggleFolder(folderId);
                }, 100);
            }
        } catch (e) { console.error(e); }
    };

    window.loadSessionGlobal = function (id) {
        if (window.location.pathname.includes('/chat')) {
            if (window.loadSession) window.loadSession(id);
        } else {
            window.location.href = '/chat?session_id=' + id;
        }
    };

    window.showFolderOptions = function (e, id, name) {
        e.stopPropagation();
        showContextMenu(e.clientX, e.clientY, [
            { label: 'Rename', action: () => promptRenameFolder(id, name) },
            { label: 'Delete', action: () => confirmDeleteFolder(id) }
        ]);
    };

    window.showSessionOptions = function (e, id, name) {
        e.stopPropagation();
        showContextMenu(e.clientX, e.clientY, [
            { label: 'Rename', action: () => promptRenameSession(id, name) },
            { label: 'Delete', action: () => confirmDeleteSession(id) }
        ]);
    };

    window.showContextMenu = function (x, y, options) {
        const existing = document.getElementById('custom-context-menu');
        if (existing) existing.remove();

        const menu = document.createElement('div');
        menu.id = 'custom-context-menu';
        menu.className = 'fixed bg-[var(--bg-panel)] border border-[var(--border-color)] shadow-xl rounded-lg z-[1000] py-1 w-32';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';

        options.forEach(opt => {
            const item = document.createElement('div');
            item.className = 'px-4 py-2 text-xs text-[var(--text-main)] hover:bg-[var(--hover-bg)] cursor-pointer';
            item.textContent = opt.label;
            item.onclick = () => { opt.action(); menu.remove(); };
            menu.appendChild(item);
        });

        document.body.appendChild(menu);
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 10);
    }

    // Custom themed prompt dialog
    let _promptCb = null;

    function showPrompt(title, msg, value, cb) {
        const t = byId('prompt-title');
        const m = byId('prompt-msg');
        const i = byId('prompt-input');
        if (t) t.textContent = title || 'Enter Value';
        if (m) m.textContent = msg || '';
        if (i) { i.value = value || ''; }
        _promptCb = cb;
        showModal('prompt-modal');
        setTimeout(() => i?.focus(), 100);
    }

    byId('btn-cancel-prompt')?.addEventListener('click', () => { hideModal('prompt-modal'); _promptCb = null; });
    byId('btn-do-prompt')?.addEventListener('click', () => {
        const val = byId('prompt-input')?.value;
        hideModal('prompt-modal');
        if (typeof _promptCb === 'function') _promptCb(val);
        _promptCb = null;
    });

    // Custom themed confirm dialog
    function showConfirm(title, msg, cb) {
        const t = byId('confirm-title');
        const m = byId('confirm-msg');
        if (t) t.textContent = title || 'Are you sure?';
        if (m) m.textContent = msg || 'This action cannot be undone.';
        _confirmCb = cb;
        showModal('confirm-modal');
    }

    function promptRenameFolder(id, oldName) {
        showPrompt("Rename Project", "Enter a new name for this project:", oldName, (n) => {
            if (n && n !== oldName) {
                fetch(`/api/folders/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ new_name: n }) })
                    .then(fetchFolders);
            }
        });
    }

    function confirmDeleteFolder(id) {
        showConfirm("Delete Project", "Delete this folder and all its chats? This cannot be undone.", () => {
            fetch(`/api/folders/${id}`, { method: 'DELETE' }).then(fetchFolders);
        });
    }

    function promptRenameSession(id, oldName) {
        showPrompt("Rename Chat", "Enter a new title for this chat:", oldName, (n) => {
            if (n && n !== oldName) {
                fetch(`/api/sessions/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ new_name: n }) })
                    .then(fetchFolders);
            }
        });
    }

    function confirmDeleteSession(id) {
        showConfirm("Delete Chat", "Delete this chat? This cannot be undone.", () => {
            fetch(`/api/sessions/${id}`, { method: 'DELETE' }).then(fetchFolders);
        });
    }

    // ============================================
    // MERGE PANEL FUNCTIONS
    // ============================================

    let currentMergeReportId = null;
    let currentMergeTab = 'preview';

    window.openMergePanel = function () {
        showModal('merge-panel');
        loadMergeReports();
        loadMergeHooks();
        currentMergeReportId = null;
        
        // Show empty state, hide content area
        const emptyState = byId('merge-empty-state');
        const contentArea = byId('merge-content-area');
        if (emptyState) {
            emptyState.classList.remove('hidden');
            emptyState.classList.add('flex');
        }
        if (contentArea) {
            contentArea.classList.add('hidden');
            contentArea.classList.remove('flex');
        }
    };

    window.closeMergePanel = function () {
        hideModal('merge-panel');
        currentMergeReportId = null;
        byId('merge-report-content').value = '';
        byId('merge-report-title').textContent = '';
        byId('merge-report-preview').innerHTML = '';
    };

    window.setMergeTab = function (tab) {
        currentMergeTab = tab;
        const btnPreview = byId('merge-tab-preview');
        const btnEdit = byId('merge-tab-edit');
        const previewContainer = byId('merge-report-preview-container');
        const editContainer = byId('merge-report-edit-container');
        const indicator = byId('merge-tab-indicator');

        if (!btnPreview || !btnEdit || !previewContainer || !editContainer) return;

        // Clean up any remaining background classes from the buttons
        btnPreview.classList.remove('bg-[var(--accent-primary)]');
        btnEdit.classList.remove('bg-[var(--accent-primary)]');

        if (tab === 'preview') {
            if (indicator) {
                indicator.style.left = '0.125rem';
                indicator.style.width = ''; // Let CSS w-[calc(50%-2px)] determine width
            }
            btnPreview.classList.add('text-white');
            btnPreview.classList.remove('text-[var(--text-muted)]', 'hover:text-[var(--text-main)]');
            btnEdit.classList.add('text-[var(--text-muted)]');
            btnEdit.classList.remove('text-white');
            
            previewContainer.classList.remove('hidden');
            editContainer.classList.add('hidden');
            
            // Render the text from textarea into preview
            const content = byId('merge-report-content').value;
            renderMergePreview(content);
        } else {
            if (indicator) {
                indicator.style.left = '50%';
                indicator.style.width = ''; // Let CSS w-[calc(50%-2px)] determine width
            }
            btnPreview.classList.remove('text-white');
            btnPreview.classList.add('text-[var(--text-muted)]', 'hover:text-[var(--text-main)]');
            btnEdit.classList.add('text-white');
            btnEdit.classList.remove('text-[var(--text-muted)]');
            
            editContainer.classList.remove('hidden');
            previewContainer.classList.add('hidden');
        }
    };

    function renderMergePreview(markdownText, highlightOriginal = null) {
        const previewEl = byId('merge-report-preview');
        if (!previewEl) return;
        
        let htmlContent = '';
        
        // If we have an original content to diff against, calculate highlights!
        let processedText = markdownText;
        if (highlightOriginal) {
            processedText = diffTexts(highlightOriginal, markdownText);
        }
        
        if (typeof marked !== 'undefined') {
            htmlContent = marked.parse(processedText || '*No content*');
        } else {
            // Fallback
            htmlContent = (processedText || '*No content*')
                .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n\n/g, '<br><br>');
        }
        
        previewEl.innerHTML = htmlContent;
    }

    function diffTexts(original, modified) {
        const origLines = original.split('\n').map(l => l.trim()).filter(Boolean);
        const modLines = modified.split('\n');
        
        const markedLines = modLines.map(line => {
            const trimmed = line.trim();
            if (!trimmed) return line;
            
            // Check if the trimmed line is present in the original report lines
            const exists = origLines.some(orig => orig.includes(trimmed) || trimmed.includes(orig));
            if (!exists) {
                // If it's a heading
                if (trimmed.startsWith('#')) {
                    return line + ' <span class="diff-inserted text-xs bg-green-500/20 text-green-500 px-1.5 py-0.5 rounded ml-2 font-normal">New Section</span>';
                }
                return `<ins class="diff-inserted bg-green-100 dark:bg-green-900/30 text-green-900 dark:text-green-200 px-1 rounded block my-1 border-l-4 border-green-500 pl-2">${line}</ins>`;
            }
            return line;
        });
        
        return markedLines.join('\n');
    }

    window.handleReportFileUpload = async function (event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        showToast('Uploading and parsing report...');
        
        try {
            const res = await fetch('/api/report/upload', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Failed to upload report');
            }

            const data = await res.json();
            showToast('Report uploaded successfully!');
            
            // Reload report list
            await loadMergeReports();
            
            // Auto select the new report
            selectMergeReport(data.report.id, data.report.topic);
        } catch (e) {
            console.error('Upload error:', e);
            showToast(e.message || 'Error uploading file');
        } finally {
            event.target.value = ''; // Reset file input
        }
    };

    async function loadMergeReports() {
        const container = byId('merge-report-list');
        if (!container) return;

        try {
            const res = await fetch('/api/history');
            const reports = await res.json();

            if (!reports || reports.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-6">
                        <svg class="w-8 h-8 mx-auto text-[var(--text-muted)] opacity-50 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <p class="text-xs text-[var(--text-muted)]">No reports</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = reports.map(report => `
                <button onclick="selectMergeReport(${report.id}, '${escapeAttr(report.topic)}', this)" 
                    class="merge-report-item w-full text-left p-2 rounded-lg text-xs hover:bg-[var(--hover-bg)] transition-colors truncate ${currentMergeReportId === report.id ? 'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]' : 'text-[var(--text-main)]'}"
                    title="${escapeAttr(report.topic)}">
                    ${escapeHtml(report.topic)}
                </button>
            `).join('');
        } catch (e) {
            console.error('Failed to load merge reports', e);
            container.innerHTML = '<div class="text-xs text-red-400 p-2">Failed to load</div>';
        }
    }

    window.selectMergeReport = async function (id, topic, element = null) {
        currentMergeReportId = id;
        byId('merge-report-title').textContent = topic;
        byId('merge-report-title').setAttribute('title', topic);

        // Highlight selected report
        document.querySelectorAll('.merge-report-item').forEach(el => {
            el.classList.remove('bg-[var(--accent-primary)]/10', 'text-[var(--accent-primary)]');
            el.classList.add('text-[var(--text-main)]');
        });
        
        let selectedBtn = element;
        if (!selectedBtn) {
            selectedBtn = Array.from(document.querySelectorAll('.merge-report-item')).find(btn => {
                const clickAttr = btn.getAttribute('onclick') || '';
                return clickAttr.includes(`selectMergeReport(${id},`) || clickAttr.includes(`selectMergeReport(${id})`);
            });
        }
        if (selectedBtn) {
            selectedBtn.classList.add('bg-[var(--accent-primary)]/10', 'text-[var(--accent-primary)]');
            selectedBtn.classList.remove('text-[var(--text-main)]');
        }

        // Show content area, hide empty state
        const emptyState = byId('merge-empty-state');
        const contentArea = byId('merge-content-area');
        if (emptyState) {
            emptyState.classList.add('hidden');
            emptyState.classList.remove('flex');
        }
        if (contentArea) {
            contentArea.classList.remove('hidden');
            contentArea.classList.add('flex');
        }

        // Reset to preview tab
        setMergeTab('preview');

        // Load report content
        const textArea = byId('merge-report-content');
        const previewEl = byId('merge-report-preview');
        textArea.value = 'Loading...';
        previewEl.innerHTML = '<div class="text-xs text-[var(--text-muted)]">Loading content...</div>';

        try {
            const res = await fetch(`/api/report/${id}`);
            const data = await res.json();
            textArea.value = data.content || '';
            renderMergePreview(data.content || '');
        } catch (e) {
            console.error('Failed to load report content', e);
            textArea.value = 'Failed to load report content';
            previewEl.textContent = 'Failed to load report content';
        }
    };

    async function loadMergeHooks() {
        const container = byId('merge-hooks-list');
        if (!container) return;

        try {
            const res = await fetch('/api/hooks');
            const hooks = await res.json();

            if (!hooks || hooks.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-8">
                        <svg class="w-10 h-10 mx-auto text-[var(--text-muted)] opacity-50 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path>
                        </svg>
                        <p class="text-sm text-[var(--text-muted)]">No hooks saved</p>
                        <p class="text-xs text-[var(--text-muted)] mt-1">Select text in chat and click Hook</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = hooks.map(hook => `
                <div class="hook-merge-item group bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg p-3 hover:border-[var(--accent-primary)] transition-colors">
                    <p class="text-sm text-[var(--text-main)] mb-3 line-clamp-4">${escapeHtml(hook.content)}</p>
                    <div class="flex items-center justify-between">
                        <span class="text-xs text-[var(--text-muted)]">${hook.date || ''}</span>
                        <button onclick="smartPushHook(${hook.id}, \`${escapeAttr(hook.content)}\`)" 
                            class="px-3 py-1.5 text-xs font-medium bg-gradient-to-r from-purple-500 to-indigo-500 hover:opacity-90 text-white rounded-lg shadow-sm transition-all flex items-center gap-1.5"
                            title="Smart Push: AI will intelligently merge this hook into the report">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                            </svg>
                            Smart Push
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error('Failed to load merge hooks', e);
            container.innerHTML = '<div class="text-xs text-red-400 p-2">Failed to load hooks</div>';
        }
    }

    window.saveMergeReport = async function () {
        if (!currentMergeReportId) {
            showToast('Please select a report first');
            return;
        }

        const content = byId('merge-report-content').value;

        try {
            const res = await fetch(`/api/report/${currentMergeReportId}/content`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content })
            });

            if (res.ok) {
                showToast('Report saved successfully');
            } else {
                showToast('Failed to save report');
            }
        } catch (e) {
            console.error('Failed to save report', e);
            showToast('Error saving report');
        }
    };

    window.smartPushHook = async function (hookId, hookContent) {
        if (!currentMergeReportId) {
            showToast('Please select a report first');
            return;
        }

        const contentArea = byId('merge-report-content');
        const reportContent = contentArea.value;

        if (!reportContent || reportContent === 'Loading...') {
            showToast('Please wait for report to load');
            return;
        }

        // Show loading state
        const originalContent = contentArea.value;
        
        // Show loading in preview too
        const previewEl = byId('merge-report-preview');
        if (previewEl) {
            previewEl.innerHTML = `
                <div class="flex flex-col items-center justify-center py-12 gap-3 text-center">
                    <svg class="animate-spin h-8 w-8 text-[var(--accent-primary)]" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p class="text-xs text-[var(--text-muted)] font-bold">AI is intelligently merging the hook into your report...</p>
                </div>
            `;
        }
        
        contentArea.value = 'AI is merging the hook into your report...';
        contentArea.disabled = true;

        try {
            const res = await fetch('/api/merge-hook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report_content: reportContent,
                    hook_content: hookContent
                })
            });

            const data = await res.json();

            if (data.status === 'success' && data.merged_content) {
                contentArea.value = data.merged_content;
                
                // Force switch to Preview tab to show the structure
                setMergeTab('preview');
                
                // Render the preview with highlighted diffs!
                renderMergePreview(data.merged_content, originalContent);
                
                showToast('Hook merged successfully! Don\'t forget to save.');
                
                // Smooth scroll to the first inserted diff element and trigger pulse animation
                setTimeout(() => {
                    const firstInsert = document.querySelector('.diff-inserted');
                    if (firstInsert) {
                        firstInsert.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        firstInsert.classList.add('animate-pulse');
                        setTimeout(() => {
                            firstInsert.classList.remove('animate-pulse');
                        }, 4000);
                    }
                }, 150);
            } else {
                contentArea.value = originalContent;
                renderMergePreview(originalContent);
                showToast(data.error || 'Failed to merge hook');
            }
        } catch (e) {
            console.error('Smart push error:', e);
            contentArea.value = originalContent;
            renderMergePreview(originalContent);
            showToast('Error merging hook');
        } finally {
            contentArea.disabled = false;
        }
    };

    // --- REPORT HISTORY PANEL MANAGEMENT ---
    window.loadHistory = function () {
        const container = document.getElementById('history-list-content');
        if (!container) return;

        container.innerHTML = '<div class="text-xs text-[var(--text-muted)] p-2">Loading...</div>';

        fetch('/api/history')
            .then(r => r.json())
            .then(data => {
                container.innerHTML = '';

                // Update workspace telemetry dynamically
                const reportsCount = data.length;
                const reportsEl = document.getElementById('telemetry-reports');
                const timeSavedEl = document.getElementById('telemetry-time-saved');
                const pagesEl = document.getElementById('telemetry-pages-generated');
                const chunksEl = document.getElementById('telemetry-rag-chunks');
                
                if (reportsEl) reportsEl.textContent = reportsCount;
                if (timeSavedEl) {
                    const hours = reportsCount * 3;
                    timeSavedEl.innerHTML = `${hours} <span class="text-[10px] font-normal text-white">h</span>`;
                }
                if (pagesEl) pagesEl.textContent = reportsCount * 8;
                if (chunksEl) {
                    const chunks = reportsCount > 0 ? reportsCount * 250 : 0;
                    chunksEl.textContent = chunks >= 1000 ? `${(chunks / 1000).toFixed(1)}k` : chunks;
                }

                if (reportsCount === 0) {
                    container.innerHTML = '<div class="text-xs text-[var(--text-muted)] p-4 text-center">No reports generated yet.</div>';
                    return;
                }

                data.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'p-3 hover:bg-[var(--hover-bg)] cursor-pointer border-b border-[var(--border-color)] group transition-colors flex items-start gap-3';
                    div.innerHTML = `
                        <div class="pt-0.5 shrink-0" onclick="event.stopPropagation()">
                            <input type="checkbox" class="report-checkbox w-4 h-4 rounded border-gray-450 dark:border-gray-600 bg-transparent text-blue-600 focus:ring-blue-500 transition-all cursor-pointer" data-id="${item.id}">
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex justify-between items-start mb-1">
                                <h4 class="text-xs font-bold text-[var(--text-main)] line-clamp-2 group-hover:text-blue-500 transition-colors">${escapeHtml(item.topic)}</h4>
                            </div>
                            <div class="flex justify-between items-center text-[10px] text-[var(--text-muted)]">
                                <span>${item.date}</span>
                                <button onclick="showReportOptions(event, ${item.id}, '${escapeAttr(item.topic)}')" class="p-0.5 hover:bg-[var(--hover-bg)] rounded opacity-0 group-hover:opacity-100 transition-opacity" title="Options">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path></svg>
                                </button>
                            </div>
                        </div>
                    `;
                    div.onclick = (e) => {
                        if (!e.target.closest('button') && !e.target.closest('input[type="checkbox"]')) {
                            window.viewReport(item.id);
                        }
                    };
                    container.appendChild(div);
                });
            })
            .catch(e => {
                console.error(e);
                container.innerHTML = '<div class="text-xs text-red-400 p-2">Failed to load history</div>';
            });
    };

    window.viewReport = window.viewReport || function (id) {
        if (window.innerWidth < 768) toggleHistory();
        window.location.href = '/?report_id=' + id;
    };

    window.showReportOptions = function (e, id, topic) {
        e.stopPropagation();
        if (window.showContextMenu) {
            window.showContextMenu(e.clientX, e.clientY, [
                { label: 'View', action: () => window.viewReport(id) },
                { label: 'Delete', action: () => window.deleteReport(null, id) }
            ]);
        }
    };

    window.deleteReport = function (e, id) {
        if (e) e.stopPropagation();
        showConfirm('Delete Report', 'Permanently delete this report?', () => {
            fetch('/api/report/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(res => {
                    if (res.status === 'success') {
                        showToast('Report deleted');
                        window.loadHistory();
                    } else {
                        showToast('Error deleting report');
                    }
                })
                .catch(err => {
                    console.error(err);
                    showToast('Error deleting report');
                });
        });
    };

    window.selectAllReports = function () {
        const checkboxes = document.querySelectorAll('.report-checkbox');
        if (checkboxes.length === 0) return;
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
        showToast(allChecked ? 'Deselected all reports' : 'Selected all reports');
    };

    window.deleteSelectedReports = function () {
        const checkboxes = document.querySelectorAll('.report-checkbox:checked');
        const ids = Array.from(checkboxes).map(cb => parseInt(cb.getAttribute('data-id')));

        if (ids.length > 0) {
            showConfirm('Delete Reports', `Permanently delete the ${ids.length} selected report(s)?`, () => {
                const promises = ids.map(id => 
                    fetch('/api/report/' + id, { method: 'DELETE' }).then(r => r.json())
                );
                Promise.all(promises)
                    .then(() => {
                        showToast('Selected reports deleted');
                        window.loadHistory();
                    })
                    .catch(err => {
                        console.error(err);
                        showToast('Error deleting selected reports');
                    });
            });
        } else {
            showConfirm('Delete All Reports', 'Permanently delete all reports in history?', () => {
                fetch('/api/reports/all', { method: 'DELETE' })
                    .then(r => r.json())
                    .then(res => {
                        if (res.status === 'success') {
                            showToast('All reports deleted');
                            window.loadHistory();
                        } else {
                            showToast('Error deleting all reports');
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        showToast('Error deleting all reports');
                    });
            });
        }
    };

    // Helper functions
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeAttr(text) {
        if (!text) return '';
        return text.replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/`/g, '\\`');
    }

    // Add Escape key handler
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllDropdowns();
            hideModal('settings-modal');
            hideModal('folder-modal');
            hideModal('merge-panel');
            hideModal('confirm-modal');
        }
    });

    // ============================================================================
    // ============================================================================
    // FRONT-END AUTHENTICATION ORCHESTRATOR & INTERCEPTOR
    // ============================================================================
    
    // Global Fetch Interceptor to handle 401 Unauthorized API responses
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch(...args);
            if (response.status === 401) {
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
            }
            return response;
        } catch (error) {
            throw error;
        }
    };

    window.checkAuthStatus = async function() {
        try {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.authenticated) {
                // Show initials avatar
                const initials = data.username.substring(0, 2).toUpperCase();
                const avatar = byId('user-avatar-initials');
                if (avatar) {
                    avatar.textContent = initials;
                    avatar.classList.remove('animate-pulse');
                }
                const display = byId('user-username-display');
                if (display) display.textContent = data.username;
                
                // Fetch folders & reports
                fetchFolders();
                if (typeof window.loadHistory === 'function') window.loadHistory();
            } else {
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
            }
        } catch (e) {
            console.error('Auth check failed:', e);
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
    };

    window.submitLogout = async function() {
        try {
            const res = await fetch('/api/auth/logout', { method: 'POST' });
            if (res.status === 200) {
                showToast('Logged out successfully');
                localStorage.removeItem('currentChatSessionId');
                window.location.href = '/login';
            }
        } catch (e) {
            console.error('Logout error:', e);
            showToast('Logout failed');
        }
    };

    // Run auth check on initialization
    document.addEventListener('DOMContentLoaded', () => {
        checkAuthStatus();
    });

})();
