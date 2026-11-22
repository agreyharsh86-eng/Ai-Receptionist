/**
 * HR Enterprises Healthcare SaaS & AI Voice Receptionist
 * Main Frontend Application Controller
 * Handles View Routing, Real-Time Statistics, Appointment Scheduling,
 * Doctors Directory, Patient Registry, Floating Jack AI Assistant, and Web Audio.
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // Application State
    // =========================================================================
    const state = {
        currentView: 'dashboardView',
        isCallActive: false,
        isMuted: false,
        isJackSpeaking: false,
        isAssistantOpen: false,
        isSpeechRecognitionMode: false,
        apiKey: localStorage.getItem('gemini_api_key') || '',
        voice: localStorage.getItem('receptionist_voice') || 'Aoede',
        customWsUrl: localStorage.getItem('custom_ws_url') || '',
        ws: null,
        audioRecorder: null,
        audioPlayer: null,
        speechRecognition: null,
        visualizerAnimationId: null,
        currentVolume: 0,
        companyInfo: null,
        chatHistory: [],
        allAppointments: [],
        allDoctors: [],
        allPatients: [],
        allMessages: [],
        currentApptFilter: 'all',
        currentMsgFilter: 'all',
        selectedBookingDoctor: null,
        authToken: localStorage.getItem('jack_auth_token') || '',
        currentUser: null,
        authChannel: 'email',
        authIdentifier: '',
        otpTimerInterval: null,
        otpSecondsLeft: 30
    };

    // =========================================================================
    // DOM Elements Cache
    // =========================================================================
    // Topbar & Clock
    const systemClock = document.getElementById('systemClock');
    const currentDateDisplay = document.getElementById('currentDateDisplay');
    const currentPageTitle = document.getElementById('currentPageTitle');
    const connectionPill = document.getElementById('connectionPill');
    const connectionText = document.getElementById('connectionText');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const appSidebar = document.getElementById('appSidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const globalSearchInput = document.getElementById('globalSearchInput');
    const notificationsBtn = document.getElementById('notificationsBtn');
    const notificationsDropdown = document.getElementById('notificationsDropdown');
    const notifBadge = document.getElementById('notifBadge');
    const notifDropdownCount = document.getElementById('notifDropdownCount');
    const notifDropdownList = document.getElementById('notifDropdownList');
    const headerSettingsBtn = document.getElementById('headerSettingsBtn');
    const openSettingsBtn = document.getElementById('openSettingsBtn');

    // Auth & User Elements
    const topbarUserPill = document.getElementById('topbarUserPill');
    const topbarUserAvatar = document.getElementById('topbarUserAvatar');
    const topbarUserName = document.getElementById('topbarUserName');
    const topbarUserStatus = document.getElementById('topbarUserStatus');
    const sidebarUserName = document.getElementById('sidebarUserName');
    const sidebarUserRole = document.getElementById('sidebarUserRole');
    const sidebarUserAvatar = document.getElementById('sidebarUserAvatar');
    const sidebarAuthActionBtn = document.getElementById('sidebarAuthActionBtn');

    // Auth Modal Elements
    const authModal = document.getElementById('authModal');
    const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
    const authAlert = document.getElementById('authAlert');
    const authStepRequest = document.getElementById('authStepRequest');
    const authStepVerify = document.getElementById('authStepVerify');
    const authStepProfile = document.getElementById('authStepProfile');
    const authTabEmail = document.getElementById('authTabEmail');
    const authTabPhone = document.getElementById('authTabPhone');
    const authNameGroup = document.getElementById('authNameGroup');
    const authNameInput = document.getElementById('authNameInput');
    const authEmailGroup = document.getElementById('authEmailGroup');
    const authEmailInput = document.getElementById('authEmailInput');
    const authPhoneGroup = document.getElementById('authPhoneGroup');
    const authPhoneInput = document.getElementById('authPhoneInput');
    const sendOtpBtn = document.getElementById('sendOtpBtn');
    const authBackToRequestBtn = document.getElementById('authBackToRequestBtn');
    const authTargetDisplay = document.getElementById('authTargetDisplay');
    const otpInputsGrid = document.getElementById('otpInputsGrid');
    const otpDigitBoxes = document.querySelectorAll('.otp-digit-box');
    const otpCountdownText = document.getElementById('otpCountdownText');
    const otpTimerBar = document.getElementById('otpTimerBar');
    const authResendBtn = document.getElementById('authResendBtn');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const profileLargeAvatar = document.getElementById('profileLargeAvatar');
    const profileLargeName = document.getElementById('profileLargeName');
    const profileLargeIdentifier = document.getElementById('profileLargeIdentifier');
    const profileMetaAuthType = document.getElementById('profileMetaAuthType');
    const profileMetaCreatedAt = document.getElementById('profileMetaCreatedAt');
    const profileMetaLastLogin = document.getElementById('profileMetaLastLogin');
    const authSwitchAccountBtn = document.getElementById('authSwitchAccountBtn');
    const authSignOutBtn = document.getElementById('authSignOutBtn');

    // Sidebar Nav & Badges
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const viewPanels = document.querySelectorAll('.view-panel');
    const sidebarApptBadge = document.getElementById('sidebarApptBadge');
    const sidebarDoctorBadge = document.getElementById('sidebarDoctorBadge');
    const sidebarPatientBadge = document.getElementById('sidebarPatientBadge');
    const sidebarMsgBadge = document.getElementById('sidebarMsgBadge');
    const quickTalkBtn = document.getElementById('quickTalkBtn');
    const quickTriggerJackBtn = document.getElementById('quickTriggerJackBtn');

    // Dashboard Stat Cards & Mini Previews
    const statTotalAppts = document.getElementById('statTotalAppts');
    const statAvailableDocs = document.getElementById('statAvailableDocs');
    const statTotalPatients = document.getElementById('statTotalPatients');
    const statPendingAppts = document.getElementById('statPendingAppts');
    const statTotalDocsSub = document.getElementById('statTotalDocsSub');
    const dashboardApptsTbody = document.getElementById('dashboardApptsTbody');
    const dashboardDoctorsMini = document.getElementById('dashboardDoctorsMini');
    const dashboardMessagesMini = document.getElementById('dashboardMessagesMini');
    const refreshDashboardBtn = document.getElementById('refreshDashboardBtn');
    const quickNewApptBtn = document.getElementById('quickNewApptBtn');
    const quickNewDocBtn = document.getElementById('quickNewDocBtn');
    const viewAllApptsLink = document.getElementById('viewAllApptsLink');
    const viewAllDoctorsLink = document.getElementById('viewAllDoctorsLink');
    const viewAllMessagesLink = document.getElementById('viewAllMessagesLink');

    // Appointments Elements
    const apptFilterGroup = document.getElementById('apptFilterGroup');
    const apptSearchInput = document.getElementById('apptSearchInput');
    const appointmentsList = document.getElementById('appointmentsList');
    const openBookApptModalBtn = document.getElementById('openBookApptModalBtn');
    const refreshApptsBtn = document.getElementById('refreshApptsBtn');
    const countFilterAll = document.getElementById('countFilterAll');
    const countFilterToday = document.getElementById('countFilterToday');
    const countFilterUpcoming = document.getElementById('countFilterUpcoming');
    const countFilterCompleted = document.getElementById('countFilterCompleted');
    const countFilterCancelled = document.getElementById('countFilterCancelled');

    // Doctors Elements
    const doctorsList = document.getElementById('doctorsList');
    const doctorSearchInput = document.getElementById('doctorSearchInput');
    const doctorSpecFilter = document.getElementById('doctorSpecFilter');
    const adminAddDoctorBtn = document.getElementById('adminAddDoctorBtn');
    const refreshDoctorsBtn = document.getElementById('refreshDoctorsBtn');

    // Patients Elements
    const patientsList = document.getElementById('patientsList');
    const patientSearchInput = document.getElementById('patientSearchInput');
    const patientNewApptBtn = document.getElementById('patientNewApptBtn');
    const refreshPatientsBtn = document.getElementById('refreshPatientsBtn');

    // Messages Elements
    const messagesList = document.getElementById('messagesList');
    const msgFilterGroup = document.getElementById('msgFilterGroup');
    const refreshMsgsBtn = document.getElementById('refreshMsgsBtn');
    const msgFilterAllCount = document.getElementById('msgFilterAllCount');
    const msgFilterUnreadCount = document.getElementById('msgFilterUnreadCount');
    const msgFilterUrgentCount = document.getElementById('msgFilterUrgentCount');

    // Directory, FAQ, Logs
    const directoryList = document.getElementById('directoryList');
    const directorySearchInput = document.getElementById('directorySearchInput');
    const refreshDirectoryBtn = document.getElementById('refreshDirectoryBtn');
    const faqList = document.getElementById('faqList');
    const logsList = document.getElementById('logsList');
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');

    // Floating Jack AI Assistant
    const jackFloatingContainer = document.getElementById('jackFloatingContainer');
    const jackFloatingBtn = document.getElementById('jackFloatingBtn');
    const jackAssistantPopup = document.getElementById('jackAssistantPopup');
    const closeAssistantBtn = document.getElementById('closeAssistantBtn');
    const minimizeAssistantBtn = document.getElementById('minimizeAssistantBtn');
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
    const micVoiceBtn = document.getElementById('micVoiceBtn');
    const waveformCanvas = document.getElementById('waveformCanvas');
    const promptPills = document.querySelectorAll('.prompt-pill');

    // Modals
    const bookDoctorModal = document.getElementById('bookDoctorModal');
    const closeBookDoctorBtn = document.getElementById('closeBookDoctorBtn');
    const cancelBookDoctorBtn = document.getElementById('cancelBookDoctorBtn');
    const confirmBookDoctorBtn = document.getElementById('confirmBookDoctorBtn');
    const bookingDoctorInfo = document.getElementById('bookingDoctorInfo');
    const bookPatientName = document.getElementById('bookPatientName');
    const bookPatientContact = document.getElementById('bookPatientContact');
    const bookApptDate = document.getElementById('bookApptDate');
    const bookApptSlot = document.getElementById('bookApptSlot');
    const bookApptPurpose = document.getElementById('bookApptPurpose');

    const addDoctorModal = document.getElementById('addDoctorModal');
    const closeAddDoctorBtn = document.getElementById('closeAddDoctorBtn');
    const cancelAddDoctorBtn = document.getElementById('cancelAddDoctorBtn');
    const confirmAddDoctorBtn = document.getElementById('confirmAddDoctorBtn');
    const newDocName = document.getElementById('newDocName');
    const newDocSpec = document.getElementById('newDocSpec');
    const newDocDept = document.getElementById('newDocDept');
    const newDocQual = document.getElementById('newDocQual');
    const newDocExp = document.getElementById('newDocExp');
    const newDocFee = document.getElementById('newDocFee');
    const newDocDays = document.getElementById('newDocDays');
    const newDocSlots = document.getElementById('newDocSlots');
    const newDocEmail = document.getElementById('newDocEmail');
    const newDocExt = document.getElementById('newDocExt');
    const newDocBio = document.getElementById('newDocBio');

    const apptDetailsModal = document.getElementById('apptDetailsModal');
    const closeApptDetailsBtn = document.getElementById('closeApptDetailsBtn');
    const dismissApptDetailsBtn = document.getElementById('dismissApptDetailsBtn');
    const apptDetailsContent = document.getElementById('apptDetailsContent');

    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const voiceSelect = document.getElementById('voiceSelect');
    const customWsUrlInput = document.getElementById('customWsUrlInput');

    const toastContainer = document.getElementById('toastContainer');

    // =========================================================================
    // System Clock & Live Date
    // =========================================================================
    function updateClock() {
        const now = new Date();
        if (systemClock) {
            systemClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' EST';
        }
        if (currentDateDisplay) {
            currentDateDisplay.textContent = now.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
        }
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Default book appointment date to tomorrow
    if (bookApptDate) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        bookApptDate.value = tomorrow.toISOString().split('T')[0];
    }

    // =========================================================================
    // View Switching & Sidebar Navigation
    // =========================================================================
    const viewTitles = {
        dashboardView: 'Dashboard Overview',
        appointmentsView: 'Appointment Management',
        doctorsView: 'Doctors & Specialists Directory',
        patientsView: 'Registered Patient Records',
        messagesView: 'Caller Inquiries & Voicemails',
        directoryView: 'Corporate Staff Directory',
        faqView: 'Office Policy & Facility Info',
        logsView: 'Reception Call History & Logs'
    };

    function switchView(targetViewId) {
        state.currentView = targetViewId;

        // Update nav items active state
        navItems.forEach(item => {
            if (item.getAttribute('data-view') === targetViewId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Show target view panel
        viewPanels.forEach(panel => {
            if (panel.id === targetViewId) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });

        // Update Page Title
        if (currentPageTitle && viewTitles[targetViewId]) {
            currentPageTitle.textContent = viewTitles[targetViewId];
        }

        // Close mobile sidebar if open
        if (appSidebar) appSidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');

        // Trigger view-specific loads
        if (targetViewId === 'dashboardView') loadDashboardStats();
        else if (targetViewId === 'appointmentsView') loadAppointments();
        else if (targetViewId === 'doctorsView') loadDoctors();
        else if (targetViewId === 'patientsView') loadPatients();
        else if (targetViewId === 'messagesView') loadMessages();
        else if (targetViewId === 'directoryView') loadDirectory();
        else if (targetViewId === 'faqView') loadCompanyDetails();
        else if (targetViewId === 'logsView') loadCallLogs();
    }

    // Attach click handlers to sidebar nav items
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        });
    });

    // Quick links from Dashboard
    if (viewAllApptsLink) viewAllApptsLink.addEventListener('click', () => switchView('appointmentsView'));
    if (viewAllDoctorsLink) viewAllDoctorsLink.addEventListener('click', () => switchView('doctorsView'));
    if (viewAllMessagesLink) viewAllMessagesLink.addEventListener('click', () => switchView('messagesView'));

    // Mobile Menu Toggle
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', () => {
            appSidebar.classList.toggle('open');
            sidebarBackdrop.classList.toggle('show');
        });
    }
    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', () => {
            appSidebar.classList.remove('open');
            sidebarBackdrop.classList.remove('show');
        });
    }

    // =========================================================================
    // Waveform Visualizer Canvas
    // =========================================================================
    const canvasCtx = waveformCanvas ? waveformCanvas.getContext('2d') : null;

    function drawWaveform() {
        if (!waveformCanvas || !canvasCtx) return;
        state.visualizerAnimationId = requestAnimationFrame(drawWaveform);

        const width = waveformCanvas.width;
        const height = waveformCanvas.height;
        canvasCtx.clearRect(0, 0, width, height);

        let freqData = new Uint8Array(0);
        if (state.audioPlayer && state.audioPlayer.isPlaying) {
            freqData = state.audioPlayer.getFrequencyData();
        }

        const barCount = 34;
        const barWidth = 4;
        const gap = (width - (barCount * barWidth)) / (barCount - 1);

        for (let i = 0; i < barCount; i++) {
            let barHeight = 3;

            if (state.isCallActive) {
                if (state.audioPlayer && state.audioPlayer.isPlaying && freqData.length > 0) {
                    const freqIdx = Math.floor((i / barCount) * freqData.length);
                    const val = freqData[freqIdx] / 255.0;
                    barHeight = Math.max(3, val * (height * 0.9));
                } else if (state.isJackSpeaking) {
                    const time = Date.now() * 0.008;
                    const wave = Math.sin(time + i * 0.4) * (height * 0.45) + Math.cos(time * 0.3 + i * 0.2) * (height * 0.25);
                    barHeight = Math.max(4, Math.abs(wave));
                } else if (state.currentVolume > 0.01) {
                    const wave = Math.sin((i / barCount) * Math.PI) * state.currentVolume * (height * 0.85);
                    barHeight = Math.max(3, wave);
                } else {
                    const time = Date.now() * 0.004;
                    barHeight = 3 + Math.sin(time + i * 0.35) * 2.5;
                }
            }

            const x = i * (barWidth + gap);
            const y = (height - barHeight) / 2;

            const grad = canvasCtx.createLinearGradient(x, y, x, y + barHeight);
            if ((state.audioPlayer && state.audioPlayer.isPlaying) || state.isJackSpeaking) {
                grad.addColorStop(0, '#00f0ff');
                grad.addColorStop(1, '#3b82f6');
            } else if (state.currentVolume > 0.05) {
                grad.addColorStop(0, '#38bdf8');
                grad.addColorStop(1, '#0284c7');
            } else {
                grad.addColorStop(0, 'rgba(0, 240, 255, 0.4)');
                grad.addColorStop(1, 'rgba(255, 255, 255, 0.1)');
            }

            canvasCtx.fillStyle = grad;
            canvasCtx.beginPath();
            if (canvasCtx.roundRect) {
                canvasCtx.roundRect(x, y, barWidth, barHeight, 2);
            } else {
                canvasCtx.rect(x, y, barWidth, barHeight);
            }
            canvasCtx.fill();
        }
    }
    drawWaveform();

    // =========================================================================
    // Floating Jack AI Assistant Window Management
    // =========================================================================
    function toggleAssistantWindow(open) {
        state.isAssistantOpen = typeof open === 'boolean' ? open : !state.isAssistantOpen;
        if (state.isAssistantOpen) {
            jackAssistantPopup.classList.add('show');
            if (chatInput) chatInput.focus();
        } else {
            jackAssistantPopup.classList.remove('show');
        }
    }

    if (jackFloatingBtn) {
        jackFloatingBtn.addEventListener('click', () => toggleAssistantWindow());
    }
    if (closeAssistantBtn) {
        closeAssistantBtn.addEventListener('click', () => toggleAssistantWindow(false));
    }
    if (minimizeAssistantBtn) {
        minimizeAssistantBtn.addEventListener('click', () => toggleAssistantWindow(false));
    }
    if (quickTalkBtn) {
        quickTalkBtn.addEventListener('click', () => toggleAssistantWindow(true));
    }
    if (quickTriggerJackBtn) {
        quickTriggerJackBtn.addEventListener('click', () => toggleAssistantWindow(true));
    }

    function updateLiveBadge(type, text) {
        if (liveBadge) {
            liveBadge.className = `live-badge ${type}`;
        }
        if (badgeText) {
            badgeText.textContent = text;
        }
        const sidebarAiState = document.getElementById('sidebarAiState');
        if (sidebarAiState) {
            if (type === 'speaking') sidebarAiState.textContent = 'Speaking...';
            else if (type === 'listening') sidebarAiState.textContent = 'Listening...';
            else if (type === 'processing') sidebarAiState.textContent = 'Thinking...';
            else sidebarAiState.textContent = 'Online & Ready';
        }
    }

    function showToolExecution(toolName, args) {
        if (!activeToolBanner || !toolBannerText) return;
        activeToolBanner.style.display = 'flex';
        let label = 'Processing front-desk clinical request...';
        if (toolName === 'search_doctors') label = 'Searching medical specialists in directory...';
        else if (toolName === 'check_availability') label = 'Checking live doctor calendar availability...';
        else if (toolName === 'book_appointment') label = `Confirming verified booking with ${args.staff_or_department || 'doctor'}...`;
        else if (toolName === 'cancel_appointment') label = 'Cancelling requested appointment...';
        else if (toolName === 'leave_message') label = `Logging caller message for ${args.recipient_name || 'clinic'}...`;
        else if (toolName === 'lookup_directory') label = `Searching directory for '${args.query || ''}'...`;
        else if (toolName === 'get_company_info') label = 'Retrieving hospital hours & parking directions...';
        else if (toolName === 'transfer_call') label = `Routing call to ${args.recipient_or_department || 'department'}...`;

        toolBannerText.textContent = label;
    }

    function hideToolExecution() {
        if (!activeToolBanner) return;
        setTimeout(() => {
            activeToolBanner.style.display = 'none';
        }, 800);
    }

    function appendTranscriptMessage(role, text) {
        if (!transcriptFeed || !text) return;

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

    // Prompt Suggestions in Assistant
    promptPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const promptText = pill.getAttribute('data-prompt');
            if (promptText) {
                sendTextMessage(promptText);
            }
        });
    });

    // =========================================================================
    // Speech Synthesis & Voice Processing
    // =========================================================================
    function speakJack(text, onComplete) {
        if (!('speechSynthesis' in window)) {
            if (onComplete) onComplete();
            return;
        }
        try {
            window.speechSynthesis.cancel();
            window.speechSynthesis.resume();
        } catch (e) { }

        // Clean markdown symbols for smooth, natural voice speech
        const spokenText = (text || '')
            .replace(/[*_#`~\[\]\(\)]/g, '')
            .replace(/•/g, '')
            .replace(/\s+/g, ' ')
            .trim();

        if (!spokenText) {
            if (onComplete) onComplete();
            return;
        }

        const utterance = new SpeechSynthesisUtterance(spokenText);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.lang = 'en-US';

        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Alex')));
        if (preferred) utterance.voice = preferred;

        utterance.onstart = () => {
            state.isJackSpeaking = true;
            updateLiveBadge('speaking', 'Jack Speaking');
        };

        utterance.onend = () => {
            state.isJackSpeaking = false;
            if (state.isCallActive) {
                updateLiveBadge('listening', 'Listening...');
            } else {
                updateLiveBadge('idle', 'Standby');
            }
            if (onComplete) onComplete();
        };

        utterance.onerror = () => {
            state.isJackSpeaking = false;
            updateLiveBadge('idle', 'Standby');
            if (onComplete) onComplete();
        };

        window.speechSynthesis.speak(utterance);
    }

    // =========================================================================
    // Browser Voice Session (Speech Recognition Fallback Mode)
    // =========================================================================
    function startBrowserVoiceSession() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            showToast('Voice speech recognition not supported in this browser. Please use text chat.', 'error');
            return;
        }

        state.isSpeechRecognitionMode = true;
        state.isCallActive = true;
        updateCallUiState(true);
        updateLiveBadge('listening', 'Listening...');
        appendTranscriptMessage('system', 'Connected to Jack via Voice Assistant mode. Speak into your microphone!');

        if (state.chatHistory.length === 0) {
            const greetingText = "Good day! Welcome to HR Enterprises. My name is Jack, your AI Voice Receptionist. How may I assist you with your appointment or inquiry today?";
            state.chatHistory.push({ role: 'model', text: greetingText });
            appendTranscriptMessage('model', greetingText);
            speakJack(greetingText);
        }

        const recognition = new SpeechRec();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onspeechstart = () => {
            if (state.isJackSpeaking) {
                try { window.speechSynthesis.cancel(); } catch (e) { }
                state.isJackSpeaking = false;
                updateLiveBadge('listening', 'Listening...');
            }
        };

        recognition.onresult = async (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript.trim();
            if (!transcript || state.isMuted) return;

            if (state.isJackSpeaking) {
                try { window.speechSynthesis.cancel(); } catch (e) { }
                state.isJackSpeaking = false;
            }

            appendTranscriptMessage('user', transcript);
            updateLiveBadge('processing', 'Jack Thinking...');
            state.chatHistory.push({ role: 'user', text: transcript });

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: transcript,
                        history: state.chatHistory,
                        api_key: state.apiKey
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Chat request failed');

                state.chatHistory.push({ role: 'model', text: data.reply });
                appendTranscriptMessage('model', data.reply);
                speakJack(data.reply);

                if (data.actions && data.actions.length > 0) {
                    loadDashboardStats();
                    loadAppointments();
                    loadMessages();
                    loadDoctors();
                    loadPatients();
                }
            } catch (err) {
                console.error('Speech interaction error:', err);
                showToast(err.message, 'error');
                updateLiveBadge('listening', 'Listening...');
            }
        };

        recognition.onerror = (e) => {
            if (e.error !== 'no-speech') {
                console.warn('Speech recognition warning:', e.error);
            }
        };

        recognition.onend = () => {
            if (state.isCallActive && state.isSpeechRecognitionMode) {
                try { recognition.start(); } catch (e) { }
            }
        };

        try {
            recognition.start();
            state.speechRecognition = recognition;
        } catch (e) {
            console.error('Could not start SpeechRecognition:', e);
            showToast('Microphone access denied', 'error');
            endVoiceCall();
        }
    }

    // =========================================================================
    // Live Voice Call Management (WebSocket Mode)
    // =========================================================================
    async function startVoiceCall() {
        if (state.isCallActive) return;

        updateLiveBadge('processing', 'Connecting...');
        if (connectionText) connectionText.textContent = 'Connecting...';

        const isVercelHost = window.location.hostname.endsWith('vercel.app') || window.location.hostname.includes('vercel');
        if ((isVercelHost && !state.customWsUrl) || (!state.apiKey && !state.customWsUrl)) {
            startBrowserVoiceSession();
            return;
        }

        try {
            state.audioPlayer = new window.PcmAudioPlayer(24000);
            state.audioPlayer.init();
            state.audioPlayer.onPlaybackStateChange = (isPlaying) => {
                if (isPlaying) updateLiveBadge('speaking', 'Jack Speaking');
                else if (state.isCallActive) updateLiveBadge('listening', 'Listening...');
            };

            state.audioRecorder = new window.PcmAudioRecorder({
                targetSampleRate: 16000,
                onAudioChunk: (base64Pcm) => {
                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({ type: 'audio', data: base64Pcm }));
                    }
                },
                onVolumeChange: (vol) => {
                    state.currentVolume = vol;
                }
            });
            await state.audioRecorder.start();

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const queryParams = new URLSearchParams();
            if (state.apiKey) queryParams.set('api_key', state.apiKey);
            if (state.voice) queryParams.set('voice', state.voice);

            let wsUrl = state.customWsUrl || `${protocol}//${window.location.host}/ws/live?${queryParams.toString()}`;
            let connectionOpened = false;
            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                connectionOpened = true;
                state.isCallActive = true;
                updateCallUiState(true);
                if (connectionPill) connectionPill.classList.add('live-active');
                if (connectionText) connectionText.textContent = 'Live Audio Call';
                appendTranscriptMessage('system', 'Connected to front desk. Jack is listening...');
            };

            state.ws.onmessage = (event) => {
                handleWebSocketMessage(event.data);
            };

            state.ws.onerror = (err) => {
                console.warn('WebSocket connection error:', err);
                if (!connectionOpened) {
                    showToast('Switching to Voice Assistant mode...', 'info');
                    if (state.audioRecorder) { state.audioRecorder.stop(); state.audioRecorder = null; }
                    if (state.audioPlayer) { state.audioPlayer.close(); state.audioPlayer = null; }
                    startBrowserVoiceSession();
                } else {
                    showToast('WebSocket connection error', 'error');
                }
            };

            state.ws.onclose = () => {
                if (connectionOpened) endVoiceCall();
            };

        } catch (err) {
            console.error('Failed to start call:', err);
            startBrowserVoiceSession();
        }
    }

    function endVoiceCall() {
        state.isCallActive = false;
        state.isSpeechRecognitionMode = false;
        state.isMuted = false;
        state.currentVolume = 0;

        try { window.speechSynthesis.cancel(); } catch (e) { }

        if (state.speechRecognition) {
            try { state.speechRecognition.stop(); } catch (e) { }
            state.speechRecognition = null;
        }

        if (state.audioRecorder) {
            state.audioRecorder.stop();
            state.audioRecorder = null;
        }

        if (state.audioPlayer) {
            state.audioPlayer.close();
            state.audioPlayer = null;
        }

        if (state.ws) {
            try { state.ws.close(); } catch (e) { }
            state.ws = null;
        }

        updateCallUiState(false);
        updateLiveBadge('idle', 'Standby');
        if (connectionPill) connectionPill.classList.remove('live-active');
        if (connectionText) connectionText.textContent = 'Ready';
        appendTranscriptMessage('system', 'Voice call ended.');
    }

    function updateCallUiState(isActive) {
        if (startCallBtn) startCallBtn.style.display = isActive ? 'none' : 'flex';
        if (endCallBtn) endCallBtn.style.display = isActive ? 'flex' : 'none';
        if (muteBtn) muteBtn.style.display = isActive ? 'flex' : 'none';
        hideToolExecution();
    }

    function handleWebSocketMessage(rawMsg) {
        try {
            const msg = JSON.parse(rawMsg);
            switch (msg.type) {
                case 'status':
                    if (msg.status === 'connected') updateLiveBadge('listening', 'Listening...');
                    break;
                case 'audio':
                    if (state.audioPlayer && msg.data) state.audioPlayer.playChunk(msg.data);
                    break;
                case 'transcript':
                    appendTranscriptMessage(msg.role === 'model' ? 'model' : 'user', msg.text);
                    break;
                case 'tool_executing':
                    showToolExecution(msg.name, msg.args);
                    break;
                case 'tool_result':
                    hideToolExecution();
                    if (['book_appointment', 'cancel_appointment'].includes(msg.name)) {
                        loadDashboardStats();
                        loadAppointments();
                        loadPatients();
                    } else if (msg.name === 'leave_message') {
                        loadDashboardStats();
                        loadMessages();
                    }
                    break;
                case 'interrupted':
                    if (state.audioPlayer) state.audioPlayer.interrupt();
                    updateLiveBadge('listening', 'Listening...');
                    break;
                case 'error':
                    showToast(msg.message, 'error');
                    appendTranscriptMessage('system', `Notice: ${msg.message}`);
                    break;
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    }

    // Call Buttons Listeners
    if (startCallBtn) startCallBtn.addEventListener('click', () => startVoiceCall());
    if (endCallBtn) endCallBtn.addEventListener('click', () => endVoiceCall());
    if (muteBtn) {
        muteBtn.addEventListener('click', () => {
            state.isMuted = !state.isMuted;
            if (muteIcon) muteIcon.textContent = state.isMuted ? '🔇' : '🎤';
            if (muteLabel) muteLabel.textContent = state.isMuted ? 'Unmute' : 'Mute';
            showToast(state.isMuted ? 'Microphone muted' : 'Microphone unmuted', 'info');
        });
    }

    // =========================================================================
    // Text Chat & Fallback REST Execution
    // =========================================================================
    async function sendTextMessage(text) {
        const query = (text || '').trim();
        if (!query) return;

        if (chatInput) chatInput.value = '';
        appendTranscriptMessage('user', query);
        state.chatHistory.push({ role: 'user', text: query });

        if (state.isCallActive && state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'text', text: query }));
            updateLiveBadge('processing', 'Thinking...');
        } else {
            updateLiveBadge('processing', 'Jack Thinking...');
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: query,
                        history: state.chatHistory,
                        api_key: state.apiKey
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Chat request failed');

                state.chatHistory.push({ role: 'model', text: data.reply });
                appendTranscriptMessage('model', data.reply);
                updateLiveBadge('idle', 'Standby');
                speakJack(data.reply);

                if (data.actions && data.actions.length > 0) {
                    loadDashboardStats();
                    loadAppointments();
                    loadMessages();
                    loadDoctors();
                    loadPatients();
                }

            } catch (err) {
                console.error('Chat error:', err);
                showToast(err.message, 'error');
                appendTranscriptMessage('system', `Error: ${err.message}`);
                updateLiveBadge('idle', 'Standby');
            }
        }
    }

    if (sendChatBtn) {
        sendChatBtn.addEventListener('click', () => {
            if (chatInput) sendTextMessage(chatInput.value);
        });
    }
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendTextMessage(chatInput.value);
            }
        });
    }
    if (micVoiceBtn) {
        micVoiceBtn.addEventListener('click', () => {
            if (state.isCallActive) {
                endVoiceCall();
            } else {
                startBrowserVoiceSession();
            }
        });
    }

    // =========================================================================
    // Data Loading: Dashboard Statistics & Overview
    // =========================================================================
    async function loadDashboardStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const stats = await res.json();

            if (statTotalAppts) statTotalAppts.textContent = stats.total_appointments || 0;
            if (statAvailableDocs) statAvailableDocs.textContent = stats.available_doctors || 0;
            if (statTotalDocsSub) statTotalDocsSub.textContent = `out of ${stats.total_doctors || 10} doctors`;
            if (statTotalPatients) statTotalPatients.textContent = stats.registered_patients || 0;
            if (statPendingAppts) statPendingAppts.textContent = stats.pending_appointments || 0;

            if (sidebarApptBadge) sidebarApptBadge.textContent = stats.total_appointments || 0;
            if (sidebarDoctorBadge) sidebarDoctorBadge.textContent = stats.available_doctors || 0;
            if (sidebarPatientBadge) sidebarPatientBadge.textContent = stats.registered_patients || 0;
            if (sidebarMsgBadge) sidebarMsgBadge.textContent = stats.unread_messages || 0;
            if (notifBadge) notifBadge.textContent = stats.unread_messages || 0;
            if (notifDropdownCount) notifDropdownCount.textContent = `${stats.unread_messages || 0} Unread`;

            // Load sub-previews
            loadDashboardApptsPreview();
            loadDashboardDoctorsPreview();
            loadDashboardMessagesPreview();
        } catch (e) {
            console.error('Error loading stats:', e);
        }
    }

    async function loadDashboardApptsPreview() {
        try {
            const res = await fetch('/api/appointments');
            const appts = await res.json();
            state.allAppointments = appts;

            if (!dashboardApptsTbody) return;

            if (appts.length === 0) {
                dashboardApptsTbody.innerHTML = `<tr><td colspan="5" class="table-loading">No scheduled consultations found.</td></tr>`;
                return;
            }

            const previewList = appts.slice(0, 5);
            dashboardApptsTbody.innerHTML = previewList.map(a => `
                <tr>
                    <td><strong>👤 ${escapeHtml(a.visitor_name)}</strong></td>
                    <td>🩺 ${escapeHtml(a.staff_name)} <span style="font-size: 0.72rem; color: var(--text-muted);">(${escapeHtml(a.department)})</span></td>
                    <td>📅 ${escapeHtml(a.date)} • ⏰ ${escapeHtml(a.time_slot)}</td>
                    <td><span class="badge-status ${a.status.toLowerCase()}">${escapeHtml(a.status)}</span></td>
                    <td>
                        <button class="btn-table-action view" onclick="window.viewAppointmentDetails(${a.id})">Details</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error('Error previewing appts:', e);
        }
    }

    async function loadDashboardDoctorsPreview() {
        try {
            const res = await fetch('/api/doctors');
            const docs = await res.json();
            state.allDoctors = docs;

            if (!dashboardDoctorsMini) return;

            const topDocs = docs.slice(0, 4);
            dashboardDoctorsMini.innerHTML = topDocs.map(d => `
                <div class="mini-doctor-item">
                    <div class="mini-doc-left">
                        <div class="mini-doc-avatar">${d.avatar_emoji || '🩺'}</div>
                        <div class="mini-doc-info">
                            <h4>${escapeHtml(d.name)}</h4>
                            <p>${escapeHtml(d.specialization)} • ${escapeHtml(d.department)}</p>
                        </div>
                    </div>
                    <button class="btn-book-quick" onclick="window.openDoctorBookingModal(${d.id})">Book</button>
                </div>
            `).join('');
        } catch (e) {
            console.error('Error previewing doctors:', e);
        }
    }

    async function loadDashboardMessagesPreview() {
        try {
            const res = await fetch('/api/messages');
            const msgs = await res.json();
            state.allMessages = msgs;

            if (notifDropdownList) {
                const unread = msgs.filter(m => !m.is_read);
                if (unread.length === 0) {
                    notifDropdownList.innerHTML = '<div class="notif-empty">No unread notifications.</div>';
                } else {
                    notifDropdownList.innerHTML = unread.slice(0, 6).map(m => `
                        <div class="notif-item" onclick="window.markMessageReadAndOpen(${m.id})">
                            <div class="notif-item-title">✉️ ${escapeHtml(m.caller_name)} (${escapeHtml(m.urgency)})</div>
                            <div class="notif-item-body">"${escapeHtml(m.message)}"</div>
                        </div>
                    `).join('');
                }
            }

            if (!dashboardMessagesMini) return;

            if (msgs.length === 0) {
                dashboardMessagesMini.innerHTML = '<div class="table-loading">No visitor inquiries recorded.</div>';
                return;
            }

            dashboardMessagesMini.innerHTML = msgs.slice(0, 3).map(m => `
                <div class="mini-msg-item">
                    <div class="mini-msg-header">
                        <span class="mini-msg-caller">👤 ${escapeHtml(m.caller_name)}</span>
                        <span class="mini-msg-time">${new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div class="mini-msg-text">"${escapeHtml(m.message)}"</div>
                </div>
            `).join('');
        } catch (e) {
            console.error('Error previewing messages:', e);
        }
    }

    // =========================================================================
    // Appointments Management Section
    // =========================================================================
    async function loadAppointments() {
        try {
            const res = await fetch('/api/appointments');
            const appts = await res.json();
            state.allAppointments = appts;
            renderAppointments();
        } catch (e) {
            console.error('Error loading appointments:', e);
            if (appointmentsList) appointmentsList.innerHTML = '<tr><td colspan="9" class="table-loading">Failed to load appointments.</td></tr>';
        }
    }

    function renderAppointments() {
        if (!appointmentsList) return;

        const q = (apptSearchInput ? apptSearchInput.value : '').toLowerCase().trim();
        const filter = state.currentApptFilter;
        const todayStr = new Date().toISOString().split('T')[0];

        // Counts
        const countAll = state.allAppointments.length;
        const countToday = state.allAppointments.filter(a => a.date === todayStr && a.status !== 'Cancelled').length;
        const countUpcoming = state.allAppointments.filter(a => a.date >= todayStr && a.status === 'Confirmed').length;
        const countCompleted = state.allAppointments.filter(a => a.status === 'Completed').length;
        const countCancelled = state.allAppointments.filter(a => a.status === 'Cancelled').length;

        if (countFilterAll) countFilterAll.textContent = countAll;
        if (countFilterToday) countFilterToday.textContent = countToday;
        if (countFilterUpcoming) countFilterUpcoming.textContent = countUpcoming;
        if (countFilterCompleted) countFilterCompleted.textContent = countCompleted;
        if (countFilterCancelled) countFilterCancelled.textContent = countCancelled;

        let filtered = state.allAppointments.filter(a => {
            // Text Search
            if (q) {
                const searchCorpus = `${a.visitor_name} ${a.staff_name} ${a.department} ${a.date} ${a.purpose}`.toLowerCase();
                if (!searchCorpus.includes(q)) return false;
            }

            // Tab Filter
            if (filter === 'today') return a.date === todayStr && a.status !== 'Cancelled';
            if (filter === 'upcoming') return a.date >= todayStr && a.status === 'Confirmed';
            if (filter === 'completed') return a.status === 'Completed';
            if (filter === 'cancelled') return a.status === 'Cancelled';
            return true;
        });

        if (filtered.length === 0) {
            appointmentsList.innerHTML = '<tr><td colspan="9" class="table-loading">No matching appointments found.</td></tr>';
            return;
        }

        appointmentsList.innerHTML = filtered.map(a => {
            const isCancelled = a.status === 'Cancelled';
            const isCompleted = a.status === 'Completed';

            return `
                <tr>
                    <td><span style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--cyan);">#${a.id}</span></td>
                    <td><strong>👤 ${escapeHtml(a.visitor_name)}</strong></td>
                    <td><span style="font-family: var(--font-mono); font-size: 0.74rem;">${escapeHtml(a.contact_info)}</span></td>
                    <td>🩺 ${escapeHtml(a.staff_name)}</td>
                    <td><span style="font-size: 0.74rem; color: var(--text-muted);">${escapeHtml(a.department)}</span></td>
                    <td>📅 ${escapeHtml(a.date)} • ⏰ ${escapeHtml(a.time_slot)}</td>
                    <td><span style="font-size: 0.76rem; max-width: 140px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">"${escapeHtml(a.purpose || 'Consultation')}"</span></td>
                    <td><span class="badge-status ${a.status.toLowerCase()}">${escapeHtml(a.status)}</span></td>
                    <td>
                        <div style="display: flex; gap: 0.35rem;">
                            <button class="btn-table-action view" onclick="window.viewAppointmentDetails(${a.id})">View</button>
                            ${!isCancelled && !isCompleted ? `<button class="btn-table-action" style="border: 1px solid var(--border-medium); color: #60a5fa;" onclick="window.markAppointmentCompleted(${a.id})">Done</button>` : ''}
                            ${!isCancelled ? `<button class="btn-table-action cancel" onclick="window.cancelAppointment(${a.id})">Cancel</button>` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    if (apptFilterGroup) {
        apptFilterGroup.querySelectorAll('.filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                apptFilterGroup.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentApptFilter = btn.getAttribute('data-filter');
                renderAppointments();
            });
        });
    }

    if (apptSearchInput) {
        apptSearchInput.addEventListener('input', () => renderAppointments());
    }

    // =========================================================================
    // Doctors Directory Section
    // =========================================================================
    async function loadDoctors(searchQuery = '', specialization = '') {
        try {
            let url = '/api/doctors';
            const params = new URLSearchParams();
            if (searchQuery) params.set('q', searchQuery);
            if (specialization) params.set('specialization', specialization);
            if (params.toString()) url += '?' + params.toString();

            const res = await fetch(url);
            const doctors = await res.json();
            state.allDoctors = doctors;

            // Load specializations in filter dropdown if empty
            if (doctorSpecFilter && doctorSpecFilter.options.length <= 1) {
                const specRes = await fetch('/api/doctors/specializations/list');
                const specs = await specRes.json();
                specs.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s;
                    opt.textContent = s;
                    doctorSpecFilter.appendChild(opt);
                });
            }

            renderDoctors();
        } catch (e) {
            console.error('Error loading doctors:', e);
            if (doctorsList) doctorsList.innerHTML = '<div class="table-loading">Failed to load doctors directory.</div>';
        }
    }

    function renderDoctors() {
        if (!doctorsList) return;

        const q = (doctorSearchInput ? doctorSearchInput.value : '').toLowerCase().trim();
        const spec = doctorSpecFilter ? doctorSpecFilter.value : '';

        let filtered = state.allDoctors.filter(d => {
            if (q) {
                const corpus = `${d.name} ${d.specialization} ${d.department} ${d.bio}`.toLowerCase();
                if (!corpus.includes(q)) return false;
            }
            if (spec && d.specialization !== spec) return false;
            return true;
        });

        if (filtered.length === 0) {
            doctorsList.innerHTML = '<div class="table-loading">No specialist doctors found matching your criteria.</div>';
            return;
        }

        doctorsList.innerHTML = filtered.map(d => {
            const isAvail = d.status === 'Available';
            return `
                <div class="doctor-card">
                    <span class="doctor-status-pill ${isAvail ? 'available' : 'away'}">${escapeHtml(d.status)}</span>
                    <div class="doctor-card-top">
                        <div class="doctor-avatar-circle">${d.avatar_emoji || '🩺'}</div>
                        <div class="doctor-card-info">
                            <h4>${escapeHtml(d.name)}</h4>
                            <span class="doctor-spec-tag">${escapeHtml(d.specialization)}</span>
                            <span class="doctor-qual-tag">${escapeHtml(d.qualification)} • ${escapeHtml(d.department)}</span>
                        </div>
                    </div>
                    <div class="doctor-details-grid">
                        <div class="detail-item">
                            <span class="detail-item-label">Experience</span>
                            <span class="detail-item-val">${d.experience_years} Years</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item-label">Consultation Fee</span>
                            <span class="detail-item-val" style="color: var(--cyan);">${escapeHtml(d.consultation_fee || '₹500')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item-label">Rating</span>
                            <span class="detail-item-val">⭐ ${d.rating || 4.8} / 5</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item-label">Working Days</span>
                            <span class="detail-item-val">${escapeHtml(d.available_days || 'Mon-Fri')}</span>
                        </div>
                    </div>
                    <div class="doctor-slots-text">
                        <strong>Available Slots:</strong> ${escapeHtml(d.available_slots || '09:00 AM - 05:00 PM')}
                    </div>
                    <div class="doctor-card-actions">
                        <button class="btn-book-doctor-full" onclick="window.openDoctorBookingModal(${d.id})">
                            📅 Book Consultation
                        </button>
                        <button class="btn-delete-doc" title="Remove Doctor" onclick="window.removeDoctor(${d.id})">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    if (doctorSearchInput) doctorSearchInput.addEventListener('input', () => renderDoctors());
    if (doctorSpecFilter) doctorSpecFilter.addEventListener('change', () => renderDoctors());

    // =========================================================================
    // Patients Directory Section
    // =========================================================================
    async function loadPatients() {
        try {
            const res = await fetch('/api/patients');
            const patients = await res.json();
            state.allPatients = patients;
            renderPatients();
        } catch (e) {
            console.error('Error loading patients:', e);
            if (patientsList) patientsList.innerHTML = '<tr><td colspan="8" class="table-loading">Failed to load patient records.</td></tr>';
        }
    }

    function renderPatients() {
        if (!patientsList) return;

        const q = (patientSearchInput ? patientSearchInput.value : '').toLowerCase().trim();
        let filtered = state.allPatients.filter(p => {
            if (q) {
                const corpus = `${p.name} ${p.contact_info} ${p.last_doctor} ${p.last_department}`.toLowerCase();
                if (!corpus.includes(q)) return false;
            }
            return true;
        });

        if (filtered.length === 0) {
            patientsList.innerHTML = '<tr><td colspan="8" class="table-loading">No matching patient records found.</td></tr>';
            return;
        }

        patientsList.innerHTML = filtered.map(p => `
            <tr>
                <td><strong>👤 ${escapeHtml(p.name)}</strong></td>
                <td><span style="font-family: var(--font-mono); font-size: 0.74rem;">${escapeHtml(p.contact_info)}</span></td>
                <td><span class="nav-badge cyan">${p.total_appointments} Consultation${p.total_appointments > 1 ? 's' : ''}</span></td>
                <td>📅 ${escapeHtml(p.last_visit_date || 'N/A')}</td>
                <td>🩺 ${escapeHtml(p.last_doctor || 'Clinic Specialist')}</td>
                <td><span style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(p.last_department || 'General')}</span></td>
                <td><span class="badge-status ${(p.last_status || 'confirmed').toLowerCase()}">${escapeHtml(p.last_status || 'Confirmed')}</span></td>
                <td>
                    <button class="btn-table-action view" onclick="window.scheduleVisitForPatient('${escapeHtml(p.name)}', '${escapeHtml(p.contact_info)}')">Schedule Visit</button>
                </td>
            </tr>
        `).join('');
    }

    if (patientSearchInput) patientSearchInput.addEventListener('input', () => renderPatients());

    // =========================================================================
    // Caller Messages Section
    // =========================================================================
    async function loadMessages() {
        try {
            const res = await fetch('/api/messages');
            const msgs = await res.json();
            state.allMessages = msgs;
            renderMessages();
        } catch (e) {
            console.error('Error loading messages:', e);
            if (messagesList) messagesList.innerHTML = '<div class="table-loading">Failed to load caller messages.</div>';
        }
    }

    function renderMessages() {
        if (!messagesList) return;

        const filter = state.currentMsgFilter;
        const countAll = state.allMessages.length;
        const countUnread = state.allMessages.filter(m => !m.is_read).length;
        const countUrgent = state.allMessages.filter(m => m.urgency === 'Urgent').length;

        if (msgFilterAllCount) msgFilterAllCount.textContent = countAll;
        if (msgFilterUnreadCount) msgFilterUnreadCount.textContent = countUnread;
        if (msgFilterUrgentCount) msgFilterUrgentCount.textContent = countUrgent;

        let filtered = state.allMessages.filter(m => {
            if (filter === 'unread') return !m.is_read;
            if (filter === 'urgent') return m.urgency === 'Urgent';
            return true;
        });

        if (filtered.length === 0) {
            messagesList.innerHTML = '<div class="table-loading">No caller messages found in this category.</div>';
            return;
        }

        messagesList.innerHTML = filtered.map(m => `
            <div class="message-card ${!m.is_read ? 'unread' : ''} ${m.urgency === 'Urgent' ? 'urgent' : ''}">
                <div class="message-card-header">
                    <div>
                        <div class="msg-caller-name">👤 ${escapeHtml(m.caller_name)}</div>
                        <div class="msg-caller-phone">📞 ${escapeHtml(m.contact_info)}</div>
                    </div>
                    <span class="badge-status ${m.urgency === 'Urgent' ? 'cancelled' : 'confirmed'}">${escapeHtml(m.urgency)}</span>
                </div>
                <div class="msg-for-tag">Recipient: <strong>${escapeHtml(m.recipient_name)}</strong></div>
                <div class="msg-body-content">"${escapeHtml(m.message)}"</div>
                <div class="message-card-footer">
                    <span>${new Date(m.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                    <div class="msg-actions-group">
                        ${!m.is_read ? `<button class="btn-table-action view" onclick="window.markMessageRead(${m.id})">Mark Read</button>` : ''}
                        <button class="btn-table-action cancel" onclick="window.deleteMessage(${m.id})">Delete</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    if (msgFilterGroup) {
        msgFilterGroup.querySelectorAll('.filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                msgFilterGroup.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentMsgFilter = btn.getAttribute('data-msg-filter');
                renderMessages();
            });
        });
    }

    // =========================================================================
    // Corporate Staff Directory & FAQs
    // =========================================================================
    async function loadDirectory(searchQuery = '') {
        try {
            const url = searchQuery ? `/api/directory?q=${encodeURIComponent(searchQuery)}` : '/api/directory';
            const res = await fetch(url);
            const staff = await res.json();

            if (!directoryList) return;
            if (staff.length === 0) {
                directoryList.innerHTML = '<div class="table-loading">No staff found matching query.</div>';
                return;
            }

            directoryList.innerHTML = staff.map(s => `
                <div class="staff-card">
                    <div class="staff-card-header">
                        <h4>👤 ${escapeHtml(s.name)}</h4>
                        <span class="badge-status confirmed">${escapeHtml(s.status)}</span>
                    </div>
                    <p style="font-size: 0.78rem; color: var(--cyan); margin-bottom: 0.35rem;">${escapeHtml(s.title)} • ${escapeHtml(s.department)}</p>
                    <p style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.65rem;">${escapeHtml(s.bio || 'Corporate team member')}</p>
                    <div style="font-size: 0.74rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
                        <span>Ext: <strong>${escapeHtml(s.phone_extension)}</strong></span>
                        <span style="font-family: var(--font-mono);">${escapeHtml(s.email)}</span>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error('Error loading directory:', e);
        }
    }

    if (directorySearchInput) {
        directorySearchInput.addEventListener('input', () => loadDirectory(directorySearchInput.value));
    }

    async function loadCompanyDetails() {
        try {
            const res = await fetch('/api/company');
            const data = await res.json();
            state.companyInfo = data;

            if (faqList && data.knowledge_base) {
                faqList.innerHTML = data.knowledge_base.map(kb => `
                    <div class="faq-card">
                        <h4 style="font-size: 0.92rem; color: #fff; margin-bottom: 0.3rem;">🏢 ${escapeHtml(kb.title)}</h4>
                        <span class="nav-badge cyan" style="margin-bottom: 0.65rem; display: inline-block;">${escapeHtml(kb.category)}</span>
                        <p style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;">${escapeHtml(kb.content)}</p>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading company details:', e);
        }
    }

    async function loadCallLogs() {
        try {
            const res = await fetch('/api/call-logs');
            const logs = await res.json();

            if (!logsList) return;
            if (logs.length === 0) {
                logsList.innerHTML = '<div class="table-loading">No voice calls recorded yet.</div>';
                return;
            }

            logsList.innerHTML = logs.map(l => `
                <div class="log-card">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.45rem;">
                        <span style="font-weight: 700; color: #fff;">📞 ${escapeHtml(l.caller_identifier || 'Web Caller')}</span>
                        <span style="font-size: 0.72rem; color: var(--cyan);">${l.duration_seconds || 0}s duration</span>
                    </div>
                    <p style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4;">${escapeHtml(l.summary || 'Clinical inquiry interaction.')}</p>
                </div>
            `).join('');
        } catch (e) {
            console.error('Error loading logs:', e);
        }
    }

    // =========================================================================
    // Modal Actions: Booking, Adding Doctor, Details
    // =========================================================================
    window.openDoctorBookingModal = function(doctorId) {
        const doc = state.allDoctors.find(d => d.id === doctorId);
        if (!doc) return;

        state.selectedBookingDoctor = doc;
        if (bookingDoctorInfo) {
            bookingDoctorInfo.innerHTML = `
                <strong>${doc.avatar_emoji || '🩺'} ${escapeHtml(doc.name)}</strong> — ${escapeHtml(doc.specialization)} (${escapeHtml(doc.department)})<br>
                <span style="color: var(--cyan);">Fee: ${escapeHtml(doc.consultation_fee || '₹500')}</span> • Experience: ${doc.experience_years} yrs • Rating: ⭐ ${doc.rating}/5
            `;
        }

        // Populate slots
        if (bookApptSlot) {
            bookApptSlot.innerHTML = '';
            const rawSlots = doc.available_slots || "09:00 AM, 10:00 AM, 11:30 AM, 02:00 PM, 03:30 PM";
            const slots = rawSlots.split(',').map(s => s.trim()).filter(Boolean);
            slots.forEach(slot => {
                const opt = document.createElement('option');
                opt.value = slot;
                opt.textContent = slot;
                bookApptSlot.appendChild(opt);
            });
        }

        // Prefill authenticated user info if available
        if (state.currentUser) {
            if (bookPatientName && !bookPatientName.value) {
                bookPatientName.value = state.currentUser.name || '';
            }
            if (bookPatientContact && !bookPatientContact.value) {
                bookPatientContact.value = state.currentUser.phone_number || state.currentUser.email || '';
            }
        }

        bookDoctorModal.classList.add('show');
    };

    window.scheduleVisitForPatient = function(name, contact) {
        if (bookPatientName) bookPatientName.value = name;
        if (bookPatientContact) bookPatientContact.value = contact;
        if (state.allDoctors.length > 0) {
            window.openDoctorBookingModal(state.allDoctors[0].id);
        } else {
            showToast('Loading doctors...', 'info');
            loadDoctors().then(() => {
                if (state.allDoctors.length > 0) window.openDoctorBookingModal(state.allDoctors[0].id);
            });
        }
    };

    if (closeBookDoctorBtn) closeBookDoctorBtn.addEventListener('click', () => bookDoctorModal.classList.remove('show'));
    if (cancelBookDoctorBtn) cancelBookDoctorBtn.addEventListener('click', () => bookDoctorModal.classList.remove('show'));

    if (confirmBookDoctorBtn) {
        confirmBookDoctorBtn.addEventListener('click', async () => {
            const name = (bookPatientName ? bookPatientName.value : '').trim();
            const contact = (bookPatientContact ? bookPatientContact.value : '').trim();
            const dateVal = (bookApptDate ? bookApptDate.value : '').trim();
            const slotVal = (bookApptSlot ? bookApptSlot.value : '').trim();
            const purposeVal = (bookApptPurpose ? bookApptPurpose.value : '').trim() || 'General Consultation';

            if (!name) {
                showToast('Please enter patient name', 'error');
                return;
            }
            if (!contact) {
                showToast('Please enter contact info', 'error');
                return;
            }
            if (!dateVal || !slotVal) {
                showToast('Please select date and slot', 'error');
                return;
            }

            const docName = state.selectedBookingDoctor ? state.selectedBookingDoctor.name : 'Dr. Arun Prakash Sharma';

            try {
                confirmBookDoctorBtn.disabled = true;
                confirmBookDoctorBtn.textContent = 'Saving Booking...';

                const reqHeaders = { 'Content-Type': 'application/json' };
                if (state.authToken) {
                    reqHeaders['Authorization'] = `Bearer ${state.authToken}`;
                }

                const res = await fetch('/api/appointments', {
                    method: 'POST',
                    headers: reqHeaders,
                    body: JSON.stringify({
                        visitor_name: name,
                        contact_info: contact,
                        staff_or_department: docName,
                        date: dateVal,
                        time_slot: slotVal,
                        purpose: purposeVal
                    })
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.detail || data.message || 'Booking conflict');
                }

                showToast(`Appointment successfully booked! Booking #${data.booking_id || data.id}`, 'success');
                bookDoctorModal.classList.remove('show');

                // Clear fields
                if (bookPatientName) bookPatientName.value = '';
                if (bookPatientContact) bookPatientContact.value = '';

                // Reload data
                loadDashboardStats();
                loadAppointments();
                loadPatients();

            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                confirmBookDoctorBtn.disabled = false;
                confirmBookDoctorBtn.textContent = '📅 Confirm Appointment';
            }
        });
    }

    // Admin Add New Doctor Modal
    if (adminAddDoctorBtn) adminAddDoctorBtn.addEventListener('click', () => addDoctorModal.classList.add('show'));
    if (quickNewDocBtn) quickNewDocBtn.addEventListener('click', () => addDoctorModal.classList.add('show'));
    if (closeAddDoctorBtn) closeAddDoctorBtn.addEventListener('click', () => addDoctorModal.classList.remove('show'));
    if (cancelAddDoctorBtn) cancelAddDoctorBtn.addEventListener('click', () => addDoctorModal.classList.remove('show'));

    if (confirmAddDoctorBtn) {
        confirmAddDoctorBtn.addEventListener('click', async () => {
            const name = (newDocName ? newDocName.value : '').trim();
            const spec = (newDocSpec ? newDocSpec.value : '').trim();
            const dept = (newDocDept ? newDocDept.value : '').trim();
            const qual = (newDocQual ? newDocQual.value : '').trim();

            if (!name || !spec || !dept || !qual) {
                showToast('Please fill in required fields (Name, Specialization, Dept, Qualification)', 'error');
                return;
            }

            try {
                confirmAddDoctorBtn.disabled = true;
                const payload = {
                    name,
                    specialization: spec,
                    department: dept,
                    qualification: qual,
                    experience_years: parseInt(newDocExp.value) || 5,
                    consultation_fee: newDocFee.value || '₹800',
                    available_days: newDocDays.value || 'Mon, Wed, Fri',
                    available_slots: newDocSlots.value || '09:00 AM, 11:00 AM, 02:00 PM',
                    email: newDocEmail.value || 'doctor@hrenterprises.com',
                    phone_extension: newDocExt.value || '201',
                    bio: newDocBio.value || '',
                    avatar_emoji: '🩺'
                };

                const res = await fetch('/api/doctors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Failed to register doctor');

                showToast(`Doctor ${name} registered successfully!`, 'success');
                addDoctorModal.classList.remove('show');

                newDocName.value = '';
                newDocSpec.value = '';
                newDocDept.value = '';
                newDocQual.value = '';

                loadDashboardStats();
                loadDoctors();
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                confirmAddDoctorBtn.disabled = false;
            }
        });
    }

    // Appointment Details Modal
    window.viewAppointmentDetails = function(apptId) {
        const appt = state.allAppointments.find(a => a.id === apptId);
        if (!appt || !apptDetailsContent) return;

        apptDetailsContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                <div style="background: rgba(0, 240, 255, 0.06); border: 1px solid var(--border-cyan); border-radius: var(--radius-sm); padding: 0.85rem;">
                    <div style="font-size: 0.72rem; color: var(--cyan); text-transform: uppercase; font-weight: 700;">Booking Reference</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #fff; font-family: var(--font-mono);">#${appt.id}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.82rem;">
                    <div><span style="color: var(--text-muted);">Patient Name:</span><br><strong>👤 ${escapeHtml(appt.visitor_name)}</strong></div>
                    <div><span style="color: var(--text-muted);">Contact Phone:</span><br><strong>📞 ${escapeHtml(appt.contact_info)}</strong></div>
                    <div><span style="color: var(--text-muted);">Consulting Doctor:</span><br><strong>🩺 ${escapeHtml(appt.staff_name)}</strong></div>
                    <div><span style="color: var(--text-muted);">Department:</span><br><strong>🏥 ${escapeHtml(appt.department)}</strong></div>
                    <div><span style="color: var(--text-muted);">Appointment Date:</span><br><strong>📅 ${escapeHtml(appt.date)}</strong></div>
                    <div><span style="color: var(--text-muted);">Time Slot:</span><br><strong>⏰ ${escapeHtml(appt.time_slot)}</strong></div>
                </div>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.75rem;">
                    <span style="color: var(--text-muted); font-size: 0.74rem;">Clinical Purpose / Symptoms:</span>
                    <p style="font-size: 0.82rem; color: #fff; margin-top: 0.2rem;">"${escapeHtml(appt.purpose || 'General Consultation')}"</p>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem;">
                    <span style="color: var(--text-muted);">Status:</span>
                    <span class="badge-status ${appt.status.toLowerCase()}">${escapeHtml(appt.status)}</span>
                </div>
            </div>
        `;
        apptDetailsModal.classList.add('show');
    };

    if (closeApptDetailsBtn) closeApptDetailsBtn.addEventListener('click', () => apptDetailsModal.classList.remove('show'));
    if (dismissApptDetailsBtn) dismissApptDetailsBtn.addEventListener('click', () => apptDetailsModal.classList.remove('show'));

    // Global Cancel & Complete Appointment Functions
    window.cancelAppointment = async function(id) {
        if (!confirm(`Are you sure you want to cancel appointment #${id}?`)) return;
        try {
            const res = await fetch(`/api/appointments/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Cancellation failed');
            showToast(`Appointment #${id} marked as cancelled`, 'info');
            loadDashboardStats();
            loadAppointments();
            loadPatients();
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    window.markAppointmentCompleted = async function(id) {
        try {
            const res = await fetch(`/api/appointments/${id}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'Completed' })
            });
            if (!res.ok) throw new Error('Update failed');
            showToast(`Appointment #${id} marked as Completed`, 'success');
            loadDashboardStats();
            loadAppointments();
            loadPatients();
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    window.removeDoctor = async function(id) {
        if (!confirm(`Are you sure you want to delete doctor #${id} from the clinic directory?`)) return;
        try {
            const res = await fetch(`/api/doctors/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete doctor');
            showToast(`Doctor #${id} removed successfully`, 'info');
            loadDashboardStats();
            loadDoctors();
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    window.markMessageRead = async function(id) {
        try {
            await fetch(`/api/messages/${id}/read`, { method: 'PATCH' });
            loadDashboardStats();
            loadMessages();
        } catch (e) { }
    };

    window.markMessageReadAndOpen = async function(id) {
        await window.markMessageRead(id);
        notificationsDropdown.classList.remove('show');
        switchView('messagesView');
    };

    window.deleteMessage = async function(id) {
        if (!confirm('Delete this message?')) return;
        try {
            await fetch(`/api/messages/${id}`, { method: 'DELETE' });
            showToast('Message deleted', 'info');
            loadDashboardStats();
            loadMessages();
        } catch (e) { }
    };

    // Quick New Appointment Trigger
    if (openBookApptModalBtn) openBookApptModalBtn.addEventListener('click', () => {
        if (state.allDoctors.length > 0) window.openDoctorBookingModal(state.allDoctors[0].id);
        else window.openDoctorBookingModal(1);
    });
    if (quickNewApptBtn) quickNewApptBtn.addEventListener('click', () => {
        if (state.allDoctors.length > 0) window.openDoctorBookingModal(state.allDoctors[0].id);
        else window.openDoctorBookingModal(1);
    });
    if (patientNewApptBtn) patientNewApptBtn.addEventListener('click', () => {
        if (state.allDoctors.length > 0) window.openDoctorBookingModal(state.allDoctors[0].id);
        else window.openDoctorBookingModal(1);
    });

    // Refresh Buttons
    if (refreshDashboardBtn) refreshDashboardBtn.addEventListener('click', () => {
        loadDashboardStats();
        showToast('Dashboard metrics refreshed', 'info');
    });
    if (refreshApptsBtn) refreshApptsBtn.addEventListener('click', () => {
        loadAppointments();
        showToast('Appointments synced', 'info');
    });
    if (refreshDoctorsBtn) refreshDoctorsBtn.addEventListener('click', () => {
        loadDoctors();
        showToast('Doctors directory synced', 'info');
    });
    if (refreshPatientsBtn) refreshPatientsBtn.addEventListener('click', () => {
        loadPatients();
        showToast('Patients synced', 'info');
    });
    if (refreshMsgsBtn) refreshMsgsBtn.addEventListener('click', () => {
        loadMessages();
        showToast('Messages synced', 'info');
    });
    if (refreshDirectoryBtn) refreshDirectoryBtn.addEventListener('click', () => {
        loadDirectory();
        showToast('Directory synced', 'info');
    });
    if (refreshLogsBtn) refreshLogsBtn.addEventListener('click', () => {
        loadCallLogs();
        showToast('Call logs refreshed', 'info');
    });

    // Notifications Dropdown Toggle
    if (notificationsBtn && notificationsDropdown) {
        notificationsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationsDropdown.classList.toggle('show');
        });
        document.addEventListener('click', (e) => {
            if (!notificationsDropdown.contains(e.target) && e.target !== notificationsBtn) {
                notificationsDropdown.classList.remove('show');
            }
        });
    }

    // Global Search Bar Handler
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const q = globalSearchInput.value.trim();
                if (!q) return;

                // Route search based on context or switch to appointments view with search
                switchView('appointmentsView');
                if (apptSearchInput) {
                    apptSearchInput.value = q;
                    renderAppointments();
                }
            }
        });
    }

    // Settings Modal Handlers
    function openSettings() {
        if (apiKeyInput) apiKeyInput.value = state.apiKey;
        if (voiceSelect) voiceSelect.value = state.voice;
        if (customWsUrlInput) customWsUrlInput.value = state.customWsUrl;
        settingsModal.classList.add('show');
    }
    if (openSettingsBtn) openSettingsBtn.addEventListener('click', openSettings);
    if (headerSettingsBtn) headerSettingsBtn.addEventListener('click', openSettings);
    if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('show'));
    if (cancelSettingsBtn) cancelSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('show'));

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', async () => {
            const key = apiKeyInput.value.trim();
            const voice = voiceSelect.value;
            const customWs = customWsUrlInput.value.trim();

            state.apiKey = key;
            state.voice = voice;
            state.customWsUrl = customWs;

            localStorage.setItem('gemini_api_key', key);
            localStorage.setItem('receptionist_voice', voice);
            localStorage.setItem('custom_ws_url', customWs);

            if (key) {
                try {
                    await fetch('/api/config/key', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ api_key: key })
                    });
                } catch (e) { }
            }

            settingsModal.classList.remove('show');
            showToast('Settings saved successfully', 'success');
        });
    }

    // =========================================================================
    // Utility Helpers
    // =========================================================================
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message, type = 'info') {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = type === 'error' ? '⚠️' : (type === 'success' ? '✅' : 'ℹ️');
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // =========================================================================
    // 7. Authentication & OTP Verification Controller
    // =========================================================================
    function showAuthAlert(msg, type = 'error') {
        if (!authAlert) return;
        authAlert.className = `auth-alert ${type}`;
        authAlert.innerHTML = `<span>${type === 'error' ? '⚠️' : (type === 'success' ? '✅' : 'ℹ️')}</span> <span>${escapeHtml(msg)}</span>`;
        authAlert.style.display = 'flex';
    }

    function hideAuthAlert() {
        if (authAlert) {
            authAlert.style.display = 'none';
            authAlert.innerHTML = '';
        }
    }

    function switchAuthTab(channel) {
        state.authChannel = channel;
        hideAuthAlert();
        if (channel === 'email') {
            if (authTabEmail) authTabEmail.classList.add('active');
            if (authTabPhone) authTabPhone.classList.remove('active');
            if (authEmailGroup) authEmailGroup.style.display = 'block';
            if (authPhoneGroup) authPhoneGroup.style.display = 'none';
            if (authEmailInput) authEmailInput.focus();
        } else {
            if (authTabPhone) authTabPhone.classList.add('active');
            if (authTabEmail) authTabEmail.classList.remove('active');
            if (authEmailGroup) authEmailGroup.style.display = 'none';
            if (authPhoneGroup) authPhoneGroup.style.display = 'block';
            if (authPhoneInput) authPhoneInput.focus();
        }
    }

    if (authTabEmail) authTabEmail.addEventListener('click', () => switchAuthTab('email'));
    if (authTabPhone) authTabPhone.addEventListener('click', () => switchAuthTab('phone'));

    function updateUserUI() {
        if (state.currentUser) {
            const displayName = state.currentUser.name || (state.currentUser.email ? state.currentUser.email.split('@')[0] : (state.currentUser.phone_number || 'User'));
            const displayIdentifier = state.currentUser.email || state.currentUser.phone_number || 'Verified Account';

            if (sidebarUserName) sidebarUserName.textContent = displayName;
            if (sidebarUserRole) sidebarUserRole.textContent = displayIdentifier;
            if (sidebarUserAvatar) sidebarUserAvatar.textContent = '👨‍⚕️';
            if (sidebarAuthActionBtn) {
                sidebarAuthActionBtn.title = 'Account Details / Sign Out';
                sidebarAuthActionBtn.textContent = '👤';
            }

            if (topbarUserName) topbarUserName.textContent = displayName;
            if (topbarUserStatus) topbarUserStatus.textContent = 'Active';
            if (topbarUserAvatar) topbarUserAvatar.textContent = '👨‍⚕️';
        } else {
            if (sidebarUserName) sidebarUserName.textContent = 'Guest Portal';
            if (sidebarUserRole) sidebarUserRole.textContent = 'Click to Sign In / Register';
            if (sidebarUserAvatar) sidebarUserAvatar.textContent = '🔒';
            if (sidebarAuthActionBtn) {
                sidebarAuthActionBtn.title = 'Sign In / Register';
                sidebarAuthActionBtn.textContent = '🔐';
            }

            if (topbarUserName) topbarUserName.textContent = 'Sign In';
            if (topbarUserStatus) topbarUserStatus.textContent = 'Guest';
            if (topbarUserAvatar) topbarUserAvatar.textContent = '👤';
        }
    }

    function openAuthModal() {
        hideAuthAlert();
        if (state.currentUser) {
            // Show Profile Panel
            if (authStepRequest) authStepRequest.style.display = 'none';
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepProfile) authStepProfile.style.display = 'block';

            const displayName = state.currentUser.name || 'Healthcare User';
            const displayId = state.currentUser.email || state.currentUser.phone_number || '';
            if (profileLargeName) profileLargeName.textContent = displayName;
            if (profileLargeIdentifier) profileLargeIdentifier.textContent = displayId;
            if (profileMetaAuthType) profileMetaAuthType.textContent = state.currentUser.email ? 'Email OTP Verified' : 'Phone OTP Verified';
            if (profileMetaCreatedAt) {
                const dt = state.currentUser.created_at ? new Date(state.currentUser.created_at) : new Date();
                profileMetaCreatedAt.textContent = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            }
            if (profileMetaLastLogin) {
                const dt = state.currentUser.last_login ? new Date(state.currentUser.last_login) : new Date();
                profileMetaLastLogin.textContent = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            }
        } else {
            // Show Request OTP Panel
            if (authStepRequest) authStepRequest.style.display = 'block';
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepProfile) authStepProfile.style.display = 'none';

            // Clear inputs
            if (authNameInput) authNameInput.value = '';
            if (authEmailInput) authEmailInput.value = '';
            if (authPhoneInput) authPhoneInput.value = '';
        }
        if (authModal) authModal.classList.add('show');
    }

    function closeAuthModal() {
        if (state.otpTimerInterval) {
            clearInterval(state.otpTimerInterval);
            state.otpTimerInterval = null;
        }
        if (authModal) authModal.classList.remove('show');
    }

    if (topbarUserPill) topbarUserPill.addEventListener('click', openAuthModal);
    if (sidebarAuthActionBtn) sidebarAuthActionBtn.addEventListener('click', openAuthModal);
    if (closeAuthModalBtn) closeAuthModalBtn.addEventListener('click', closeAuthModal);

    // Stop timer on modal click outside
    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target === authModal) closeAuthModal();
        });
    }

    function startOtpCountdown(totalSeconds = 30) {
        if (state.otpTimerInterval) {
            clearInterval(state.otpTimerInterval);
            state.otpTimerInterval = null;
        }

        state.otpSecondsLeft = totalSeconds;
        if (authResendBtn) authResendBtn.disabled = true;

        if (otpCountdownText) {
            otpCountdownText.textContent = `${state.otpSecondsLeft}s`;
            otpCountdownText.classList.remove('urgent');
        }
        if (otpTimerBar) {
            otpTimerBar.style.width = '100%';
            otpTimerBar.classList.remove('urgent');
        }

        state.otpTimerInterval = setInterval(() => {
            state.otpSecondsLeft--;

            if (state.otpSecondsLeft <= 0) {
                clearInterval(state.otpTimerInterval);
                state.otpTimerInterval = null;

                if (otpCountdownText) {
                    otpCountdownText.textContent = 'Expired';
                    otpCountdownText.classList.add('urgent');
                }
                if (otpTimerBar) {
                    otpTimerBar.style.width = '0%';
                    otpTimerBar.classList.add('urgent');
                }
                if (authResendBtn) {
                    authResendBtn.disabled = false;
                }
                showAuthAlert('The verification code has expired after 30 seconds. Please click "Resend Code" to receive a fresh code.', 'error');
            } else {
                if (otpCountdownText) {
                    otpCountdownText.textContent = `${state.otpSecondsLeft}s`;
                }
                const pct = Math.max(0, (state.otpSecondsLeft / totalSeconds) * 100);
                if (otpTimerBar) {
                    otpTimerBar.style.width = `${pct}%`;
                }

                if (state.otpSecondsLeft <= 10) {
                    if (otpCountdownText) otpCountdownText.classList.add('urgent');
                    if (otpTimerBar) otpTimerBar.classList.add('urgent');
                }
            }
        }, 1000);
    }

    async function handleSendOtp(isResend = false) {
        hideAuthAlert();

        let identifier = '';
        if (state.authChannel === 'email') {
            identifier = (authEmailInput ? authEmailInput.value : '').trim();
            if (!identifier || !identifier.includes('@') || !identifier.includes('.')) {
                showAuthAlert('Please enter a valid email address (e.g. user@example.com)', 'error');
                if (authEmailInput) authEmailInput.focus();
                return;
            }
        } else {
            identifier = (authPhoneInput ? authPhoneInput.value : '').trim();
            const cleanDigits = identifier.replace(/[\s\-\(\)\+]/g, '');
            if (!identifier || cleanDigits.length < 7) {
                showAuthAlert('Please enter a valid phone number (e.g. +91 9876543210)', 'error');
                if (authPhoneInput) authPhoneInput.focus();
                return;
            }
        }

        try {
            if (sendOtpBtn) {
                sendOtpBtn.disabled = true;
                sendOtpBtn.innerHTML = '<span class="btn-text">Sending OTP...</span>';
            }
            if (authResendBtn) {
                authResendBtn.disabled = true;
            }

            let res, data;
            try {
                res = await fetch('/api/auth/send-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        identifier: identifier,
                        channel: state.authChannel
                    })
                });
            } catch (networkErr) {
                throw new Error('Cannot reach the server. Please check your connection.');
            }

            // Parse JSON response
            try {
                data = await res.json();
            } catch (parseErr) {
                throw new Error(`Server error (HTTP ${res.status}). Please try again.`);
            }

            // Handle specific HTTP errors with meaningful messages
            if (!res.ok) {
                if (res.status === 404) {
                    throw new Error('Authentication service not found. Please refresh the page and try again.');
                } else if (res.status === 422) {
                    const detail = data.detail;
                    if (Array.isArray(detail)) {
                        throw new Error(detail.map(d => d.msg || d.message).join('. '));
                    }
                    throw new Error(typeof detail === 'string' ? detail : 'Invalid input. Please check your email or phone number.');
                } else if (res.status === 429) {
                    throw new Error('Too many OTP requests. Please wait a moment before trying again.');
                } else if (res.status === 500) {
                    throw new Error('A server error occurred. Please try again in a moment.');
                } else {
                    throw new Error(data.detail || data.message || `Request failed (HTTP ${res.status}).`);
                }
            }

            state.authIdentifier = identifier;

            // Update Step 2 UI
            if (authTargetDisplay) authTargetDisplay.textContent = identifier;
            if (authStepRequest) authStepRequest.style.display = 'none';
            if (authStepVerify) authStepVerify.style.display = 'block';

            // Clear OTP inputs
            otpDigitBoxes.forEach(box => {
                box.value = '';
                box.classList.remove('filled');
            });

            // Focus first digit box
            if (otpDigitBoxes[0]) {
                setTimeout(() => otpDigitBoxes[0].focus(), 100);
            }

            // Start 30-Second Countdown
            startOtpCountdown(data.expires_in || 30);

            showToast(`Verification code sent via ${state.authChannel}`, 'success');
        } catch (err) {
            showAuthAlert(err.message, 'error');
        } finally {
            if (sendOtpBtn) {
                sendOtpBtn.disabled = false;
                sendOtpBtn.innerHTML = '<span class="btn-text">Continue & Send OTP</span> <span class="btn-arrow">→</span>';
            }
        }
    }

    if (sendOtpBtn) sendOtpBtn.addEventListener('click', () => handleSendOtp(false));
    if (authResendBtn) authResendBtn.addEventListener('click', () => handleSendOtp(true));

    if (authBackToRequestBtn) {
        authBackToRequestBtn.addEventListener('click', () => {
            if (state.otpTimerInterval) {
                clearInterval(state.otpTimerInterval);
                state.otpTimerInterval = null;
            }
            hideAuthAlert();
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepRequest) authStepRequest.style.display = 'block';
        });
    }

    // 6-digit OTP Inputs behavior
    otpDigitBoxes.forEach((box, idx) => {
        // Input event (digit typed)
        box.addEventListener('input', (e) => {
            const val = box.value.replace(/[^0-9]/g, '');
            box.value = val ? val[0] : '';

            if (box.value) {
                box.classList.add('filled');
                // Move to next input box
                if (idx < otpDigitBoxes.length - 1) {
                    otpDigitBoxes[idx + 1].focus();
                } else {
                    // Check if all 6 filled -> Auto verify
                    const fullOtp = Array.from(otpDigitBoxes).map(b => b.value).join('');
                    if (fullOtp.length === 6) {
                        handleVerifyOtp();
                    }
                }
            } else {
                box.classList.remove('filled');
            }
        });

        // Keydown (Backspace navigation)
        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !box.value && idx > 0) {
                otpDigitBoxes[idx - 1].focus();
            }
        });

        // Paste support (pasting full 6 digits)
        box.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim();
            const digits = pasteData.replace(/[^0-9]/g, '');

            if (digits.length >= 6) {
                for (let i = 0; i < 6; i++) {
                    otpDigitBoxes[i].value = digits[i];
                    otpDigitBoxes[i].classList.add('filled');
                }
                otpDigitBoxes[5].focus();
                handleVerifyOtp();
            } else {
                showAuthAlert('Pasted code must be at least 6 digits', 'error');
            }
        });
    });

    async function handleVerifyOtp() {
        hideAuthAlert();

        const fullOtp = Array.from(otpDigitBoxes).map(b => b.value.trim()).join('');
        if (fullOtp.length !== 6 || !/^\d{6}$/.test(fullOtp)) {
            showAuthAlert('Please enter all 6 numeric digits of the verification code.', 'error');
            return;
        }

        try {
            if (verifyOtpBtn) {
                verifyOtpBtn.disabled = true;
                verifyOtpBtn.innerHTML = '<span class="btn-text">Verifying...</span>';
            }

            const userName = (authNameInput ? authNameInput.value.trim() : '') || null;

            let res, data;
            try {
                res = await fetch('/api/auth/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        identifier: state.authIdentifier,
                        otp: fullOtp,
                        name: userName
                    })
                });
            } catch (networkErr) {
                throw new Error('Cannot reach the server. Please check your connection.');
            }

            try {
                data = await res.json();
            } catch (parseErr) {
                throw new Error(`Server error (HTTP ${res.status}). Please try again.`);
            }

            if (!res.ok) {
                if (res.status === 404) {
                    throw new Error('Verification service not found. Please refresh the page.');
                } else if (res.status === 422) {
                    const detail = data.detail;
                    if (Array.isArray(detail)) {
                        throw new Error(detail.map(d => d.msg || d.message).join('. '));
                    }
                    throw new Error(typeof detail === 'string' ? detail : 'Invalid verification code format.');
                } else if (res.status === 500) {
                    throw new Error('A server error occurred during verification. Please try again.');
                } else {
                    throw new Error(data.detail || data.message || 'Verification failed. Please check your code.');
                }
            }

            // Stop timer
            if (state.otpTimerInterval) {
                clearInterval(state.otpTimerInterval);
                state.otpTimerInterval = null;
            }

            // Save token and user state
            state.authToken = data.token;
            localStorage.setItem('jack_auth_token', data.token);
            state.currentUser = data.user;

            updateUserUI();
            showToast(`Welcome ${state.currentUser.name || 'User'}! Authentication successful.`, 'success');

            // Close modal after brief success feedback
            setTimeout(() => {
                closeAuthModal();
            }, 600);
        } catch (err) {
            showAuthAlert(err.message, 'error');
            // Only clear inputs on wrong code, not on network errors
            if (!err.message.includes('server') && !err.message.includes('reach')) {
                otpDigitBoxes.forEach(b => {
                    b.value = '';
                    b.classList.remove('filled');
                });
                if (otpDigitBoxes[0]) otpDigitBoxes[0].focus();
            }
        } finally {
            if (verifyOtpBtn) {
                verifyOtpBtn.disabled = false;
                verifyOtpBtn.innerHTML = '<span class="btn-text">Verify & Sign In</span> <span class="btn-arrow">✓</span>';
            }
        }
    }

    if (verifyOtpBtn) verifyOtpBtn.addEventListener('click', handleVerifyOtp);

    async function handleLogout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
        } catch (e) { }

        if (state.otpTimerInterval) {
            clearInterval(state.otpTimerInterval);
            state.otpTimerInterval = null;
        }

        localStorage.removeItem('jack_auth_token');
        state.authToken = '';
        state.currentUser = null;

        updateUserUI();
        showToast('Signed out successfully.', 'info');

        // Reset to Step 1
        if (authStepProfile) authStepProfile.style.display = 'none';
        if (authStepVerify) authStepVerify.style.display = 'none';
        if (authStepRequest) authStepRequest.style.display = 'block';
    }

    if (authSignOutBtn) authSignOutBtn.addEventListener('click', handleLogout);
    if (authSwitchAccountBtn) {
        authSwitchAccountBtn.addEventListener('click', () => {
            handleLogout();
        });
    }

    async function checkAuthState() {
        if (!state.authToken) {
            updateUserUI();
            return;
        }

        try {
            const res = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${state.authToken}`
                }
            });

            if (res.ok) {
                const data = await res.json();
                state.currentUser = data.user;
                updateUserUI();
            } else {
                // Token expired or invalid
                localStorage.removeItem('jack_auth_token');
                state.authToken = '';
                state.currentUser = null;
                updateUserUI();
            }
        } catch (err) {
            console.warn('Auth check skipped (offline or server starting):', err);
            updateUserUI();
        }
    }

    // =========================================================================
    // Initial Application Boot
    // =========================================================================
    checkAuthState();
    loadDashboardStats();
    loadAppointments();
    loadDoctors();
    loadPatients();
    loadMessages();
    loadDirectory();
    loadCompanyDetails();
});
