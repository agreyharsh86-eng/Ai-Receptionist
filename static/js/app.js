/**
 * Corporate AI Receptionist - Main Application Controller
 * Manages WebSocket real-time live streaming, Web Audio pipeline, visualizer,
 * appointments, caller message inbox, staff directory, and settings.
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        isCallActive: false,
        isMuted: false,
        activeTab: 'appointmentsTab',
        apiKey: localStorage.getItem('gemini_api_key') || '',
        voice: localStorage.getItem('receptionist_voice') || 'Aoede',
        ws: null,
        audioRecorder: null,
        audioPlayer: null,
        visualizerAnimationId: null,
        currentVolume: 0,
        companyInfo: null
    };

    // DOM Elements
    const systemClock = document.getElementById('systemClock');
    const connectionPill = document.getElementById('connectionPill');
    const connectionText = document.getElementById('connectionText');
    const liveBadge = document.getElementById('liveBadge');
    const badgeText = document.getElementById('badgeText');
    const startCallBtn = document.getElementById('startCallBtn');
    const endCallBtn = document.getElementById('endCallBtn');
    const muteBtn = document.getElementById('muteBtn');
    const muteIcon = document.getElementById('muteIcon');
    const muteLabel = document.getElementById('muteLabel');
    const activeToolBanner = document.getElementById('activeToolBanner');
    const toolBannerText = document.getElementById('toolBannerText');
    const transcriptFeed = document.getElementById('transcriptFeed');
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');
    const waveformCanvas = document.getElementById('waveformCanvas');
    const consoleHero = document.getElementById('consoleHero');
    const avatarContainer = document.getElementById('avatarContainer');

    // Management Suite Elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const appointmentsList = document.getElementById('appointmentsList');
    const messagesList = document.getElementById('messagesList');
    const directoryList = document.getElementById('directoryList');
    const faqList = document.getElementById('faqList');
    const logsList = document.getElementById('logsList');
    const apptCountBadge = document.getElementById('apptCountBadge');
    const msgCountBadge = document.getElementById('msgCountBadge');
    const directorySearchInput = document.getElementById('directorySearchInput');

    // Settings Modal Elements
    const settingsModal = document.getElementById('settingsModal');
    const openSettingsBtn = document.getElementById('openSettingsBtn');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const voiceSelect = document.getElementById('voiceSelect');

    // Initialize System Clock
    function updateClock() {
        const now = new Date();
        systemClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' EST';
    }
    setInterval(updateClock, 1000);
    updateClock();

    // =========================================================================
    // Visualizer Waveform Canvas
    // =========================================================================
    const canvasCtx = waveformCanvas.getContext('2d');

    function drawWaveform() {
        state.visualizerAnimationId = requestAnimationFrame(drawWaveform);

        const width = waveformCanvas.width;
        const height = waveformCanvas.height;
        canvasCtx.clearRect(0, 0, width, height);

        let freqData = new Uint8Array(0);
        if (state.audioPlayer && state.audioPlayer.isPlaying) {
            freqData = state.audioPlayer.getFrequencyData();
        }

        const barCount = 42;
        const barWidth = 6;
        const gap = (width - (barCount * barWidth)) / (barCount - 1);

        for (let i = 0; i < barCount; i++) {
            let barHeight = 4;

            if (state.isCallActive) {
                if (state.audioPlayer && state.audioPlayer.isPlaying && freqData.length > 0) {
                    const freqIdx = Math.floor((i / barCount) * freqData.length);
                    const val = freqData[freqIdx] / 255.0;
                    barHeight = Math.max(4, val * (height * 0.9));
                } else if (state.currentVolume > 0.01) {
                    // User mic volume fluctuation
                    const wave = Math.sin((i / barCount) * Math.PI) * state.currentVolume * (height * 0.85);
                    barHeight = Math.max(4, wave);
                } else {
                    // Gentle idle pulse
                    const time = Date.now() * 0.003;
                    barHeight = 4 + Math.sin(time + i * 0.3) * 3;
                }
            }

            const x = i * (barWidth + gap);
            const y = (height - barHeight) / 2;

            // Gradient fill
            const grad = canvasCtx.createLinearGradient(x, y, x, y + barHeight);
            if (state.audioPlayer && state.audioPlayer.isPlaying) {
                grad.addColorStop(0, '#00f0ff');
                grad.addColorStop(1, '#6366f1');
            } else if (state.currentVolume > 0.05) {
                grad.addColorStop(0, '#38bdf8');
                grad.addColorStop(1, '#0284c7');
            } else {
                grad.addColorStop(0, 'rgba(255, 255, 255, 0.2)');
                grad.addColorStop(1, 'rgba(255, 255, 255, 0.05)');
            }

            canvasCtx.fillStyle = grad;
            canvasCtx.beginPath();
            canvasCtx.roundRect(x, y, barWidth, barHeight, 3);
            canvasCtx.fill();
        }
    }
    drawWaveform();

    // =========================================================================
    // Live Voice Call Management (WebSocket & Audio Engine)
    // =========================================================================

    async function startVoiceCall() {
        if (state.isCallActive) return;

        // Check if API key is provided
        if (!state.apiKey) {
            // Check if server already has GEMINI_API_KEY
            const cfg = await fetch('/api/config').then(r => r.json()).catch(() => ({}));
            if (!cfg.has_api_key) {
                showToast('Please enter your Gemini API Key in Settings first.', 'warning');
                openSettingsModal();
                return;
            }
        }

        updateLiveBadge('processing', 'Connecting...');
        connectionText.textContent = 'Connecting...';

        try {
            // 1. Initialize Audio Player for 24kHz Gemini output
            state.audioPlayer = new window.PcmAudioPlayer(24000);
            state.audioPlayer.init();
            state.audioPlayer.onPlaybackStateChange = (isPlaying) => {
                if (isPlaying) {
                    updateLiveBadge('speaking', 'Aria Speaking');
                } else if (state.isCallActive) {
                    updateLiveBadge('listening', 'Listening...');
                }
            };

            // 2. Initialize Microphone Recorder for 16kHz input
            state.audioRecorder = new window.PcmAudioRecorder({
                targetSampleRate: 16000,
                onAudioChunk: (base64Pcm) => {
                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({
                            type: 'audio',
                            data: base64Pcm
                        }));
                    }
                },
                onVolumeChange: (vol) => {
                    state.currentVolume = vol;
                }
            });
            await state.audioRecorder.start();

            // 3. Connect to WebSocket
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const queryParams = new URLSearchParams();
            if (state.apiKey) queryParams.set('api_key', state.apiKey);
            if (state.voice) queryParams.set('voice', state.voice);

            const wsUrl = `${protocol}//${window.location.host}/ws/live?${queryParams.toString()}`;
            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                state.isCallActive = true;
                updateCallUiState(true);
                connectionPill.classList.add('live-active');
                connectionText.textContent = 'Live Audio Call';
                appendTranscriptMessage('system', 'Connected to front desk. Aria is listening...');
            };

            state.ws.onmessage = (event) => {
                handleWebSocketMessage(event.data);
            };

            state.ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                showToast('WebSocket connection error', 'error');
            };

            state.ws.onclose = () => {
                endVoiceCall();
            };

        } catch (err) {
            console.error('Failed to start call:', err);
            showToast(`Could not access microphone: ${err.message}`, 'error');
            endVoiceCall();
        }
    }

    function handleWebSocketMessage(rawMsg) {
        try {
            const msg = JSON.parse(rawMsg);

            switch (msg.type) {
                case 'status':
                    if (msg.status === 'connected') {
                        updateLiveBadge('listening', 'Listening...');
                    }
                    break;

                case 'audio':
                    // Play 24kHz PCM chunk
                    if (state.audioPlayer && msg.data) {
                        state.audioPlayer.playChunk(msg.data);
                    }
                    break;

                case 'transcript':
                    appendTranscriptMessage(msg.role === 'model' ? 'model' : 'user', msg.text);
                    break;

                case 'tool_executing':
                    showToolExecution(msg.name, msg.args);
                    break;

                case 'tool_result':
                    hideToolExecution(msg.name, msg.result);
                    // Refresh tabs when data-modifying tools execute
                    if (['book_appointment', 'cancel_appointment'].includes(msg.name)) {
                        loadAppointments();
                    } else if (msg.name === 'leave_message') {
                        loadMessages();
                    }
                    break;

                case 'interrupted':
                    // Stop audio playback immediately on user interruption
                    if (state.audioPlayer) {
                        state.audioPlayer.interrupt();
                    }
                    updateLiveBadge('listening', 'Listening...');
                    break;

                case 'error':
                    showToast(msg.message, 'error');
                    appendTranscriptMessage('system', `Notice: ${msg.message}`);
                    break;
            }
        } catch (e) {
            console.error('Error handling WebSocket message:', e);
        }
    }

    function endVoiceCall() {
        if (!state.isCallActive && !state.ws) return;

        state.isCallActive = false;
        state.currentVolume = 0;

        if (state.ws) {
            if (state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'hangup' }));
            }
            state.ws.close();
            state.ws = null;
        }

        if (state.audioRecorder) {
            state.audioRecorder.stop();
            state.audioRecorder = null;
        }

        if (state.audioPlayer) {
            state.audioPlayer.close();
            state.audioPlayer = null;
        }

        updateCallUiState(false);
        updateLiveBadge('idle', 'Standby');
        connectionPill.classList.remove('live-active');
        connectionText.textContent = 'Ready';
        appendTranscriptMessage('system', 'Call ended. Thank you for visiting Apex Horizon Enterprises.');

        // Refresh call history
        setTimeout(loadCallLogs, 1200);
    }

    function toggleMute() {
        if (!state.audioRecorder) return;
        state.isMuted = !state.isMuted;
        state.audioRecorder.setMuted(state.isMuted);

        if (state.isMuted) {
            muteBtn.classList.add('muted');
            muteIcon.textContent = '🔇';
            muteLabel.textContent = 'Unmute';
            showToast('Microphone muted', 'info');
        } else {
            muteBtn.classList.remove('muted');
            muteIcon.textContent = '🎤';
            muteLabel.textContent = 'Mute';
            showToast('Microphone unmuted', 'info');
        }
    }

    function updateCallUiState(isActive) {
        if (isActive) {
            startCallBtn.style.display = 'none';
            endCallBtn.style.display = 'flex';
            muteBtn.style.display = 'flex';
            consoleHero.classList.add('active-call');
        } else {
            startCallBtn.style.display = 'flex';
            endCallBtn.style.display = 'none';
            muteBtn.style.display = 'none';
            consoleHero.classList.remove('active-call');
            hideToolExecution();
        }
    }

    function updateLiveBadge(type, text) {
        liveBadge.className = `live-badge ${type}`;
        badgeText.textContent = text;
    }

    function showToolExecution(toolName, args) {
        activeToolBanner.style.display = 'flex';
        let label = 'Processing front-desk request...';
        if (toolName === 'check_availability') label = 'Checking calendar slot availability...';
        else if (toolName === 'book_appointment') label = `Booking appointment for ${args.visitor_name || 'visitor'}...`;
        else if (toolName === 'cancel_appointment') label = 'Cancelling scheduled appointment...';
        else if (toolName === 'leave_message') label = `Logging message for ${args.recipient_name || 'staff member'}...`;
        else if (toolName === 'lookup_directory') label = `Searching directory for '${args.query || ''}'...`;
        else if (toolName === 'get_company_info') label = 'Retrieving office details & directions...';
        else if (toolName === 'transfer_call') label = `Routing call to ${args.recipient_or_department || 'extension'}...`;

        toolBannerText.textContent = label;
    }

    function hideToolExecution(toolName, result) {
        setTimeout(() => {
            activeToolBanner.style.display = 'none';
        }, 800);
    }

    // =========================================================================
    // Transcript Feed & Text Chat
    // =========================================================================

    function appendTranscriptMessage(role, text) {
        if (!text) return;

        if (role === 'system') {
            const notice = document.createElement('div');
            notice.className = 'system-notice';
            notice.textContent = text;
            transcriptFeed.appendChild(notice);
            transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
            return;
        }

        const msgDiv = document.createElement('div');
        msgDiv.className = `transcript-message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'model' ? '🎙️' : '👤';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = text;

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        transcriptFeed.appendChild(msgDiv);

        transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
    }

    async function sendTextMessage(text) {
        const query = text.trim();
        if (!query) return;

        chatInput.value = '';
        appendTranscriptMessage('user', query);

        if (state.isCallActive && state.ws && state.ws.readyState === WebSocket.OPEN) {
            // Forward text into live session
            state.ws.send(JSON.stringify({
                type: 'text',
                text: query
            }));
            updateLiveBadge('processing', 'Thinking...');
        } else {
            // Fallback REST Chat
            updateLiveBadge('processing', 'Aria Thinking...');
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: query,
                        api_key: state.apiKey
                    })
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.detail || 'Chat request failed');
                }

                appendTranscriptMessage('model', data.reply);
                updateLiveBadge('idle', 'Standby');

                // Optional browser speech synthesis for fallback chat
                if ('speechSynthesis' in window) {
                    const utter = new SpeechSynthesisUtterance(data.reply);
                    utter.rate = 1.05;
                    utter.pitch = 1.0;
                    window.speechSynthesis.speak(utter);
                }

                // If tools modified data, refresh
                if (data.actions && data.actions.length > 0) {
                    loadAppointments();
                    loadMessages();
                }

            } catch (err) {
                console.error('Chat error:', err);
                showToast(err.message, 'error');
                appendTranscriptMessage('system', `Error: ${err.message}`);
                updateLiveBadge('idle', 'Standby');
            }
        }
    }

    // =========================================================================
    // Front Desk Data Loaders & Tabs
    // =========================================================================

    async function loadCompanyDetails() {
        try {
            const res = await fetch('/api/company');
            const data = await res.json();
            state.companyInfo = data;

            document.getElementById('companyHeaderTitle').textContent = data.name;
            document.getElementById('receptionistNameDisplay').textContent = data.receptionist_name;

            // Render FAQs
            if (data.knowledge_base) {
                faqList.innerHTML = data.knowledge_base.map(kb => `
                    <div class="faq-item">
                        <div class="faq-title">${escapeHtml(kb.title)} (${escapeHtml(kb.category)})</div>
                        <div class="faq-content">${escapeHtml(kb.content)}</div>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading company info:', e);
        }
    }

    async function loadAppointments() {
        try {
            const res = await fetch('/api/appointments');
            const appts = await res.json();

            apptCountBadge.textContent = appts.filter(a => a.status === 'Confirmed').length;

            if (appts.length === 0) {
                appointmentsList.innerHTML = '<div class="system-notice">No upcoming appointments scheduled.</div>';
                return;
            }

            appointmentsList.innerHTML = appts.map(a => `
                <div class="appointment-card">
                    <div class="appointment-header">
                        <div class="appointment-visitor">${escapeHtml(a.visitor_name)}</div>
                        <div class="appointment-time">${escapeHtml(a.date)} at ${escapeHtml(a.time_slot)}</div>
                    </div>
                    <div class="appointment-details">
                        Meeting with: <strong>${escapeHtml(a.staff_name)}</strong> (${escapeHtml(a.department)})
                    </div>
                    <div class="appointment-purpose">
                        "${escapeHtml(a.purpose || 'Business consultation')}"
                    </div>
                    <div class="appointment-footer">
                        <span class="badge-status ${a.status.toLowerCase()}">${escapeHtml(a.status)}</span>
                        ${a.status !== 'Cancelled' ? `<button class="btn-cancel-appt" onclick="window.cancelAppointment(${a.id})">Cancel</button>` : ''}
                    </div>
                </div>
            `).join('');
        } catch (e) {
            appointmentsList.innerHTML = '<div class="system-notice">Failed to load appointments.</div>';
        }
    }

    async function loadMessages() {
        try {
            const res = await fetch('/api/messages');
            const msgs = await res.json();

            msgCountBadge.textContent = msgs.filter(m => !m.is_read).length;

            if (msgs.length === 0) {
                messagesList.innerHTML = '<div class="system-notice">Inbox is empty. No visitor messages.</div>';
                return;
            }

            messagesList.innerHTML = msgs.map(m => `
                <div class="message-card ${!m.is_read ? 'unread' : ''} ${m.urgency === 'Urgent' ? 'urgent' : ''}">
                    <div class="message-header">
                        <span class="message-caller">${escapeHtml(m.caller_name)} (${escapeHtml(m.contact_info)})</span>
                        <span class="badge-status ${m.urgency === 'Urgent' ? 'cancelled' : 'confirmed'}">${escapeHtml(m.urgency)}</span>
                    </div>
                    <div class="message-recipient">For: ${escapeHtml(m.recipient_name)}</div>
                    <div class="message-content">"${escapeHtml(m.message)}"</div>
                    <div class="message-footer">
                        <span>${new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        <div>
                            ${!m.is_read ? `<button class="btn-cancel-appt" style="color: var(--primary); margin-right: 0.5rem;" onclick="window.markMessageRead(${m.id})">Mark Read</button>` : ''}
                            <button class="btn-cancel-appt" onclick="window.deleteMessage(${m.id})">Delete</button>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            messagesList.innerHTML = '<div class="system-notice">Failed to load messages.</div>';
        }
    }

    async function loadDirectory(searchQuery = '') {
        try {
            const url = searchQuery ? `/api/directory?q=${encodeURIComponent(searchQuery)}` : '/api/directory';
            const res = await fetch(url);
            const staff = await res.json();

            if (staff.length === 0) {
                directoryList.innerHTML = '<div class="system-notice">No staff found matching your search.</div>';
                return;
            }

            directoryList.innerHTML = staff.map(s => {
                let statusClass = 'available';
                if (s.status.includes('Meeting')) statusClass = 'meeting';
                else if (s.status.includes('Office') || s.status.includes('Leave')) statusClass = 'away';

                return `
                    <div class="staff-card">
                        <div class="staff-info">
                            <h4>${escapeHtml(s.name)}</h4>
                            <p>${escapeHtml(s.title)} • ${escapeHtml(s.department)}</p>
                        </div>
                        <div class="staff-contact">
                            <span class="staff-ext">Ext. ${escapeHtml(s.phone_extension)}</span>
                            <span class="status-badge ${statusClass}">${escapeHtml(s.status)}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            directoryList.innerHTML = '<div class="system-notice">Failed to load directory.</div>';
        }
    }

    async function loadCallLogs() {
        try {
            const res = await fetch('/api/call-logs');
            const logs = await res.json();

            if (logs.length === 0) {
                logsList.innerHTML = '<div class="system-notice">No call sessions recorded yet.</div>';
                return;
            }

            logsList.innerHTML = logs.map(l => `
                <div class="appointment-card">
                    <div class="appointment-header">
                        <div class="appointment-visitor">${escapeHtml(l.caller_identifier)}</div>
                        <div class="appointment-time">${l.duration_seconds}s call</div>
                    </div>
                    <div class="appointment-details">
                        Started: ${new Date(l.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div class="appointment-purpose">
                        ${escapeHtml(l.summary)}
                    </div>
                </div>
            `).join('');
        } catch (e) {
            logsList.innerHTML = '<div class="system-notice">Failed to load call logs.</div>';
        }
    }

    // Global Action Helpers
    window.cancelAppointment = async function(id) {
        if (!confirm('Are you sure you want to cancel this appointment?')) return;
        try {
            const res = await fetch(`/api/appointments/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('Appointment cancelled', 'info');
                loadAppointments();
            }
        } catch (e) {
            showToast('Failed to cancel appointment', 'error');
        }
    };

    window.markMessageRead = async function(id) {
        try {
            const res = await fetch(`/api/messages/${id}/read`, { method: 'PATCH' });
            if (res.ok) {
                loadMessages();
            }
        } catch (e) {
            showToast('Failed to update message', 'error');
        }
    };

    window.deleteMessage = async function(id) {
        try {
            const res = await fetch(`/api/messages/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('Message deleted', 'info');
                loadMessages();
            }
        } catch (e) {
            showToast('Failed to delete message', 'error');
        }
    };

    // =========================================================================
    // Settings Modal
    // =========================================================================

    function openSettingsModal() {
        apiKeyInput.value = state.apiKey;
        voiceSelect.value = state.voice;
        settingsModal.classList.add('active');
    }

    function closeSettingsModal() {
        settingsModal.classList.remove('active');
    }

    async function saveSettings() {
        const key = apiKeyInput.value.trim();
        const selectedVoice = voiceSelect.value;

        state.apiKey = key;
        state.voice = selectedVoice;
        localStorage.setItem('gemini_api_key', key);
        localStorage.setItem('receptionist_voice', selectedVoice);

        if (key) {
            await fetch('/api/config/key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key })
            });
        }

        showToast('Settings saved successfully', 'success');
        closeSettingsModal();
    }

    // =========================================================================
    // UI Helpers & Toasts
    // =========================================================================

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = 'toast';
        const icon = type === 'error' ? '❌' : (type === 'success' ? '✅' : (type === 'warning' ? '⚠️' : 'ℹ️'));
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // =========================================================================
    // Event Listeners
    // =========================================================================

    startCallBtn.addEventListener('click', startVoiceCall);
    endCallBtn.addEventListener('click', endVoiceCall);
    muteBtn.addEventListener('click', toggleMute);

    sendChatBtn.addEventListener('click', () => sendTextMessage(chatInput.value));
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendTextMessage(chatInput.value);
        }
    });

    // Quick suggestion prompt pills
    document.querySelectorAll('.prompt-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const prompt = pill.getAttribute('data-prompt');
            chatInput.value = prompt;
            sendTextMessage(prompt);
        });
    });

    // Tab Navigation
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(target).classList.add('active');

            if (target === 'appointmentsTab') loadAppointments();
            else if (target === 'messagesTab') loadMessages();
            else if (target === 'directoryTab') loadDirectory();
            else if (target === 'logsTab') loadCallLogs();
        });
    });

    // Refresh Buttons
    document.getElementById('refreshApptsBtn')?.addEventListener('click', loadAppointments);
    document.getElementById('refreshMsgsBtn')?.addEventListener('click', loadMessages);
    document.getElementById('refreshLogsBtn')?.addEventListener('click', loadCallLogs);

    // Directory Search
    directorySearchInput.addEventListener('input', (e) => {
        loadDirectory(e.target.value);
    });

    // Settings Modal
    openSettingsBtn.addEventListener('click', openSettingsModal);
    closeSettingsBtn.addEventListener('click', closeSettingsModal);
    cancelSettingsBtn.addEventListener('click', closeSettingsModal);
    saveSettingsBtn.addEventListener('click', saveSettings);

    // Initial Data Fetch
    loadCompanyDetails();
    loadAppointments();
    loadMessages();
    loadDirectory();
});
