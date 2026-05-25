(function () {
  let currentSessionId = null;
  let hasMessages = false;
  let attachedFiles = [];

  document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const sessId = params.get('session_id');
    if (sessId) {
      window.loadSession(sessId);
      window.history.replaceState({}, document.title, "/chat");
    } else {
      // Restore last session from localStorage
      const savedSessionId = localStorage.getItem('currentChatSessionId');
      if (savedSessionId) {
        window.loadSession(savedSessionId);
      }
    }

    initFileUpload();
    initChatForm();
    initChatInputAutoResize();
  });

  function initChatInputAutoResize() {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput || chatInput.tagName.toLowerCase() !== 'textarea') return;

    const adjustHeight = () => {
      chatInput.style.height = 'auto'; // Reset to auto to get the clean content height
      const scrollHeight = chatInput.scrollHeight;
      
      if (scrollHeight > 120) {
        chatInput.style.height = '120px';
        chatInput.style.overflowY = 'auto';
      } else {
        chatInput.style.height = Math.max(36, scrollHeight) + 'px';
        chatInput.style.overflowY = 'hidden';
      }
    };

    chatInput.addEventListener('input', adjustHeight);

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const form = document.getElementById('chat-form');
        if (form) {
          form.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      }
    });
  }

  function initFileUpload() {
    const fileInput = document.getElementById('file-upload');
    const previewArea = document.getElementById('file-preview-area');

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        files.forEach(file => {
          if (!attachedFiles.find(f => f.name === file.name)) {
            attachedFiles.push(file);
            addFilePreview(file, previewArea);
          }
        });
        fileInput.value = '';
      });
    }
  }

  function addFilePreview(file, container) {
    const chip = document.createElement('div');
    chip.className = 'file-chip flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-xs text-[var(--text-main)]';
    chip.innerHTML = `
      <svg class="w-3 h-3 text-[var(--accent-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
      </svg>
      <span class="max-w-[120px] truncate">${file.name}</span>
      <button type="button" class="remove-file p-0.5 hover:text-red-500 transition-colors">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    `;

    chip.querySelector('.remove-file').addEventListener('click', () => {
      attachedFiles = attachedFiles.filter(f => f.name !== file.name);
      chip.remove();
    });

    container.appendChild(chip);
  }

  function initChatForm() {
    const form = document.getElementById('chat-form');
    if (!form) return;

    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      if (!currentSessionId) {
        window.showToast('Please select or create a chat session first');
        return;
      }

      const input = document.getElementById('chat-input');
      const message = (input?.value || '').trim();
      if (!message) return;

      // --- Message Filtering Logic ---
      const lowerMsg = message.toLowerCase();

      // 1. Casual Greeting/Small Talk
      // Matches exact phrases like "hey", "hello", "hi", "ok", "thanks"
      const casualPattern = /^(hey|hello|hi|howdy|greetings|thank you|thanks|thx|ok|okay|cool|wow)$/i;

      // 2. Appreciative
      // Matches phrases containing appreciation
      const appreciativePattern = /(good job|great work|nice one|you are (awesome|great|good|amazing)|love you|excellent work)/i;

      // 3. Aggressive/Insulting
      // Matches specific keywords anywhere in the message
      const aggressivePattern = /(stupid|idiot|dumb|hate you|useless|shut up|crazy|mad)/i;

      if (casualPattern.test(message)) {
        input.value = '';
        showSystemPopup('Notice', 'Please do not send casual conversational messages.');
        return;
      }

      if (appreciativePattern.test(message)) {
        input.value = '';
        showSystemPopup('Notice', 'It\'s my job. Please refrain from giving such messages.');
        return;
      }

      if (aggressivePattern.test(message)) {
        input.value = '';
        showSystemPopup('Warning', 'Please maintain a professional tone.');
        return;
      }
      // -------------------------------

      const model = document.getElementById('model-select')?.value || 'default';
      const mode = document.getElementById('chat-mode')?.value || 'normal';

      input.value = '';
      if (input.tagName.toLowerCase() === 'textarea') {
        input.style.height = '36px';
        input.style.overflowY = 'hidden';
      }
      input.disabled = true;
      document.getElementById('send-btn').disabled = true;

      renderUserMessage(message, attachedFiles.map(f => f.name));

      if (!hasMessages) {
        transitionInputToBottom();
        hasMessages = true;
      }

      showTypingIndicator();

      try {
        const formData = new FormData();
        formData.append('message', message);
        formData.append('session_id', currentSessionId);
        formData.append('model', model);
        formData.append('mode', mode);

        attachedFiles.forEach(file => {
          formData.append('files', file);
        });

        const response = await fetch('/chat', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        hideTypingIndicator();

        if (data.error) {
          renderAssistantMessage('Error: ' + data.error);
        } else {
          renderAssistantMessage(data.response);
        }

        attachedFiles = [];
        document.getElementById('file-preview-area').innerHTML = '';

      } catch (err) {
        hideTypingIndicator();
        renderAssistantMessage('Connection error. Please try again.');
        console.error('Chat error:', err);
      } finally {
        input.disabled = false;
        document.getElementById('send-btn').disabled = false;
        if (input.tagName.toLowerCase() === 'textarea') {
          input.style.height = '36px';
          input.style.overflowY = 'hidden';
        }
        input.focus();
      }
    });
  }

  function showSystemPopup(title, message, isWarning = false) {
    const overlay = document.createElement('div');
    overlay.className = 'custom-modal-overlay active';
    overlay.style.zIndex = '9999'; // Ensure it's on top of everything

    const modal = document.createElement('div');
    modal.className = 'bg-[var(--bg-panel)] rounded-2xl shadow-2xl p-8 w-full max-w-sm border border-[var(--border-color)] modal-pop flex flex-col items-center text-center';

    // Icon
    const iconColor = isWarning || title.toLowerCase().includes('warning') ? 'text-red-500' : 'text-blue-500';
    const iconSvg = isWarning || title.toLowerCase().includes('warning')
      ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>'
      : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>';

    modal.innerHTML = `
      <div class="mb-4 ${iconColor}">
        <svg class="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          ${iconSvg}
        </svg>
      </div>
      <h3 class="text-xl font-bold text-[var(--text-main)] mb-2">${escapeHtml(title)}</h3>
      <p class="text-sm text-[var(--text-muted)] mb-8 leading-relaxed">${escapeHtml(message)}</p>
      <button class="w-full px-5 py-3 text-sm font-medium bg-[var(--accent-primary)] hover:opacity-90 text-white rounded-xl shadow-lg shadow-blue-500/20 transition-all">
        Got it
      </button>
    `;

    const btn = modal.querySelector('button');
    btn.onclick = () => {
      overlay.classList.remove('active');
      setTimeout(() => overlay.remove(), 200);
    };

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Focus button for accessibility
    setTimeout(() => btn.focus(), 100);
  }

  function extractAttachments(text) {
    if (!text) return { text: '', files: [] };
    const pattern = /\n\n\[Attached:\s*(.*?)\]/i;
    const match = text.match(pattern);
    if (match) {
      const cleanText = text.replace(pattern, '').trim();
      const files = match[1].split(',').map(f => f.trim()).filter(Boolean);
      return { text: cleanText, files: files };
    }
    return { text: text, files: [] };
  }

  function renderUserMessage(rawText, fileNames = []) {
    const container = document.getElementById('messages-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    const msgId = 'user-msg-' + Date.now();

    // Parse attachments from history text block if present
    const parsed = extractAttachments(rawText);
    const textToShow = parsed.text;
    
    // De-duplicate both initial fileNames array and parsed file list
    const allFiles = [...new Set([...fileNames, ...parsed.files])];

    let filesHtml = '';
    if (allFiles.length > 0) {
      filesHtml = `<div class="mt-3 flex flex-wrap gap-2 justify-end w-full">
        ${allFiles.map(name => {
          const isPdf = name.toLowerCase().endsWith('.pdf');
          const isDocx = name.toLowerCase().endsWith('.docx');
          const iconColor = isPdf ? 'text-red-500' : (isDocx ? 'text-blue-500' : 'text-gray-400');
          const iconSvg = isPdf 
            ? `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />` 
            : `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />`;
          
          return `
            <div class="chatgpt-file-card flex items-center gap-3 p-3 bg-[var(--bg-panel)] hover:bg-[var(--hover-bg)] border border-[var(--border-color)] rounded-xl max-w-xs text-left shadow-sm transition-all select-none">
              <div class="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                <svg class="w-6 h-6 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  ${iconSvg}
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-xs font-semibold text-[var(--text-main)] truncate" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
                <div class="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-semibold mt-0.5">${isPdf ? 'PDF Document' : (isDocx ? 'Word Doc' : 'Attachment')}</div>
              </div>
            </div>
          `;
        }).join('')}
      </div>`;
    }

    msgDiv.innerHTML = `
      <div class="user-msg-wrapper">
        <div class="message-bubble" id="${msgId}" data-raw-text="${escapeHtml(rawText).replace(/"/g, '&quot;')}">
          <p class="message-text">${escapeHtml(textToShow)}</p>
          ${filesHtml}
        </div>
        <div class="message-actions user-actions">
          <button class="action-btn" onclick="copyMessageText('${msgId}')" title="Copy">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
            </svg>
          </button>
          <button class="action-btn" onclick="editUserMessage('${msgId}')" title="Edit">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
            </svg>
          </button>
        </div>
      </div>
    `;
    container.appendChild(msgDiv);
    scrollToBottom();
  }

  function renderAssistantMessage(text, msgId = null, skipAnimation = false) {
    const container = document.getElementById('messages-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant-message';
    const id = msgId || ('asst-msg-' + Date.now());

    const formattedText = formatMarkdown(text);

    msgDiv.innerHTML = `
      <div class="message-bubble" id="${id}" data-raw-text="${escapeHtml(text).replace(/"/g, '&quot;')}">
        <div class="message-text prose"></div>
        <div class="message-actions assistant-actions">
          <button class="action-btn" onclick="copyMessageText('${id}')" title="Copy">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
            </svg>
          </button>
          <button class="action-btn like-btn" onclick="likeMessage('${id}')" title="Like">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
            </svg>
          </button>
          <button class="action-btn dislike-btn" onclick="dislikeMessage('${id}')" title="Dislike">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path>
            </svg>
          </button>
          <div class="redo-container">
            <button class="action-btn redo-btn" onclick="toggleRedoMenu('${id}')" title="Redo with different model">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
            </button>
            <div class="redo-menu" id="redo-menu-${id}">
              <div class="redo-menu-title">Regenerate with:</div>
              <button class="redo-option" onclick="redoWithModel('${id}', 'default')">nvidia/Nemotron</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'qwen-80b')">Qwen 2.5 72B</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'mistral')">Mistral Small</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'gemini')">Gemini 2.0 Flash</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'gpt-oss')">GPT-4o (OSS)</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'gemma')">Gemma 2 27B</button>
              <button class="redo-option" onclick="redoWithModel('${id}', 'deepseek')">DeepSeek R1</button>
            </div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(msgDiv);
    scrollToBottom();

    const textEl = msgDiv.querySelector('.message-text');

    // Skip animation for loaded history messages
    if (skipAnimation) {
      textEl.innerHTML = formattedText;
      return;
    }

    // Fast typing animation effect
    typeText(textEl, formattedText);
  }

  // Fast typing animation - reveals formatted HTML progressively
  function typeText(element, html) {
    const chunkSize = 8; // Characters per chunk
    const delay = 3; // Milliseconds between chunks (very fast)
    let visibleChars = 0;

    // Parse the HTML to get all text nodes with their positions
    const textNodes = [];
    let totalChars = 0;

    function extractTextNodes(node, path = []) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent;
        if (text.length > 0) {
          textNodes.push({
            start: totalChars,
            end: totalChars + text.length,
            text: text
          });
          totalChars += text.length;
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        for (let i = 0; i < node.childNodes.length; i++) {
          extractTextNodes(node.childNodes[i], [...path, i]);
        }
      }
    }

    // Create a template from the HTML
    const template = document.createElement('div');
    template.innerHTML = html;
    extractTextNodes(template);

    // Function to truncate text in cloned HTML based on visible characters
    function getPartialHTML(chars) {
      const clone = template.cloneNode(true);
      let remaining = chars;

      function truncateNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
          const text = node.textContent;
          if (remaining <= 0) {
            node.textContent = '';
          } else if (remaining < text.length) {
            node.textContent = text.substring(0, remaining);
            remaining = 0;
          } else {
            remaining -= text.length;
          }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          for (let i = 0; i < node.childNodes.length; i++) {
            truncateNode(node.childNodes[i]);
          }
          // Hide elements that have no visible text content yet but preserve spacing
          const hasVisibleText = node.textContent && node.textContent.trim().length > 0;
          if (!hasVisibleText) {
            node.style.visibility = 'hidden';
          }
        }
      }

      truncateNode(clone);
      return clone.innerHTML;
    }

    // Animate by progressively revealing more characters
    function typeChunk() {
      if (visibleChars < totalChars) {
        visibleChars = Math.min(visibleChars + chunkSize, totalChars);
        element.innerHTML = getPartialHTML(visibleChars);
        scrollToBottom();
        setTimeout(typeChunk, delay);
      } else {
        // Animation complete - ensure full HTML is shown
        element.innerHTML = html;
        scrollToBottom();
      }
    }

    typeChunk();
  }

  function showTypingIndicator() {
    const container = document.getElementById('messages-container');
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'typing-indicator';
    indicator.innerHTML = `
      <div class="typing-bubble">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    container.appendChild(indicator);
    scrollToBottom();
  }

  function hideTypingIndicator() {
    document.getElementById('typing-indicator')?.remove();
  }

  function transitionInputToBottom() {
    const unitMsg = document.getElementById('unit-msg');
    if (unitMsg) {
      unitMsg.classList.remove('unit-msg-centered');
      unitMsg.classList.add('unit-msg-docked');
    }
  }

  function resetInputToCenter() {
    const unitMsg = document.getElementById('unit-msg');
    if (unitMsg) {
      unitMsg.classList.remove('unit-msg-docked');
      unitMsg.classList.add('unit-msg-centered');
    }
  }

  function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    try {
      // Intercept <think> tags for Deep Dive mode and convert them into a visual accordion
      // This regex handles missing closing tags (if the model cuts off mid-thought)
      text = text.replace(/<think>([\s\S]*?)(?:<\/think>|$)/gi, (match, thoughtProcess) => {
        const cleanContent = thoughtProcess.trim();
        // Give a short 2-3 word snippet to the user giving them an idea of what occurred
        const words = cleanContent.split(/[\s]+/).filter(w => w.length > 0);
        const snippet = words.length > 0 ? words.slice(0, 3).join(' ') + '...' : 'Analyzing deep context...';
        
        return `
<details class="ai-thought-process">
  <summary>
    <span class="think-icon">💡</span> Thinking: <span class="think-snippet">"${escapeHtml(snippet)}"</span>
  </summary>
  <div class="thought-content">
    ${escapeHtml(cleanContent).replace(/\n/g, '<br>')}
  </div>
</details>
`;
      });

      // Use marked library if available, otherwise return raw text (protected against XSS via escaping if necessary, though marked handles it)
      // We assume marked is loaded globally via layout.html
      if (typeof marked !== 'undefined') {
        const html = marked.parse(text);
        // Wrap tables in table-wrapper for horizontal scroll. Marked renders tables as <table>...</table>
        return html.replace(/<table>/g, '<div class="table-wrapper"><table>').replace(/<\/table>/g, '</table></div>');
      }
      return escapeHtml(text).replace(/\n/g, '<br>');
    } catch (e) {
      console.error('Markdown parse error', e);
      return escapeHtml(text);
    }
  }

  // Copy code block function
  window.copyCodeBlock = function (btn) {
    const codeBlock = btn.closest('.code-block-wrapper').querySelector('code');
    if (!codeBlock) {
      window.showToast?.('No code to copy');
      return;
    }
    const text = codeBlock.textContent;

    // Try modern clipboard API first, fallback to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showCopiedFeedback(btn);
      }).catch(() => {
        fallbackCopy(text, btn);
      });
    } else {
      fallbackCopy(text, btn);
    }
  };

  function showCopiedFeedback(btn) {
    const originalText = btn.innerHTML;
    btn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
    </svg> Copied!`;
    setTimeout(() => {
      btn.innerHTML = originalText;
    }, 1500);
  }

  function fallbackCopy(text, btn) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      showCopiedFeedback(btn);
    } catch (err) {
      window.showToast?.('Failed to copy');
    }
    document.body.removeChild(textarea);
  }

  async function loadSessionMessages(sessionId) {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`);
      const messages = await response.json();

      const container = document.getElementById('messages-container');
      container.innerHTML = '';

      if (messages.length > 0) {
        hasMessages = true;
        transitionInputToBottom();

        messages.forEach(msg => {
          if (msg.role === 'user') {
            renderUserMessage(msg.content);
          } else {
            renderAssistantMessage(msg.content, null, true); // Skip animation for history
          }
        });
      } else {
        hasMessages = false;
        resetInputToCenter();
      }
    } catch (err) {
      console.error('Error loading messages:', err);
    }
  }

  window.loadSession = function (id) {
    currentSessionId = id;

    // Save to localStorage for persistence across reloads
    localStorage.setItem('currentChatSessionId', id);

    const w = document.getElementById('welcome-state');
    if (w) w.classList.add('hidden');

    const c = document.getElementById('chat-interface');
    if (c) {
      c.classList.remove('hidden');
    }
    document.getElementById('active-indicator')?.classList.remove('hidden');

    const titleEl = document.getElementById('active-session-title');
    if (titleEl) titleEl.textContent = "Chat Session " + id;

    loadSessionMessages(id);
  };

  window.resetToWelcomeState = function () {
    currentSessionId = null;
    localStorage.removeItem('currentChatSessionId');

    // Update UI
    const w = document.getElementById('welcome-state');
    const c = document.getElementById('chat-interface');

    if (w) w.classList.remove('hidden');
    if (c) c.classList.add('hidden');

    document.getElementById('active-indicator')?.classList.add('hidden');

    const titleEl = document.getElementById('active-session-title');
    if (titleEl) titleEl.textContent = '';

    const container = document.getElementById('messages-container');
    if (container) container.innerHTML = '';

    // Clean URL without reloading
    window.history.replaceState({}, document.title, "/chat");
  };

  function handleHookButtonClick() {
    const selection = window.getSelection();
    const selectedText = selection ? selection.toString().trim() : '';

    if (selectedText) {
      saveHook(selectedText);
    } else {
      openHookPanel();
    }
  }
  window.handleHookButtonClick = handleHookButtonClick;

  // Open hook panel and load hooks
  function openHookPanel() {
    const panel = document.getElementById('hook-panel');
    if (panel) {
      panel.style.transform = 'translateX(0%)';
      fetchHooks();
    }
  }
  window.openHookPanel = openHookPanel;
  window.openMergePanel = openHookPanel;

  // Fetch hooks from API
  async function fetchHooks() {
    try {
      const response = await fetch('/api/hooks');
      const hooks = await response.json();
      renderHooks(hooks);
    } catch (err) {
      console.error('Error fetching hooks:', err);
      renderHooks([]);
    }
  }
  window.fetchHooks = fetchHooks;

  // Render hooks in the panel
  function renderHooks(hooks) {
    const container = document.getElementById('hook-list-content');
    if (!container) return;

    if (!hooks || hooks.length === 0) {
      container.innerHTML = `
        <div class="text-center py-8">
          <svg class="w-12 h-12 mx-auto text-[var(--text-muted)] opacity-50 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path>
          </svg>
          <p class="text-sm text-[var(--text-muted)]">No hooks saved yet</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Select text and click Hook to save</p>
        </div>
      `;
      return;
    }

    container.innerHTML = hooks.map(hook => `
      <div class="hook-item group bg-[var(--bg-main)] border border-[var(--border-color)] rounded-lg p-3 mb-2 hover:border-[var(--accent-primary)] transition-colors">
        <div class="flex justify-between items-start gap-2">
          <p class="text-sm text-[var(--text-main)] flex-1 line-clamp-3">${escapeHtml(hook.content)}</p>
          <button onclick="deleteHook(${hook.id})" class="opacity-0 group-hover:opacity-100 p-1 text-[var(--text-muted)] hover:text-red-500 rounded transition-all" title="Delete hook">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-2">${hook.date}</p>
      </div>
    `).join('');
  }

  // Delete a hook
  async function deleteHook(hookId) {
    try {
      const response = await fetch(`/api/hooks/${hookId}`, { method: 'DELETE' });
      const data = await response.json();
      if (data.status === 'success') {
        window.showToast?.('Hook deleted');
        fetchHooks(); // Refresh the list
      } else {
        window.showToast?.('Failed to delete hook');
      }
    } catch (err) {
      console.error('Error deleting hook:', err);
      window.showToast?.('Error deleting hook');
    }
  }
  window.deleteHook = deleteHook;

  async function saveHook(content) {
    try {
      const response = await fetch(window.ADD_HOOK_URL || '/add-hook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content })
      });

      const data = await response.json();
      if (data.status === 'success') {
        window.showToast('Hook saved!');
        window.getSelection()?.removeAllRanges();
        // Open the hook panel to show the saved hook
        openHookPanel();
      } else {
        window.showToast('Failed to save hook');
      }
    } catch (err) {
      console.error('Hook save error:', err);
      window.showToast('Error saving hook');
    }
  }

  window.attemptNewChat = async function () {
    if (!currentSessionId) {
      window.showToast('No active session. Please select a folder first.');
      return;
    }

    try {
      // Fetch current session info to get folder_id
      const response = await fetch(`/api/sessions/${currentSessionId}/info`);
      if (!response.ok) {
        window.showToast('Could not find current session info');
        return;
      }
      const sessionInfo = await response.json();
      const folderId = sessionInfo.folder_id;

      if (folderId) {
        // Create new session in the same folder
        await window.createSession(folderId, 'New Chat', true);
      } else {
        window.showToast('Could not determine folder for new chat');
      }
    } catch (err) {
      console.error('Error creating new chat:', err);
      window.showToast('Error creating new chat');
    }
  };

  window.toggleChatModelSelect = function (id) {
    const opt = document.getElementById(id + '-options');
    if (!opt) return;

    // Determine if input bar is docked at bottom
    const unitMsg = document.getElementById('unit-msg');
    const isDocked = unitMsg && unitMsg.classList.contains('unit-msg-docked');

    if (isDocked) {
      // Open upward when at bottom of screen
      opt.style.bottom = '100%';
      opt.style.top = 'auto';
      opt.style.marginBottom = '4px';
      opt.style.marginTop = '';
      opt.style.boxShadow = '0 -10px 25px rgba(0, 0, 0, 0.15)';
    } else {
      // Open downward when centered
      opt.style.bottom = 'auto';
      opt.style.top = '100%';
      opt.style.marginTop = '4px';
      opt.style.marginBottom = '';
      opt.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.15)';
    }

    opt.classList.toggle('show');
  };

  window.selectCustomOption = function (value, text, inputId, changeCb) {
    const hidden = document.getElementById(inputId);
    const trigger = document.getElementById(inputId + '-trigger-text');
    if (hidden) hidden.value = value;
    if (trigger) trigger.textContent = text;
    const opts = document.getElementById(inputId + '-options');
    if (opts) opts.classList.remove('show');
    if (changeCb && typeof window[changeCb] === 'function') window[changeCb](value);
  };

  window.setMode = function (mode) {
    const indicator = document.getElementById('mode-indicator');
    const btnNormal = document.getElementById('mode-normal');
    const btnDeep = document.getElementById('mode-deep');
    const hiddenInput = document.getElementById('chat-mode');

    if (hiddenInput) hiddenInput.value = mode;

    if (mode === 'normal') {
      if (indicator) {
        indicator.style.left = '0.125rem';
        indicator.classList.remove('left-1/2');
      }
      btnNormal?.classList.add('text-white');
      btnNormal?.classList.remove('text-[var(--text-muted)]');
      btnDeep?.classList.add('text-[var(--text-muted)]');
      btnDeep?.classList.remove('text-white');
    } else if (mode === 'deep_dive') {
      if (indicator) {
        indicator.style.left = '50%';
        indicator.classList.remove('left-0.5');
      }
      btnNormal?.classList.remove('text-white');
      btnNormal?.classList.add('text-[var(--text-muted)]');
      btnDeep?.classList.remove('text-[var(--text-muted)]');
      btnDeep?.classList.add('text-white');
    }
  };

  let recognition = null;
  let isRecording = false;
  let originalPlaceholder = '';

  window.toggleRecording = function () {
    const micBtn = document.getElementById('mic-btn');
    const chatInput = document.getElementById('chat-input');
    const inputBox = document.querySelector('.input-box');
    if (!micBtn || !chatInput) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      window.showToast('Speech recognition not supported in this browser. Please use Chrome, Safari or Edge.');
      return;
    }

    if (isRecording) {
      if (recognition) {
        recognition.stop();
      }
      return;
    }

    try {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = function () {
        isRecording = true;
        micBtn.classList.add('text-red-500', 'animate-pulse');
        micBtn.classList.remove('text-[var(--text-muted)]');
        if (inputBox) {
          inputBox.classList.add('ring-2', 'ring-red-500/50', 'border-red-500/50');
        }
        originalPlaceholder = chatInput.placeholder || 'Ask a question...';
        chatInput.placeholder = 'Listening... Speak now!';
        window.showToast('Listening... Speak now.');
      };

      recognition.onerror = function (event) {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          window.showToast('Microphone access denied. Please allow microphone permissions.');
        } else {
          window.showToast('Speech recognition error: ' + event.error);
        }
        stopRecordingState();
      };

      recognition.onend = function () {
        stopRecordingState();
      };

      recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          const currentText = chatInput.value;
          chatInput.value = currentText ? (currentText + ' ' + transcript) : transcript;
          chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
      };

      recognition.start();

    } catch (e) {
      console.error('Failed to start speech recognition:', e);
      window.showToast('Could not start microphone.');
      stopRecordingState();
    }

    function stopRecordingState() {
      isRecording = false;
      if (micBtn) {
        micBtn.classList.remove('text-red-500', 'animate-pulse');
        micBtn.classList.add('text-[var(--text-muted)]');
      }
      if (inputBox) {
        inputBox.classList.remove('ring-2', 'ring-red-500/50', 'border-red-500/50');
      }
      if (chatInput) {
        chatInput.placeholder = originalPlaceholder || 'Ask a question...';
      }
    }
  };

  // ============================================
  // MESSAGE ACTION HANDLERS
  // ============================================

  window.copyMessageText = function (msgId) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl) {
      window.showToast?.('Message not found');
      return;
    }

    // Get raw text from data attribute and decode HTML entities
    let rawText = msgEl.dataset.rawText || '';
    if (rawText) {
      const textarea = document.createElement('textarea');
      textarea.innerHTML = rawText;
      rawText = textarea.value;
    } else {
      rawText = msgEl.querySelector('.message-text')?.innerText || '';
    }

    if (!rawText) {
      window.showToast?.('No text to copy');
      return;
    }

    // Try modern clipboard API first, fallback to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(rawText).then(() => {
        window.showToast?.('Copied to clipboard');
      }).catch(() => {
        fallbackCopyMessage(rawText);
      });
    } else {
      fallbackCopyMessage(rawText);
    }
  };

  function fallbackCopyMessage(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999); // For mobile devices
    try {
      document.execCommand('copy');
      window.showToast?.('Copied to clipboard');
    } catch (err) {
      window.showToast?.('Failed to copy');
    }
    document.body.removeChild(textarea);
  }

  window.editUserMessage = function (msgId) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl || msgEl.classList.contains('editing')) return;

    const textEl = msgEl.querySelector('.message-text');
    if (!textEl) return;

    let rawText = msgEl.dataset.rawText || textEl.innerText;
    const textarea = document.createElement('textarea');
    textarea.innerHTML = rawText;
    rawText = textarea.value;

    msgEl.dataset.originalText = rawText;
    msgEl.classList.add('editing');
    textEl.contentEditable = 'true';
    textEl.textContent = rawText;
    textEl.focus();

    const range = document.createRange();
    range.selectNodeContents(textEl);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    const actionsEl = msgEl.closest('.user-msg-wrapper')?.querySelector('.message-actions');
    if (actionsEl) {
      actionsEl.dataset.originalHtml = actionsEl.innerHTML;
      actionsEl.innerHTML = `
        <button class="action-btn" onclick="saveUserMessage('${msgId}')" title="Save" style="color: #22c55e;">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        </button>
        <button class="action-btn" onclick="cancelEditUserMessage('${msgId}')" title="Cancel" style="color: #ef4444;">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      `;
      actionsEl.style.opacity = '1';
    }

    textEl.onkeydown = function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        window.saveUserMessage(msgId);
      } else if (e.key === 'Escape') {
        window.cancelEditUserMessage(msgId);
      }
    };
  };

  window.saveUserMessage = function (msgId) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl) return;
    const textEl = msgEl.querySelector('.message-text');
    if (!textEl) return;

    const newText = textEl.textContent.trim();
    msgEl.dataset.rawText = escapeHtml(newText).replace(/"/g, '&quot;');
    textEl.contentEditable = 'false';
    textEl.onkeydown = null;
    msgEl.classList.remove('editing');

    const actionsEl = msgEl.closest('.user-msg-wrapper')?.querySelector('.message-actions');
    if (actionsEl && actionsEl.dataset.originalHtml) {
      actionsEl.innerHTML = actionsEl.dataset.originalHtml;
      actionsEl.style.opacity = '';
      delete actionsEl.dataset.originalHtml;
    }
    delete msgEl.dataset.originalText;
    window.showToast('Message updated');
  };

  window.cancelEditUserMessage = function (msgId) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl) return;
    const textEl = msgEl.querySelector('.message-text');
    if (!textEl) return;

    textEl.textContent = msgEl.dataset.originalText || '';
    textEl.contentEditable = 'false';
    textEl.onkeydown = null;
    msgEl.classList.remove('editing');

    const actionsEl = msgEl.closest('.user-msg-wrapper')?.querySelector('.message-actions');
    if (actionsEl && actionsEl.dataset.originalHtml) {
      actionsEl.innerHTML = actionsEl.dataset.originalHtml;
      actionsEl.style.opacity = '';
      delete actionsEl.dataset.originalHtml;
    }
    delete msgEl.dataset.originalText;
  };

  window.likeMessage = function (msgId) {
    const btn = document.querySelector(`#${msgId} .like-btn`);
    if (btn) {
      btn.classList.toggle('active');
      document.querySelector(`#${msgId} .dislike-btn`)?.classList.remove('active');
    }
    window.showToast('Feedback recorded');
  };

  window.dislikeMessage = function (msgId) {
    const btn = document.querySelector(`#${msgId} .dislike-btn`);
    if (btn) {
      btn.classList.toggle('active');
      document.querySelector(`#${msgId} .like-btn`)?.classList.remove('active');
    }
    window.showToast('Feedback recorded');
  };

  window.toggleRedoMenu = function (msgId) {
    // Close other redo menus
    document.querySelectorAll('.redo-menu.show').forEach(menu => {
      if (menu.id !== `redo-menu-${msgId}`) {
        menu.classList.remove('show');
      }
    });
    const menu = document.getElementById(`redo-menu-${msgId}`);
    if (menu) menu.classList.toggle('show');
  };

  window.redoWithModel = async function (msgId, model) {
    const menu = document.getElementById(`redo-menu-${msgId}`);
    if (menu) menu.classList.remove('show');

    const msgEl = document.getElementById(msgId);
    if (!msgEl) return;

    // Find the previous user message
    const msgContainer = msgEl.closest('.message');
    let prevUserMsg = msgContainer?.previousElementSibling;
    while (prevUserMsg && !prevUserMsg.classList.contains('user-message')) {
      prevUserMsg = prevUserMsg.previousElementSibling;
    }

    if (!prevUserMsg) {
      window.showToast('Could not find original query');
      return;
    }

    const userText = prevUserMsg.querySelector('.message-text')?.innerText || '';
    if (!userText) {
      window.showToast('Could not find original query');
      return;
    }

    // Show loading state
    const textEl = msgEl.querySelector('.message-text');
    const originalContent = textEl?.innerHTML;
    if (textEl) {
      textEl.innerHTML = '<div class="typing-dots inline-flex gap-1"><span></span><span></span><span></span></div> Regenerating...';
    }

    try {
      const mode = document.getElementById('chat-mode')?.value || 'normal';
      const formData = new FormData();
      formData.append('message', userText);
      formData.append('session_id', currentSessionId);
      formData.append('model', model);
      formData.append('mode', mode);

      const response = await fetch('/chat', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.error) {
        if (textEl) textEl.innerHTML = originalContent;
        window.showToast('Error: ' + data.error);
      } else {
        if (textEl) {
          textEl.innerHTML = formatMarkdown(data.response);
          msgEl.dataset.rawText = escapeHtml(data.response).replace(/"/g, '&quot;');
        }
        window.showToast('Response regenerated');
      }
    } catch (err) {
      if (textEl) textEl.innerHTML = originalContent;
      window.showToast('Failed to regenerate');
      console.error('Redo error:', err);
    }
  };

  // Close redo menus when clicking outside
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.redo-container')) {
      document.querySelectorAll('.redo-menu.show').forEach(menu => {
        menu.classList.remove('show');
      });
    }
  });

})();
