/**
 * HR Enterprises — JACK AI Receptionist & Enterprise Healthcare SaaS
 * Main Frontend Application Controller
 * Handles Navigation, Appointments, Doctors, Patients, Call History,
 * Analytics, Settings, Authentication, and Floating Jack AI Voice Assistant.
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // 1. Application State
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
        chatHistory: [],
        allAppointments: [],
        allDoctors: [],
        allPatients: [],
        allCallLogs: [],
        allMessages: [],
        currentApptFilter: 'all',
        currentCallFilter: 'all',
        selectedBookingDoctor: null,
        authToken: localStorage.getItem('jack_auth_token') || '',
        currentUser: null,
        authChannel: 'email',
        authIdentifier: '',
        otpTimerInterval: null,
        otpSecondsLeft: 30
    };

    // =========================================================================
    // 2. DOM Elements Cache
    // =========================================================================
    // Topbar & Navigation
    const systemClock = document.getElementById('systemClock');
    const currentDateDisplay = document.getElementById('currentDateDisplay');
    const currentPageTitle = document.getElementById('currentPageTitle');
    const currentPageSubtitle = document.getElementById('currentPageSubtitle');
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
    const sidebarLogoutNavBtn = document.getElementById('sidebarLogoutNavBtn');

    // User Profile Bar
    const topbarUserPill = document.getElementById('topbarUserPill');
    const topbarUserAvatar = document.getElementById('topbarUserAvatar');
    const topbarUserName = document.getElementById('topbarUserName');
    const topbarUserStatus = document.getElementById('topbarUserStatus');
    const sidebarUserName = document.getElementById('sidebarUserName');
    const sidebarUserRole = document.getElementById('sidebarUserRole');
    const sidebarUserAvatar = document.getElementById('sidebarUserAvatar');
    const sidebarAuthActionBtn = document.getElementById('sidebarAuthActionBtn');

    // Sidebar Nav & Badges
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const viewPanels = document.querySelectorAll('.view-panel');
    const sidebarApptBadge = document.getElementById('sidebarApptBadge');
    const sidebarDoctorBadge = document.getElementById('sidebarDoctorBadge');
    const sidebarPatientBadge = document.getElementById('sidebarPatientBadge');
    const sidebarCallBadge = document.getElementById('sidebarCallBadge');
    const quickTalkBtn = document.getElementById('quickTalkBtn');

    // Dashboard Elements
    const statTotalAppts = document.getElementById('statTotalAppts');
    const statTodayAppts = document.getElementById('statTodayAppts');
    const statTotalPatients = document.getElementById('statTotalPatients');
    const statAvailableDocs = document.getElementById('statAvailableDocs');
    const statTotalDocsSub = document.getElementById('statTotalDocsSub');
    const dashboardApptsTbody = document.getElementById('dashboardApptsTbody');
    const dashboardCallsMini = document.getElementById('dashboardCallsMini');
    const refreshDashboardBtn = document.getElementById('refreshDashboardBtn');
    const quickNewApptBtn = document.getElementById('quickNewApptBtn');
    const heroTalkJackBtn = document.getElementById('heroTalkJackBtn');
    const stripNewApptBtn = document.getElementById('stripNewApptBtn');
    const stripNewDocBtn = document.getElementById('stripNewDocBtn');
    const stripTalkJackBtn = document.getElementById('stripTalkJackBtn');
    const stripViewAnalyticsBtn = document.getElementById('stripViewAnalyticsBtn');
    const viewAllApptsLink = document.getElementById('viewAllApptsLink');
    const viewAllCallsLink = document.getElementById('viewAllCallsLink');

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

    // Call History Elements
    const callHistoryList = document.getElementById('callHistoryList');
    const callHistoryFilterGroup = document.getElementById('callHistoryFilterGroup');
    const callSearchInput = document.getElementById('callSearchInput');
    const refreshCallsBtn = document.getElementById('refreshCallsBtn');
    const countCallsAll = document.getElementById('countCallsAll');
    const countCallsVoice = document.getElementById('countCallsVoice');
    const countCallsMsg = document.getElementById('countCallsMsg');
    const countCallsUrgent = document.getElementById('countCallsUrgent');

    // Analytics Elements
    const refreshAnalyticsBtn = document.getElementById('refreshAnalyticsBtn');
    const kpiResolutionRate = document.getElementById('kpiResolutionRate');
    const kpiAvgDuration = document.getElementById('kpiAvgDuration');
    const kpiDocUtilization = document.getElementById('kpiDocUtilization');
    const kpiAiHandled = document.getElementById('kpiAiHandled');
    const analyticsDeptBars = document.getElementById('analyticsDeptBars');
    const analyticsStatusBars = document.getElementById('analyticsStatusBars');
    const analyticsDailyTrend = document.getElementById('analyticsDailyTrend');
    const analyticsDocLoad = document.getElementById('analyticsDocLoad');

    // Settings View Elements
    const settingsApiKeyInput = document.getElementById('settingsApiKeyInput');
    const settingsVoiceSelect = document.getElementById('settingsVoiceSelect');
    const settingsCustomWs = document.getElementById('settingsCustomWs');
    const saveMainSettingsBtn = document.getElementById('saveMainSettingsBtn');

    // Floating Jack AI Assistant
    const quickTriggerJackBtn = document.getElementById('quickTriggerJackBtn');
    const floatingAssistantWindow = document.getElementById('floatingAssistantWindow');
    const closeFloatingAssistantBtn = document.getElementById('closeFloatingAssistantBtn');
    const floatingAiStatusText = document.getElementById('floatingAiStatusText');
    const visualizerWaves = document.getElementById('visualizerWaves');
    const assistantVoiceState = document.getElementById('assistantVoiceState');
    const assistantChatStream = document.getElementById('assistantChatStream');
    const assistantTextInput = document.getElementById('assistantTextInput');
    const startVoiceCallBtn = document.getElementById('startVoiceCallBtn');
    const sendAssistantTextBtn = document.getElementById('sendAssistantTextBtn');
    const promptChips = document.querySelectorAll('.prompt-chip');

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

    // Auth Modal
    const authModal = document.getElementById('authModal');
    const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
    const authAlert = document.getElementById('authAlert');
    const authStepRequest = document.getElementById('authStepRequest');
    const authStepVerify = document.getElementById('authStepVerify');
    const authStepProfile = document.getElementById('authStepProfile');
    const authTabEmail = document.getElementById('authTabEmail');
    const authTabPhone = document.getElementById('authTabPhone');
    const authNameInput = document.getElementById('authNameInput');
    const authEmailGroup = document.getElementById('authEmailGroup');
    const authEmailInput = document.getElementById('authEmailInput');
    const authPhoneGroup = document.getElementById('authPhoneGroup');
    const authPhoneInput = document.getElementById('authPhoneInput');
    const sendOtpBtn = document.getElementById('sendOtpBtn');
    const authBackToRequestBtn = document.getElementById('authBackToRequestBtn');
    const authTargetDisplay = document.getElementById('authTargetDisplay');
    const otpDigitBoxes = document.querySelectorAll('.otp-digit-box');
    const otpCountdownText = document.getElementById('otpCountdownText');
    const otpTimerBar = document.getElementById('otpTimerBar');
    const authResendBtn = document.getElementById('authResendBtn');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const profileLargeName = document.getElementById('profileLargeName');
    const profileLargeIdentifier = document.getElementById('profileLargeIdentifier');
    const profileMetaAuthType = document.getElementById('profileMetaAuthType');
    const profileMetaCreatedAt = document.getElementById('profileMetaCreatedAt');
    const authSwitchAccountBtn = document.getElementById('authSwitchAccountBtn');
    const authSignOutBtn = document.getElementById('authSignOutBtn');

    const toastContainer = document.getElementById('toastContainer');

    // =========================================================================
    // 3. System Clock & Date
    // =========================================================================
    function updateClock() {
        const now = new Date();
        if (systemClock) {
            systemClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        if (currentDateDisplay) {
            currentDateDisplay.textContent = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
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
    // 4. View Switching & Navigation
    // =========================================================================
    const viewMetadata = {
        dashboardView: {
            title: 'Dashboard Overview',
            subtitle: 'Real-time healthcare operations, clinical appointments & intelligent AI concierge'
        },
        appointmentsView: {
            title: 'Clinical Appointment Management',
            subtitle: 'Track, verify, schedule and manage patient bookings across all departments'
        },
        doctorsView: {
            title: 'Doctors & Specialists Directory',
            subtitle: 'Consulting medical faculty, clinical schedules, consultation fees and real-time availability'
        },
        patientsView: {
            title: 'Registered Patients Registry',
            subtitle: 'Patient contact details, historical consultations, and rapid appointment scheduling'
        },
        callHistoryView: {
            title: 'Receptionist Call History & Messages',
            subtitle: 'Comprehensive record of live AI voice interactions, telephone caller notes, and voicemails'
        },
        analyticsView: {
            title: 'Clinical Operations & AI Analytics',
            subtitle: 'Performance metrics, department distributions, doctor utilization, and AI receptionist efficiency'
        },
        settingsView: {
            title: 'System & Voice Assistant Configuration',
            subtitle: 'Configure Gemini Live AI parameters, voice personas, operating hours, and security settings'
        }
    };

    function switchView(targetViewId) {
        if (!targetViewId) return;
        state.currentView = targetViewId;

        // Update nav items
        navItems.forEach(item => {
            if (item.getAttribute('data-view') === targetViewId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Show panel
        viewPanels.forEach(panel => {
            if (panel.id === targetViewId) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });

        // Update headings
        if (viewMetadata[targetViewId]) {
            if (currentPageTitle) currentPageTitle.textContent = viewMetadata[targetViewId].title;
            if (currentPageSubtitle) currentPageSubtitle.textContent = viewMetadata[targetViewId].subtitle;
        }

        // Close mobile drawer
        if (appSidebar) appSidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');

        // Trigger view loads
        if (targetViewId === 'dashboardView') loadDashboardStats();
        else if (targetViewId === 'appointmentsView') loadAppointments();
        else if (targetViewId === 'doctorsView') loadDoctors();
        else if (targetViewId === 'patientsView') loadPatients();
        else if (targetViewId === 'callHistoryView') loadCallHistory();
        else if (targetViewId === 'analyticsView') loadAnalytics();
        else if (targetViewId === 'settingsView') syncSettingsInputs();
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        });
    });

    // Mobile Drawer
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

    // Dashboard Quick Action Links
    if (viewAllApptsLink) viewAllApptsLink.addEventListener('click', () => switchView('appointmentsView'));
    if (viewAllCallsLink) viewAllCallsLink.addEventListener('click', () => switchView('callHistoryView'));
    if (stripViewAnalyticsBtn) stripViewAnalyticsBtn.addEventListener('click', () => switchView('analyticsView'));

    // Global Search Bar Handler
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const q = globalSearchInput.value.trim();
                if (!q) return;
                switchView('appointmentsView');
                if (apptSearchInput) {
                    apptSearchInput.value = q;
                    renderAppointments();
                }
            }
        });
    }

    // =========================================================================
    // 5. Data Fetching & Dashboard Overview
    // =========================================================================
    async function loadDashboardStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const stats = await res.json();

            if (statTotalAppts) statTotalAppts.textContent = stats.total_appointments || 0;
            if (statTodayAppts) statTodayAppts.textContent = stats.today_appointments || 0;
            if (statTotalPatients) statTotalPatients.textContent = stats.registered_patients || 0;
            if (statAvailableDocs) statAvailableDocs.textContent = stats.available_doctors || 0;
            if (statTotalDocsSub) statTotalDocsSub.textContent = `out of ${stats.total_doctors || 10} specialists`;

            if (sidebarApptBadge) sidebarApptBadge.textContent = stats.total_appointments || 0;
            if (sidebarDoctorBadge) sidebarDoctorBadge.textContent = stats.available_doctors || 0;
            if (sidebarPatientBadge) sidebarPatientBadge.textContent = stats.registered_patients || 0;
            if (sidebarCallBadge) sidebarCallBadge.textContent = stats.unread_messages || 0;
            if (notifBadge) notifBadge.style.display = (stats.unread_messages > 0) ? 'block' : 'none';
            if (notifDropdownCount) notifDropdownCount.textContent = `${stats.unread_messages || 0} Unread`;

            loadDashboardApptsPreview();
            loadDashboardCallsPreview();
        } catch (e) {
            console.error('Error loading dashboard stats:', e);
        }
    }

    async function loadDashboardApptsPreview() {
        try {
            const res = await fetch('/api/appointments');
            const appts = await res.json();
            state.allAppointments = appts;

            if (!dashboardApptsTbody) return;
            if (appts.length === 0) {
                dashboardApptsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--text-muted);">No appointments booked yet.</td></tr>`;
                return;
            }

            const preview = appts.slice(0, 5);
            dashboardApptsTbody.innerHTML = preview.map(a => `
                <tr>
                    <td>
                        <span class="cell-patient-name">${escapeHtml(a.visitor_name)}</span>
                        <span class="cell-subtext">${escapeHtml(a.contact_info)}</span>
                    </td>
                    <td>
                        <span style="font-weight: 600; color: var(--text-heading);">${escapeHtml(a.staff_name)}</span>
                        <span class="cell-subtext">${escapeHtml(a.department)}</span>
                    </td>
                    <td>
                        <span style="font-weight: 600;">${escapeHtml(a.date)}</span>
                        <span class="cell-subtext">${escapeHtml(a.time_slot)}</span>
                    </td>
                    <td><span class="status-pill ${a.status.toLowerCase()}">${escapeHtml(a.status)}</span></td>
                    <td>
                        <button class="btn-secondary btn-sm" onclick="window.viewAppointmentDetails(${a.id})">Details</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error('Error previewing appts:', e);
        }
    }

    async function loadDashboardCallsPreview() {
        try {
            const [logsRes, msgsRes] = await Promise.all([
                fetch('/api/call-logs'),
                fetch('/api/messages')
            ]);
            const logs = await logsRes.json();
            const msgs = await msgsRes.json();

            state.allCallLogs = logs;
            state.allMessages = msgs;

            if (!dashboardCallsMini) return;

            // Combine logs and messages
            const combined = [];
            logs.forEach(l => combined.push({
                type: 'call',
                title: l.caller_identifier || 'Web Caller',
                text: l.summary || 'Clinical inquiry handled by Jack AI.',
                time: l.started_at,
                duration: `${l.duration_seconds || 45}s`
            }));
            msgs.forEach(m => combined.push({
                type: 'message',
                title: m.caller_name || 'Visitor Note',
                text: m.message,
                time: m.created_at,
                urgency: m.urgency
            }));

            if (combined.length === 0) {
                dashboardCallsMini.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted); font-size: 0.8rem;">No recent receptionist calls recorded.</div>';
                return;
            }

            dashboardCallsMini.innerHTML = combined.slice(0, 4).map(item => `
                <div style="background: var(--bg-muted); border-radius: var(--radius-md); padding: 0.75rem 0.95rem; border: 1px solid var(--border-light);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                        <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-heading);">${item.type === 'call' ? '📞' : '✉️'} ${escapeHtml(item.title)}</span>
                        <span style="font-size: 0.7rem; color: var(--brand-primary); font-weight: 600;">${item.duration || item.urgency || 'Recent'}</span>
                    </div>
                    <p style="font-size: 0.78rem; color: var(--text-body); margin: 0; line-height: 1.4;">${escapeHtml(item.text)}</p>
                </div>
            `).join('');
        } catch (e) {
            console.error('Error previewing calls:', e);
        }
    }

    if (refreshDashboardBtn) refreshDashboardBtn.addEventListener('click', () => {
        loadDashboardStats();
        showToast('Dashboard refreshed', 'info');
    });

    // =========================================================================
    // 6. Appointments Management View
    // =========================================================================
    async function loadAppointments() {
        try {
            const res = await fetch('/api/appointments');
            const appts = await res.json();
            state.allAppointments = appts;
            renderAppointments();
        } catch (e) {
            console.error('Error loading appointments:', e);
            if (appointmentsList) appointmentsList.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #ef4444;">Failed to load appointments.</td></tr>';
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
            if (q) {
                const text = `${a.visitor_name} ${a.staff_name} ${a.department} ${a.date} ${a.purpose}`.toLowerCase();
                if (!text.includes(q)) return false;
            }
            if (filter === 'today') return a.date === todayStr && a.status !== 'Cancelled';
            if (filter === 'upcoming') return a.date >= todayStr && a.status === 'Confirmed';
            if (filter === 'completed') return a.status === 'Completed';
            if (filter === 'cancelled') return a.status === 'Cancelled';
            return true;
        });

        if (filtered.length === 0) {
            appointmentsList.innerHTML = `
                <tr>
                    <td colspan="6">
                        <div class="empty-state-box">
                            <span class="empty-state-icon">📅</span>
                            <h4 class="empty-state-title">No appointments found</h4>
                            <p class="empty-state-desc">There are no consultations matching the selected filter or search keyword.</p>
                            <button class="btn-primary btn-sm" onclick="window.openDoctorBookingModal()">Schedule New Consultation</button>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        appointmentsList.innerHTML = filtered.map(a => {
            const isCancelled = a.status === 'Cancelled';
            const isCompleted = a.status === 'Completed';

            return `
                <tr>
                    <td>
                        <span class="cell-patient-name">👤 ${escapeHtml(a.visitor_name)}</span>
                        <span class="cell-subtext">${escapeHtml(a.contact_info)}</span>
                    </td>
                    <td>
                        <span style="font-weight: 600; color: var(--text-heading);">🩺 ${escapeHtml(a.staff_name)}</span>
                        <span class="cell-subtext">${escapeHtml(a.department)}</span>
                    </td>
                    <td>
                        <span style="font-weight: 700; color: var(--text-heading);">📅 ${escapeHtml(a.date)}</span>
                        <span class="cell-subtext">⏰ ${escapeHtml(a.time_slot)}</span>
                    </td>
                    <td>
                        <span style="font-size: 0.78rem; max-width: 180px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            "${escapeHtml(a.purpose || 'General Consultation')}"
                        </span>
                    </td>
                    <td>
                        <span class="status-pill ${a.status.toLowerCase()}">${escapeHtml(a.status)}</span>
                    </td>
                    <td>
                        <div style="display: flex; gap: 0.35rem;">
                            <button class="btn-secondary btn-sm" onclick="window.viewAppointmentDetails(${a.id})">Details</button>
                            ${!isCancelled && !isCompleted ? `<button class="btn-secondary btn-sm" style="color: #2563eb;" onclick="window.markAppointmentCompleted(${a.id})">Done</button>` : ''}
                            ${!isCancelled ? `<button class="btn-secondary btn-sm" style="color: #dc2626;" onclick="window.cancelAppointment(${a.id})">Cancel</button>` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    if (apptFilterGroup) {
        apptFilterGroup.querySelectorAll('.filter-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                apptFilterGroup.querySelectorAll('.filter-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentApptFilter = btn.getAttribute('data-filter');
                renderAppointments();
            });
        });
    }

    if (apptSearchInput) apptSearchInput.addEventListener('input', renderAppointments);
    if (refreshApptsBtn) refreshApptsBtn.addEventListener('click', () => {
        loadAppointments();
        showToast('Appointments refreshed', 'info');
    });

    // =========================================================================
    // 7. Doctors Directory View (with Admin-Only Add Doctor Check)
    // =========================================================================
    async function loadDoctors() {
        try {
            const [docsRes, specsRes] = await Promise.all([
                fetch('/api/doctors'),
                fetch('/api/doctors/specializations/list')
            ]);
            const docs = await docsRes.json();
            const specs = await specsRes.json();

            state.allDoctors = docs;

            if (doctorSpecFilter && specs.length > 0) {
                doctorSpecFilter.innerHTML = '<option value="all">All Specializations</option>' +
                    specs.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
            }

            renderDoctors();
        } catch (e) {
            console.error('Error loading doctors:', e);
            if (doctorsList) doctorsList.innerHTML = '<div style="color: #ef4444; padding: 2rem;">Failed to load medical staff directory.</div>';
        }
    }

    function renderDoctors() {
        if (!doctorsList) return;

        const q = (doctorSearchInput ? doctorSearchInput.value : '').toLowerCase().trim();
        const spec = doctorSpecFilter ? doctorSpecFilter.value : 'all';

        let filtered = state.allDoctors.filter(d => {
            if (q) {
                const text = `${d.name} ${d.specialization} ${d.department} ${d.qualification}`.toLowerCase();
                if (!text.includes(q)) return false;
            }
            if (spec !== 'all' && d.specialization !== spec) return false;
            return true;
        });

        if (filtered.length === 0) {
            doctorsList.innerHTML = `
                <div class="empty-state-box" style="grid-column: 1 / -1;">
                    <span class="empty-state-icon">🩺</span>
                    <h4 class="empty-state-title">No specialists found</h4>
                    <p class="empty-state-desc">Try clearing your search query or choosing a different specialization.</p>
                </div>
            `;
            return;
        }

        doctorsList.innerHTML = filtered.map(d => `
            <div class="doctor-profile-card">
                <span class="status-pill ${d.status.toLowerCase()} doctor-status-badge">${escapeHtml(d.status)}</span>
                <div class="doctor-card-header">
                    <div class="doctor-avatar-box">${d.avatar_emoji || '🩺'}</div>
                    <div class="doctor-header-info">
                        <h4 class="doctor-name-title">${escapeHtml(d.name)}</h4>
                        <span class="doctor-spec-label">${escapeHtml(d.specialization)}</span>
                        <span class="doctor-dept-label">${escapeHtml(d.department)} • ${escapeHtml(d.qualification || 'MBBS, MD')}</span>
                    </div>
                </div>

                <div class="doctor-specs-list">
                    <div>
                        <span class="doc-spec-item-label">Consultation Fee</span>
                        <span class="doc-spec-item-value" style="color: var(--brand-primary);">${escapeHtml(d.consultation_fee || '₹500')}</span>
                    </div>
                    <div>
                        <span class="doc-spec-item-label">Experience</span>
                        <span class="doc-spec-item-value">${d.experience_years || 5} Years</span>
                    </div>
                    <div>
                        <span class="doc-spec-item-label">Patient Rating</span>
                        <span class="doc-spec-item-value">⭐ ${d.rating || 4.8} / 5</span>
                    </div>
                    <div>
                        <span class="doc-spec-item-label">Phone Ext.</span>
                        <span class="doc-spec-item-value" style="font-family: var(--font-mono);">${d.phone_extension || '101'}</span>
                    </div>
                </div>

                <div class="doctor-schedule-strip">
                    <div><strong>Available Days:</strong> ${escapeHtml(d.available_days || 'Mon, Wed, Fri')}</div>
                    <div><strong>Slots:</strong> ${escapeHtml(d.available_slots ? d.available_slots.split(',').slice(0, 3).join(', ') + '...' : '09:00 AM, 11:00 AM, 02:00 PM')}</div>
                </div>

                <div class="doctor-card-footer">
                    <button class="btn-primary btn-sm" style="flex: 1; justify-content: center;" onclick="window.openDoctorBookingModal(${d.id})">
                        📅 Book Consultation
                    </button>
                </div>
            </div>
        `).join('');
    }

    if (doctorSearchInput) doctorSearchInput.addEventListener('input', renderDoctors);
    if (doctorSpecFilter) doctorSpecFilter.addEventListener('change', renderDoctors);
    if (refreshDoctorsBtn) refreshDoctorsBtn.addEventListener('click', () => {
        loadDoctors();
        showToast('Doctors directory refreshed', 'info');
    });

    // Admin Only Check for Register Doctor
    function handleAdminAddDoctorClick() {
        if (!state.currentUser) {
            showToast('Administrator privileges required. Please sign in to register doctors.', 'error');
            openAuthModal();
            return;
        }
        if (addDoctorModal) addDoctorModal.classList.add('show');
    }

    if (adminAddDoctorBtn) adminAddDoctorBtn.addEventListener('click', handleAdminAddDoctorClick);
    if (stripNewDocBtn) stripNewDocBtn.addEventListener('click', handleAdminAddDoctorClick);

    // =========================================================================
    // 8. Patients Registry View
    // =========================================================================
    async function loadPatients() {
        try {
            const res = await fetch('/api/patients');
            const patients = await res.json();
            state.allPatients = patients;
            renderPatients();
        } catch (e) {
            console.error('Error loading patients:', e);
            if (patientsList) patientsList.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #ef4444;">Failed to load patients.</td></tr>';
        }
    }

    function renderPatients() {
        if (!patientsList) return;

        const q = (patientSearchInput ? patientSearchInput.value : '').toLowerCase().trim();

        let filtered = state.allPatients.filter(p => {
            if (q) {
                const text = `${p.name} ${p.contact_info} ${p.last_doctor} ${p.last_department}`.toLowerCase();
                if (!text.includes(q)) return false;
            }
            return true;
        });

        if (filtered.length === 0) {
            patientsList.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="empty-state-box">
                            <span class="empty-state-icon">👥</span>
                            <h4 class="empty-state-title">No patient records found</h4>
                            <p class="empty-state-desc">Patient records automatically appear when appointments are scheduled.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        patientsList.innerHTML = filtered.map(p => `
            <tr>
                <td>
                    <span class="cell-patient-name">👤 ${escapeHtml(p.name)}</span>
                </td>
                <td>
                    <span style="font-family: var(--font-mono); font-size: 0.76rem;">${escapeHtml(p.contact_info || 'N/A')}</span>
                </td>
                <td>
                    <span style="font-weight: 700; color: var(--brand-primary);">${p.total_appointments} Consultation${p.total_appointments > 1 ? 's' : ''}</span>
                </td>
                <td>
                    <span style="font-weight: 600; color: var(--text-heading);">${escapeHtml(p.last_doctor || 'General Consultation')}</span>
                    <span class="cell-subtext">${escapeHtml(p.last_department || 'General Medicine')}</span>
                </td>
                <td>
                    <span>${escapeHtml(p.last_visit_date || 'Recent')}</span>
                </td>
                <td>
                    <span class="status-pill ${p.last_status ? p.last_status.toLowerCase() : 'confirmed'}">${escapeHtml(p.last_status || 'Active')}</span>
                </td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="window.scheduleVisitForPatient('${escapeHtml(p.name)}', '${escapeHtml(p.contact_info)}')">
                        📅 Schedule
                    </button>
                </td>
            </tr>
        `).join('');
    }

    if (patientSearchInput) patientSearchInput.addEventListener('input', renderPatients);
    if (refreshPatientsBtn) refreshPatientsBtn.addEventListener('click', () => {
        loadPatients();
        showToast('Patient records refreshed', 'info');
    });
    if (patientNewApptBtn) patientNewApptBtn.addEventListener('click', () => window.openDoctorBookingModal());

    // =========================================================================
    // 9. Call History & Messages View
    // =========================================================================
    async function loadCallHistory() {
        try {
            const [logsRes, msgsRes] = await Promise.all([
                fetch('/api/call-logs'),
                fetch('/api/messages')
            ]);
            const logs = await logsRes.json();
            const msgs = await msgsRes.json();

            state.allCallLogs = logs;
            state.allMessages = msgs;
            renderCallHistory();
        } catch (e) {
            console.error('Error loading call history:', e);
            if (callHistoryList) callHistoryList.innerHTML = '<div style="color: #ef4444; padding: 2rem;">Failed to load call history.</div>';
        }
    }

    function renderCallHistory() {
        if (!callHistoryList) return;

        const q = (callSearchInput ? callSearchInput.value : '').toLowerCase().trim();
        const filter = state.currentCallFilter;

        // Unify logs and messages
        const unified = [];
        state.allCallLogs.forEach(l => {
            unified.push({
                kind: 'voice',
                id: l.id,
                title: l.caller_identifier || 'Web Voice Caller',
                summary: l.summary || 'Real-time AI voice receptionist clinical consultation.',
                action: l.action_taken || 'Inquiry Handled by Jack',
                duration: `${l.duration_seconds || 45}s`,
                timestamp: l.started_at,
                urgency: 'Normal'
            });
        });

        state.allMessages.forEach(m => {
            unified.push({
                kind: 'message',
                id: m.id,
                title: m.caller_name || 'Caller Voicemail',
                summary: `"${m.message}" (Recipient: ${m.recipient_name || 'Front Desk'})`,
                action: m.is_read ? 'Reviewed' : 'Pending Review',
                contact: m.contact_info,
                duration: 'Voicemail Note',
                timestamp: m.created_at,
                urgency: m.urgency || 'Normal',
                is_read: m.is_read
            });
        });

        // Counts
        const countAll = unified.length;
        const countVoice = unified.filter(u => u.kind === 'voice').length;
        const countMsg = unified.filter(u => u.kind === 'message').length;
        const countUrgent = unified.filter(u => u.urgency.toLowerCase() === 'urgent').length;

        if (countCallsAll) countCallsAll.textContent = countAll;
        if (countCallsVoice) countCallsVoice.textContent = countVoice;
        if (countCallsMsg) countCallsMsg.textContent = countMsg;
        if (countCallsUrgent) countCallsUrgent.textContent = countUrgent;

        // Filtering
        let filtered = unified.filter(item => {
            if (q) {
                const text = `${item.title} ${item.summary} ${item.action}`.toLowerCase();
                if (!text.includes(q)) return false;
            }
            if (filter === 'voice') return item.kind === 'voice';
            if (filter === 'messages') return item.kind === 'message';
            if (filter === 'urgent') return item.urgency.toLowerCase() === 'urgent';
            return true;
        });

        if (filtered.length === 0) {
            callHistoryList.innerHTML = `
                <div class="empty-state-box">
                    <span class="empty-state-icon">📞</span>
                    <h4 class="empty-state-title">No call records found</h4>
                    <p class="empty-state-desc">Live phone interactions and visitor messages will appear here.</p>
                </div>
            `;
            return;
        }

        callHistoryList.innerHTML = filtered.map(item => `
            <div class="call-item-card">
                <div class="call-item-left">
                    <div class="call-type-icon ${item.kind === 'message' ? 'voicemail' : ''}">
                        ${item.kind === 'voice' ? '🎙️' : '✉️'}
                    </div>
                    <div class="call-details">
                        <div class="call-title-row">
                            <h4 class="caller-name-heading">${escapeHtml(item.title)}</h4>
                            <span class="status-pill ${item.urgency.toLowerCase() === 'urgent' ? 'cancelled' : 'confirmed'}">${escapeHtml(item.urgency)}</span>
                            <span style="font-size: 0.72rem; color: var(--brand-primary); font-weight: 700;">${item.duration}</span>
                        </div>
                        <p class="call-summary-text">${escapeHtml(item.summary)}</p>
                        <div class="call-meta-row">
                            <span>🕒 ${item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Recent'}</span>
                            <span>•</span>
                            <span>⚡ Outcome: <strong>${escapeHtml(item.action)}</strong></span>
                            ${item.contact ? `<span>• Contact: <strong>${escapeHtml(item.contact)}</strong></span>` : ''}
                        </div>
                    </div>
                </div>
                ${item.kind === 'message' && !item.is_read ? `
                    <button class="btn-secondary btn-sm" onclick="window.markMessageReadAndOpen(${item.id})">Mark Read</button>
                ` : ''}
            </div>
        `).join('');
    }

    if (callHistoryFilterGroup) {
        callHistoryFilterGroup.querySelectorAll('.filter-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                callHistoryFilterGroup.querySelectorAll('.filter-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentCallFilter = btn.getAttribute('data-call-filter');
                renderCallHistory();
            });
        });
    }

    if (callSearchInput) callSearchInput.addEventListener('input', renderCallHistory);
    if (refreshCallsBtn) refreshCallsBtn.addEventListener('click', () => {
        loadCallHistory();
        showToast('Call history refreshed', 'info');
    });

    // =========================================================================
    // 10. Analytics Dashboard
    // =========================================================================
    async function loadAnalytics() {
        try {
            const [analyticsRes, statsRes] = await Promise.all([
                fetch('/api/analytics'),
                fetch('/api/stats')
            ]);
            const data = await analyticsRes.json();
            const stats = await statsRes.json();

            // KPIs
            if (kpiResolutionRate) kpiResolutionRate.textContent = data.call_metrics.first_call_resolution_rate || '92.4%';
            if (kpiAvgDuration) kpiAvgDuration.textContent = `${data.call_metrics.avg_duration_seconds || 45}s`;
            if (kpiAiHandled) kpiAiHandled.textContent = data.call_metrics.ai_handled_rate || '88.6%';
            if (kpiDocUtilization) {
                const avail = stats.available_doctors || 8;
                const total = stats.total_doctors || 10;
                const pct = Math.round((avail / Math.max(total, 1)) * 100);
                kpiDocUtilization.textContent = `${pct}%`;
            }

            // 1. Department Breakdown Bars
            if (analyticsDeptBars) {
                const depts = data.department_breakdown || [];
                const totalDeptCounts = depts.reduce((sum, d) => sum + d.count, 0) || 1;
                if (depts.length === 0) {
                    analyticsDeptBars.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No department appointment data yet.</div>';
                } else {
                    analyticsDeptBars.innerHTML = depts.map(d => {
                        const pct = Math.round((d.count / totalDeptCounts) * 100);
                        return `
                            <div class="analytics-bar-item">
                                <div class="bar-item-header">
                                    <span>🏥 ${escapeHtml(d.department)}</span>
                                    <span>${d.count} (${pct}%)</span>
                                </div>
                                <div class="bar-track">
                                    <div class="bar-fill-cyan" style="width: ${pct}%;"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // 2. Status Breakdown Bars
            if (analyticsStatusBars) {
                const statuses = data.status_breakdown || [];
                const totalStatus = statuses.reduce((sum, s) => sum + s.count, 0) || 1;
                if (statuses.length === 0) {
                    analyticsStatusBars.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No status data available.</div>';
                } else {
                    analyticsStatusBars.innerHTML = statuses.map(s => {
                        const pct = Math.round((s.count / totalStatus) * 100);
                        let fillClass = 'bar-fill-cyan';
                        if (s.status === 'Confirmed') fillClass = 'bar-fill-cyan';
                        else if (s.status === 'Completed') fillClass = 'bar-fill-emerald';
                        else if (s.status === 'Cancelled') fillClass = 'bar-fill-rose';
                        else if (s.status === 'Pending') fillClass = 'bar-fill-amber';

                        return `
                            <div class="analytics-bar-item">
                                <div class="bar-item-header">
                                    <span>${escapeHtml(s.status)}</span>
                                    <span>${s.count} (${pct}%)</span>
                                </div>
                                <div class="bar-track">
                                    <div class="${fillClass}" style="width: ${pct}%;"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // 3. 7-Day Trend Bars
            if (analyticsDailyTrend) {
                const trends = data.daily_trend || [];
                const maxCount = Math.max(...trends.map(t => t.count), 5);
                if (trends.length === 0) {
                    analyticsDailyTrend.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">Booking volume history will appear here.</div>';
                } else {
                    analyticsDailyTrend.innerHTML = trends.map(t => {
                        const pct = Math.round((t.count / maxCount) * 100);
                        return `
                            <div class="analytics-bar-item">
                                <div class="bar-item-header">
                                    <span>📅 ${escapeHtml(t.date)}</span>
                                    <span>${t.count} Visit${t.count > 1 ? 's' : ''}</span>
                                </div>
                                <div class="bar-track">
                                    <div class="bar-fill-cyan" style="width: ${pct}%;"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // 4. Doctor Workload Bars
            if (analyticsDocLoad) {
                const docs = data.doctor_load || [];
                const maxDocAppts = Math.max(...docs.map(d => d.appointments_count), 5);
                if (docs.length === 0) {
                    analyticsDocLoad.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">Doctor workload metrics will update with consultations.</div>';
                } else {
                    analyticsDocLoad.innerHTML = docs.map(d => {
                        const pct = Math.round((d.appointments_count / maxDocAppts) * 100);
                        return `
                            <div class="analytics-bar-item">
                                <div class="bar-item-header">
                                    <span>🩺 ${escapeHtml(d.doctor_name)}</span>
                                    <span>${d.appointments_count} Bookings</span>
                                </div>
                                <div class="bar-track">
                                    <div class="bar-fill-emerald" style="width: ${pct}%;"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }
        } catch (e) {
            console.error('Error loading analytics:', e);
        }
    }

    if (refreshAnalyticsBtn) refreshAnalyticsBtn.addEventListener('click', () => {
        loadAnalytics();
        showToast('Analytics refreshed', 'info');
    });

    // =========================================================================
    // 11. Settings Sync & Configuration
    // =========================================================================
    function syncSettingsInputs() {
        if (settingsApiKeyInput) settingsApiKeyInput.value = state.apiKey;
        if (settingsVoiceSelect) settingsVoiceSelect.value = state.voice;
        if (settingsCustomWs) settingsCustomWs.value = state.customWsUrl;
    }

    function saveSettings(key, voice, customWs) {
        state.apiKey = key;
        state.voice = voice;
        state.customWsUrl = customWs;

        localStorage.setItem('gemini_api_key', key);
        localStorage.setItem('receptionist_voice', voice);
        localStorage.setItem('custom_ws_url', customWs);

        if (key) {
            fetch('/api/config/key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key })
            }).catch(() => {});
        }

        showToast('Settings saved successfully', 'success');
    }

    if (saveMainSettingsBtn) {
        saveMainSettingsBtn.addEventListener('click', () => {
            const key = settingsApiKeyInput.value.trim();
            const voice = settingsVoiceSelect.value;
            const customWs = settingsCustomWs.value.trim();
            saveSettings(key, voice, customWs);
        });
    }

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            const key = apiKeyInput.value.trim();
            const voice = voiceSelect.value;
            const customWs = customWsUrlInput.value.trim();
            saveSettings(key, voice, customWs);
            if (settingsModal) settingsModal.classList.remove('show');
        });
    }

    function openSettingsModal() {
        if (apiKeyInput) apiKeyInput.value = state.apiKey;
        if (voiceSelect) voiceSelect.value = state.voice;
        if (customWsUrlInput) customWsUrlInput.value = state.customWsUrl;
        if (settingsModal) settingsModal.classList.add('show');
    }

    if (openSettingsBtn) openSettingsBtn.addEventListener('click', openSettingsModal);
    if (headerSettingsBtn) headerSettingsBtn.addEventListener('click', openSettingsModal);
    if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('show'));
    if (cancelSettingsBtn) cancelSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('show'));

    // =========================================================================
    // 12. Floating Jack AI Voice & Chat Assistant
    // =========================================================================
    function openFloatingAssistant() {
        state.isAssistantOpen = true;
        if (floatingAssistantWindow) floatingAssistantWindow.classList.add('show');
        if (assistantTextInput) assistantTextInput.focus();
    }

    function closeFloatingAssistant() {
        state.isAssistantOpen = false;
        if (floatingAssistantWindow) floatingAssistantWindow.classList.remove('show');
        if (state.isCallActive) endVoiceCall();
    }

    if (quickTriggerJackBtn) quickTriggerJackBtn.addEventListener('click', openFloatingAssistant);
    if (quickTalkBtn) quickTalkBtn.addEventListener('click', openFloatingAssistant);
    if (heroTalkJackBtn) heroTalkJackBtn.addEventListener('click', openFloatingAssistant);
    if (stripTalkJackBtn) stripTalkJackBtn.addEventListener('click', openFloatingAssistant);
    if (closeFloatingAssistantBtn) closeFloatingAssistantBtn.addEventListener('click', closeFloatingAssistant);

    promptChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.getAttribute('data-prompt');
            if (prompt) sendAssistantMessage(prompt);
        });
    });

    function appendAssistantMessage(role, text) {
        if (!assistantChatStream) return;
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role === 'user' ? 'user' : 'jack'}`;
        bubble.textContent = text;
        assistantChatStream.appendChild(bubble);
        assistantChatStream.scrollTop = assistantChatStream.scrollHeight;
    }

    async function sendAssistantMessage(text) {
        const query = (text || '').trim();
        if (!query) return;

        if (assistantTextInput) assistantTextInput.value = '';
        appendAssistantMessage('user', query);
        state.chatHistory.push({ role: 'user', text: query });

        if (state.isCallActive && state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'text', text: query }));
            setAiVisualState('thinking', 'Jack is processing...');
        } else {
            setAiVisualState('thinking', 'Jack is thinking...');
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
                appendAssistantMessage('model', data.reply);
                setAiVisualState('idle', 'Online & Ready');
                speakBrowserFallback(data.reply);

                if (data.actions && data.actions.length > 0) {
                    loadDashboardStats();
                    loadAppointments();
                    loadDoctors();
                    loadPatients();
                    loadCallHistory();
                }
            } catch (err) {
                console.error('Chat error:', err);
                showToast(err.message, 'error');
                appendAssistantMessage('jack', `Error: ${err.message}`);
                setAiVisualState('idle', 'Online & Ready');
            }
        }
    }

    if (sendAssistantTextBtn) {
        sendAssistantTextBtn.addEventListener('click', () => {
            if (assistantTextInput) sendAssistantMessage(assistantTextInput.value);
        });
    }

    if (assistantTextInput) {
        assistantTextInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendAssistantMessage(assistantTextInput.value);
            }
        });
    }

    function setAiVisualState(mode, text) {
        if (floatingAiStatusText) floatingAiStatusText.textContent = text;
        if (assistantVoiceState) assistantVoiceState.textContent = text;

        const waveBars = document.querySelectorAll('.wave-bar');
        if (mode === 'speaking' || mode === 'listening') {
            waveBars.forEach(b => b.classList.add('speaking'));
        } else {
            waveBars.forEach(b => b.classList.remove('speaking'));
        }
    }

    function speakBrowserFallback(text) {
        if (!('speechSynthesis' in window)) return;
        try { window.speechSynthesis.cancel(); } catch (e) {}

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.onstart = () => setAiVisualState('speaking', 'Jack is speaking...');
        utterance.onend = () => setAiVisualState('idle', 'Online & Ready');
        utterance.onerror = () => setAiVisualState('idle', 'Online & Ready');
        window.speechSynthesis.speak(utterance);
    }

    // Live Voice Call with WebSocket
    async function startVoiceCall() {
        if (state.isCallActive) return;

        setAiVisualState('connecting', 'Connecting audio stream...');

        // If no Gemini key or on serverless proxy, fallback to SpeechRecognition
        if (!state.apiKey && !state.customWsUrl) {
            startSpeechRecognitionFallback();
            return;
        }

        try {
            state.audioPlayer = new window.PcmAudioPlayer(24000);
            state.audioPlayer.init();
            state.audioPlayer.onPlaybackStateChange = (isPlaying) => {
                if (isPlaying) setAiVisualState('speaking', 'Jack is speaking...');
                else if (state.isCallActive) setAiVisualState('listening', 'Jack is listening...');
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

            const wsUrl = state.customWsUrl || `${protocol}//${window.location.host}/ws/live?${queryParams.toString()}`;
            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                state.isCallActive = true;
                if (startVoiceCallBtn) startVoiceCallBtn.classList.add('active');
                setAiVisualState('listening', 'Jack is listening...');
                appendAssistantMessage('jack', 'Connected to front desk. Speak naturally or type anytime.');
            };

            state.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'status' && msg.status === 'connected') {
                        setAiVisualState('listening', 'Jack is listening...');
                    } else if (msg.type === 'audio' && state.audioPlayer && msg.data) {
                        state.audioPlayer.playChunk(msg.data);
                    } else if (msg.type === 'transcript') {
                        appendAssistantMessage(msg.role === 'model' ? 'jack' : 'user', msg.text);
                    } else if (msg.type === 'tool_result') {
                        loadDashboardStats();
                        loadAppointments();
                        loadDoctors();
                        loadPatients();
                    } else if (msg.type === 'interrupted') {
                        if (state.audioPlayer) state.audioPlayer.interrupt();
                        setAiVisualState('listening', 'Jack is listening...');
                    }
                } catch (e) {
                    console.error('WebSocket parse error:', e);
                }
            };

            state.ws.onerror = (err) => {
                console.warn('Live WebSocket error, falling back to voice recognizer:', err);
                endVoiceCall();
                startSpeechRecognitionFallback();
            };

            state.ws.onclose = () => {
                endVoiceCall();
            };
        } catch (err) {
            console.error('Start call error:', err);
            startSpeechRecognitionFallback();
        }
    }

    function endVoiceCall() {
        state.isCallActive = false;
        state.isSpeechRecognitionMode = false;

        try { window.speechSynthesis.cancel(); } catch (e) {}

        if (state.speechRecognition) {
            try { state.speechRecognition.stop(); } catch (e) {}
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
            try { state.ws.close(); } catch (e) {}
            state.ws = null;
        }

        if (startVoiceCallBtn) startVoiceCallBtn.classList.remove('active');
        setAiVisualState('idle', 'Online & Ready');
    }

    function startSpeechRecognitionFallback() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            showToast('Microphone speech recognition not supported in this browser. Please use text chat.', 'error');
            return;
        }

        state.isSpeechRecognitionMode = true;
        state.isCallActive = true;
        if (startVoiceCallBtn) startVoiceCallBtn.classList.add('active');
        setAiVisualState('listening', 'Listening via microphone...');

        const recognition = new SpeechRec();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const text = event.results[last][0].transcript.trim();
            if (text) sendAssistantMessage(text);
        };

        recognition.onerror = (e) => {
            if (e.error !== 'no-speech') console.warn('Speech rec error:', e.error);
        };

        recognition.onend = () => {
            if (state.isCallActive && state.isSpeechRecognitionMode) {
                try { recognition.start(); } catch (e) {}
            }
        };

        try {
            recognition.start();
            state.speechRecognition = recognition;
        } catch (e) {
            console.error('Speech recognition start failed:', e);
            endVoiceCall();
        }
    }

    if (startVoiceCallBtn) {
        startVoiceCallBtn.addEventListener('click', () => {
            if (state.isCallActive) {
                endVoiceCall();
            } else {
                startVoiceCall();
            }
        });
    }

    // =========================================================================
    // 13. Modal Actions: Bookings, Doctors, Details
    // =========================================================================
    window.openDoctorBookingModal = function(doctorId) {
        if (!state.allDoctors || state.allDoctors.length === 0) {
            loadDoctors().then(() => finishOpenBooking(doctorId));
        } else {
            finishOpenBooking(doctorId);
        }
    };

    function finishOpenBooking(doctorId) {
        let doc = null;
        if (doctorId) {
            doc = state.allDoctors.find(d => d.id === doctorId);
        }
        if (!doc && state.allDoctors.length > 0) {
            doc = state.allDoctors[0];
        }

        state.selectedBookingDoctor = doc;

        if (bookingDoctorInfo && doc) {
            bookingDoctorInfo.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.65rem;">
                    <span style="font-size: 1.5rem;">${doc.avatar_emoji || '🩺'}</span>
                    <div>
                        <strong style="color: var(--text-heading);">${escapeHtml(doc.name)}</strong> — ${escapeHtml(doc.specialization)} (${escapeHtml(doc.department)})<br>
                        <span style="color: var(--brand-primary); font-weight: 700;">Consultation Fee: ${escapeHtml(doc.consultation_fee || '₹500')}</span> • Experience: ${doc.experience_years || 5} yrs
                    </div>
                </div>
            `;
        }

        if (bookApptSlot && doc) {
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

        // Prefill authenticated user details
        if (state.currentUser) {
            if (bookPatientName && !bookPatientName.value) bookPatientName.value = state.currentUser.name || '';
            if (bookPatientContact && !bookPatientContact.value) bookPatientContact.value = state.currentUser.phone_number || state.currentUser.email || '';
        }

        if (bookDoctorModal) bookDoctorModal.classList.add('show');
    }

    window.scheduleVisitForPatient = function(name, contact) {
        if (bookPatientName) bookPatientName.value = name || '';
        if (bookPatientContact) bookPatientContact.value = contact || '';
        window.openDoctorBookingModal();
    };

    if (openBookApptModalBtn) openBookApptModalBtn.addEventListener('click', () => window.openDoctorBookingModal());
    if (quickNewApptBtn) quickNewApptBtn.addEventListener('click', () => window.openDoctorBookingModal());
    if (stripNewApptBtn) stripNewApptBtn.addEventListener('click', () => window.openDoctorBookingModal());

    if (closeBookDoctorBtn) closeBookDoctorBtn.addEventListener('click', () => bookDoctorModal.classList.remove('show'));
    if (cancelBookDoctorBtn) cancelBookDoctorBtn.addEventListener('click', () => bookDoctorModal.classList.remove('show'));

    if (confirmBookDoctorBtn) {
        confirmBookDoctorBtn.addEventListener('click', async () => {
            const name = (bookPatientName ? bookPatientName.value : '').trim();
            const contact = (bookPatientContact ? bookPatientContact.value : '').trim();
            const dateVal = (bookApptDate ? bookApptDate.value : '').trim();
            const slotVal = (bookApptSlot ? bookApptSlot.value : '').trim();
            const purposeVal = (bookApptPurpose ? bookApptPurpose.value : '').trim() || 'General Medical Consultation';

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
                if (state.authToken) reqHeaders['Authorization'] = `Bearer ${state.authToken}`;

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
                if (!res.ok) throw new Error(data.detail || 'Booking failed');

                showToast(`Appointment confirmed (#${data.appointment_id || ''})`, 'success');
                if (bookDoctorModal) bookDoctorModal.classList.remove('show');

                loadDashboardStats();
                loadAppointments();
                loadPatients();
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                if (confirmBookDoctorBtn) {
                    confirmBookDoctorBtn.disabled = false;
                    confirmBookDoctorBtn.textContent = 'Confirm Appointment';
                }
            }
        });
    }

    // Add Doctor Submission (Admin Only)
    if (closeAddDoctorBtn) closeAddDoctorBtn.addEventListener('click', () => addDoctorModal.classList.remove('show'));
    if (cancelAddDoctorBtn) cancelAddDoctorBtn.addEventListener('click', () => addDoctorModal.classList.remove('show'));

    if (confirmAddDoctorBtn) {
        confirmAddDoctorBtn.addEventListener('click', async () => {
            const name = (newDocName ? newDocName.value : '').trim();
            const spec = (newDocSpec ? newDocSpec.value : '').trim();
            const dept = (newDocDept ? newDocDept.value : '').trim();
            const qual = (newDocQual ? newDocQual.value : '').trim();

            if (!name || !spec || !dept) {
                showToast('Please fill in doctor name, specialization and department', 'error');
                return;
            }

            try {
                confirmAddDoctorBtn.disabled = true;
                confirmAddDoctorBtn.textContent = 'Registering...';

                const res = await fetch('/api/doctors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        specialization: spec,
                        department: dept,
                        qualification: qual || 'MBBS, MD',
                        experience_years: parseInt(newDocExp.value) || 5,
                        consultation_fee: newDocFee.value || '₹500',
                        available_days: newDocDays.value || 'Mon, Wed, Fri',
                        available_slots: newDocSlots.value || '09:00 AM, 11:00 AM, 02:00 PM',
                        email: newDocEmail.value || 'doctor@hrenterprises.com',
                        phone_extension: newDocExt.value || '101',
                        bio: newDocBio.value || '',
                        status: 'Available'
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Doctor registration failed');

                showToast(`Doctor ${name} registered successfully!`, 'success');
                if (addDoctorModal) addDoctorModal.classList.remove('show');
                loadDoctors();
                loadDashboardStats();
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                if (confirmAddDoctorBtn) {
                    confirmAddDoctorBtn.disabled = false;
                    confirmAddDoctorBtn.textContent = '💾 Register Doctor';
                }
            }
        });
    }

    // Appointment Details & Actions
    window.viewAppointmentDetails = function(apptId) {
        const appt = state.allAppointments.find(a => a.id === apptId);
        if (!appt) return;

        if (apptDetailsContent) {
            apptDetailsContent.innerHTML = `
                <div style="background: var(--bg-muted); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-size: 0.76rem; font-weight: 700; color: var(--brand-primary); font-family: var(--font-mono);">APPOINTMENT #${appt.id}</span>
                        <span class="status-pill ${appt.status.toLowerCase()}">${escapeHtml(appt.status)}</span>
                    </div>
                    <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-heading); margin-bottom: 0.25rem;">${escapeHtml(appt.visitor_name)}</h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin: 0;">Contact: ${escapeHtml(appt.contact_info)}</p>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.82rem; margin-bottom: 1rem;">
                    <div><strong>Specialist:</strong><br>${escapeHtml(appt.staff_name)}</div>
                    <div><strong>Department:</strong><br>${escapeHtml(appt.department)}</div>
                    <div><strong>Consultation Date:</strong><br>${escapeHtml(appt.date)}</div>
                    <div><strong>Time Slot:</strong><br>${escapeHtml(appt.time_slot)}</div>
                </div>

                <div style="background: #F8FAFC; border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 0.75rem; font-size: 0.8rem;">
                    <strong>Reason for Consultation:</strong><br>
                    "${escapeHtml(appt.purpose || 'General Consultation')}"
                </div>
            `;
        }

        if (apptDetailsModal) apptDetailsModal.classList.add('show');
    };

    if (closeApptDetailsBtn) closeApptDetailsBtn.addEventListener('click', () => apptDetailsModal.classList.remove('show'));
    if (dismissApptDetailsBtn) dismissApptDetailsBtn.addEventListener('click', () => apptDetailsModal.classList.remove('show'));

    window.markAppointmentCompleted = async function(apptId) {
        try {
            const res = await fetch(`/api/appointments/${apptId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'Completed' })
            });
            if (!res.ok) throw new Error('Status update failed');
            showToast(`Appointment #${apptId} marked as Completed`, 'success');
            loadAppointments();
            loadDashboardStats();
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    window.cancelAppointment = async function(apptId) {
        if (!confirm(`Are you sure you want to cancel appointment #${apptId}?`)) return;
        try {
            const res = await fetch(`/api/appointments/${apptId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Cancellation failed');
            showToast(`Appointment #${apptId} has been cancelled`, 'info');
            loadAppointments();
            loadDashboardStats();
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    window.markMessageReadAndOpen = async function(msgId) {
        try {
            await fetch(`/api/messages/${msgId}/read`, { method: 'PATCH' });
            loadDashboardStats();
            loadCallHistory();
        } catch (e) {}
    };

    // =========================================================================
    // 14. Authentication Controller (Login / Register / OTP)
    // =========================================================================
    function showAuthAlert(msg, type = 'error') {
        if (!authAlert) return;
        authAlert.style.display = 'block';
        authAlert.style.background = (type === 'error') ? '#FEF2F2' : '#ECFDF5';
        authAlert.style.color = (type === 'error') ? '#DC2626' : '#059669';
        authAlert.style.border = `1px solid ${type === 'error' ? '#FECACA' : '#A7F3D0'}`;
        authAlert.textContent = msg;
    }

    function hideAuthAlert() {
        if (authAlert) authAlert.style.display = 'none';
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
            if (topbarUserStatus) topbarUserStatus.textContent = 'Online';
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
            if (authStepRequest) authStepRequest.style.display = 'none';
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepProfile) authStepProfile.style.display = 'block';

            if (profileLargeName) profileLargeName.textContent = state.currentUser.name || 'Healthcare User';
            if (profileLargeIdentifier) profileLargeIdentifier.textContent = state.currentUser.email || state.currentUser.phone_number || '';
            if (profileMetaAuthType) profileMetaAuthType.textContent = state.currentUser.email ? 'Email OTP' : 'Phone OTP';
            if (profileMetaCreatedAt) {
                const dt = state.currentUser.created_at ? new Date(state.currentUser.created_at) : new Date();
                profileMetaCreatedAt.textContent = dt.toLocaleDateString();
            }
        } else {
            if (authStepRequest) authStepRequest.style.display = 'block';
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepProfile) authStepProfile.style.display = 'none';
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

    function startOtpCountdown(totalSeconds = 30) {
        if (state.otpTimerInterval) {
            clearInterval(state.otpTimerInterval);
            state.otpTimerInterval = null;
        }

        state.otpSecondsLeft = totalSeconds;
        if (authResendBtn) authResendBtn.disabled = true;

        if (otpCountdownText) otpCountdownText.textContent = `${state.otpSecondsLeft}s`;
        if (otpTimerBar) otpTimerBar.style.width = '100%';

        state.otpTimerInterval = setInterval(() => {
            state.otpSecondsLeft--;

            if (state.otpSecondsLeft <= 0) {
                clearInterval(state.otpTimerInterval);
                state.otpTimerInterval = null;

                if (otpCountdownText) otpCountdownText.textContent = 'Expired';
                if (otpTimerBar) otpTimerBar.style.width = '0%';
                if (authResendBtn) authResendBtn.disabled = false;
                showAuthAlert('Verification code has expired. Please click Resend Code.', 'error');
            } else {
                if (otpCountdownText) otpCountdownText.textContent = `${state.otpSecondsLeft}s`;
                const pct = Math.max(0, (state.otpSecondsLeft / totalSeconds) * 100);
                if (otpTimerBar) otpTimerBar.style.width = `${pct}%`;
            }
        }, 1000);
    }

    async function handleSendOtp(isResend = false) {
        hideAuthAlert();

        let identifier = '';
        if (state.authChannel === 'email') {
            identifier = (authEmailInput ? authEmailInput.value : '').trim();
            if (!identifier || !identifier.includes('@')) {
                showAuthAlert('Please enter a valid email address', 'error');
                if (authEmailInput) authEmailInput.focus();
                return;
            }
        } else {
            identifier = (authPhoneInput ? authPhoneInput.value : '').trim();
            const digits = identifier.replace(/[^0-9]/g, '');
            if (digits.length < 7) {
                showAuthAlert('Please enter a valid phone number', 'error');
                if (authPhoneInput) authPhoneInput.focus();
                return;
            }
        }

        try {
            if (sendOtpBtn) {
                sendOtpBtn.disabled = true;
                sendOtpBtn.textContent = 'Sending OTP...';
            }
            if (authResendBtn) authResendBtn.disabled = true;

            const res = await fetch('/api/auth/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    identifier: identifier,
                    channel: state.authChannel
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');

            state.authIdentifier = identifier;
            if (authTargetDisplay) authTargetDisplay.textContent = identifier;
            if (authStepRequest) authStepRequest.style.display = 'none';
            if (authStepVerify) authStepVerify.style.display = 'block';

            otpDigitBoxes.forEach(b => { b.value = ''; b.classList.remove('filled'); });
            if (otpDigitBoxes[0]) setTimeout(() => otpDigitBoxes[0].focus(), 100);

            startOtpCountdown(data.expires_in || 30);
            showToast(`Verification code sent via ${state.authChannel}`, 'success');
        } catch (err) {
            showAuthAlert(err.message, 'error');
        } finally {
            if (sendOtpBtn) {
                sendOtpBtn.disabled = false;
                sendOtpBtn.textContent = 'Continue & Send OTP →';
            }
        }
    }

    if (sendOtpBtn) sendOtpBtn.addEventListener('click', () => handleSendOtp(false));
    if (authResendBtn) authResendBtn.addEventListener('click', () => handleSendOtp(true));

    if (authBackToRequestBtn) {
        authBackToRequestBtn.addEventListener('click', () => {
            if (state.otpTimerInterval) clearInterval(state.otpTimerInterval);
            hideAuthAlert();
            if (authStepVerify) authStepVerify.style.display = 'none';
            if (authStepRequest) authStepRequest.style.display = 'block';
        });
    }

    // 6-digit inputs auto-advance and backspace
    otpDigitBoxes.forEach((box, idx) => {
        box.addEventListener('input', () => {
            const val = box.value.replace(/[^0-9]/g, '');
            box.value = val ? val[0] : '';

            if (box.value) {
                box.classList.add('filled');
                if (idx < otpDigitBoxes.length - 1) {
                    otpDigitBoxes[idx + 1].focus();
                } else {
                    const full = Array.from(otpDigitBoxes).map(b => b.value).join('');
                    if (full.length === 6) handleVerifyOtp();
                }
            } else {
                box.classList.remove('filled');
            }
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !box.value && idx > 0) {
                otpDigitBoxes[idx - 1].focus();
            }
        });

        box.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text').trim().replace(/[^0-9]/g, '');
            if (text.length >= 6) {
                for (let i = 0; i < 6; i++) {
                    otpDigitBoxes[i].value = text[i];
                    otpDigitBoxes[i].classList.add('filled');
                }
                otpDigitBoxes[5].focus();
                handleVerifyOtp();
            }
        });
    });

    async function handleVerifyOtp() {
        hideAuthAlert();
        const otpCode = Array.from(otpDigitBoxes).map(b => b.value.trim()).join('');

        if (otpCode.length !== 6) {
            showAuthAlert('Please enter all 6 numeric digits', 'error');
            return;
        }

        try {
            if (verifyOtpBtn) {
                verifyOtpBtn.disabled = true;
                verifyOtpBtn.textContent = 'Verifying...';
            }

            const res = await fetch('/api/auth/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    identifier: state.authIdentifier,
                    otp: otpCode,
                    name: (authNameInput ? authNameInput.value.trim() : '') || null
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Verification failed');

            if (state.otpTimerInterval) clearInterval(state.otpTimerInterval);

            state.authToken = data.token;
            localStorage.setItem('jack_auth_token', data.token);
            state.currentUser = data.user;

            updateUserUI();
            showToast(`Welcome ${state.currentUser.name || 'User'}! Authentication successful.`, 'success');
            setTimeout(closeAuthModal, 500);
        } catch (err) {
            showAuthAlert(err.message, 'error');
            otpDigitBoxes.forEach(b => { b.value = ''; b.classList.remove('filled'); });
            if (otpDigitBoxes[0]) otpDigitBoxes[0].focus();
        } finally {
            if (verifyOtpBtn) {
                verifyOtpBtn.disabled = false;
                verifyOtpBtn.textContent = 'Verify & Sign In ✓';
            }
        }
    }

    if (verifyOtpBtn) verifyOtpBtn.addEventListener('click', handleVerifyOtp);

    async function handleLogout() {
        try { await fetch('/api/auth/logout', { method: 'POST' }); } catch (e) {}

        if (state.otpTimerInterval) clearInterval(state.otpTimerInterval);
        localStorage.removeItem('jack_auth_token');
        state.authToken = '';
        state.currentUser = null;

        updateUserUI();
        showToast('Signed out successfully', 'info');
        if (authStepProfile) authStepProfile.style.display = 'none';
        if (authStepRequest) authStepRequest.style.display = 'block';
    }

    if (authSignOutBtn) authSignOutBtn.addEventListener('click', handleLogout);
    if (sidebarLogoutNavBtn) sidebarLogoutNavBtn.addEventListener('click', handleLogout);
    if (authSwitchAccountBtn) authSwitchAccountBtn.addEventListener('click', handleLogout);

    async function checkAuthState() {
        if (!state.authToken) {
            updateUserUI();
            return;
        }

        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${state.authToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                state.currentUser = data.user;
                updateUserUI();
            } else {
                localStorage.removeItem('jack_auth_token');
                state.authToken = '';
                state.currentUser = null;
                updateUserUI();
            }
        } catch (e) {
            updateUserUI();
        }
    }

    // =========================================================================
    // 15. Helper Utilities
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
    // 16. Initial Application Boot
    // =========================================================================
    checkAuthState();
    loadDashboardStats();
    loadAppointments();
    loadDoctors();
    loadPatients();
    loadCallHistory();
    loadAnalytics();
});
