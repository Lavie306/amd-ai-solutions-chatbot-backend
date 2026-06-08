(function () {
    // Prevent double loading
    if (window.AmdChatbotInitialized) return;
    window.AmdChatbotInitialized = true;

    // Config defaults
    let config = {
        api_host: window.location.origin,
        bot_name: "AMD Assistant",
        welcome_message: "Xin chào! Tôi là trợ lý ảo của AMD AI Solutions. Tôi có thể giúp gì cho bạn?",
        handoff_message: "Cảm ơn bạn đã để lại thông tin. Team AMD sẽ liên hệ trong vòng 24h làm việc.",
        zalo_number: "0901 234 567",
        language: "vi"
    };

    // Load session or generate UUID
    let sessionId = localStorage.getItem("amd_chatbot_session_id");
    if (!sessionId) {
        sessionId = "sess_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
        localStorage.setItem("amd_chatbot_session_id", sessionId);
    }

    // Add FontAwesome for icons
    const fontAwesomeLink = document.createElement("link");
    fontAwesomeLink.rel = "stylesheet";
    fontAwesomeLink.href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css";
    document.head.appendChild(fontAwesomeLink);

    // CSS Styling
    const styles = `
        :root {
            --amd-primary: #2563eb;
            --amd-primary-hover: #1d4ed8;
            --amd-bg-gradient: linear-gradient(135deg, #2563eb, #1d4ed8);
            --amd-gray-light: #f3f4f6;
            --amd-text-dark: #1f2937;
            --amd-text-light: #6b7280;
            --amd-border-radius: 16px;
            --amd-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            --amd-glass-bg: rgba(255, 255, 255, 0.98);
        }

        #amd-chat-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--amd-bg-gradient);
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 999999;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        #amd-chat-fab:hover {
            transform: scale(1.1) rotate(5deg);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6);
        }
        #amd-chat-fab i {
            font-size: 24px;
            transition: transform 0.3s;
        }
        #amd-chat-fab.active i {
            transform: rotate(90deg);
        }
        #amd-chat-fab .badge {
            position: absolute;
            top: -2px;
            right: -2px;
            width: 14px;
            height: 14px;
            background: #ef4444;
            border-radius: 50%;
            border: 2px solid white;
            animation: pulse-badge 2s infinite;
        }

        @keyframes pulse-badge {
            0% { transform: scale(0.9); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.8; }
            100% { transform: scale(0.9); opacity: 1; }
        }

        #amd-chat-window {
            position: fixed;
            bottom: 96px;
            right: 24px;
            width: 380px;
            height: 600px;
            max-height: calc(100vh - 120px);
            border-radius: var(--amd-border-radius);
            background: var(--amd-glass-bg);
            box-shadow: var(--amd-shadow);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            z-index: 999998;
            opacity: 0;
            transform: translateY(20px) scale(0.95);
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(229, 231, 235, 0.5);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #amd-chat-window.active {
            opacity: 1;
            transform: translateY(0) scale(1);
            pointer-events: auto;
        }

        .amd-chat-header {
            background: var(--amd-bg-gradient);
            color: white;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .amd-chat-header-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .amd-chat-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            border: 2px solid rgba(255, 255, 255, 0.4);
        }
        .amd-chat-title-group {
            display: flex;
            flex-direction: column;
        }
        .amd-chat-title {
            font-weight: 600;
            font-size: 16px;
            margin: 0;
            line-height: 1.2;
        }
        .amd-chat-subtitle {
            font-size: 12px;
            opacity: 0.85;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 2px;
        }
        .amd-chat-online-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10b981;
        }
        .amd-chat-close {
            color: rgba(255, 255, 255, 0.8);
            cursor: pointer;
            font-size: 20px;
            transition: color 0.2s;
            border: none;
            background: transparent;
        }
        .amd-chat-close:hover {
            color: white;
        }

        .amd-chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: #f9fafb;
        }

        .amd-msg-wrapper {
            display: flex;
            flex-direction: column;
            max-width: 85%;
        }
        .amd-msg-wrapper.user {
            align-self: flex-end;
            align-items: flex-end;
        }
        .amd-msg-wrapper.bot {
            align-self: flex-start;
            align-items: flex-start;
        }
        .amd-msg-bubble {
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.5;
            word-wrap: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .amd-msg-wrapper.user .amd-msg-bubble {
            background: var(--amd-primary);
            color: white;
            border-bottom-right-radius: 4px;
        }
        .amd-msg-wrapper.bot .amd-msg-bubble {
            background: white;
            color: var(--amd-text-dark);
            border-bottom-left-radius: 4px;
            border: 1px solid #e5e7eb;
        }
        .amd-msg-timestamp {
            font-size: 10px;
            color: var(--amd-text-light);
            margin-top: 4px;
            padding: 0 4px;
        }

        .amd-chat-input-area {
            padding: 14px 18px;
            background: white;
            border-top: 1px solid #f3f4f6;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .amd-chat-input {
            flex: 1;
            border: 1px solid #e5e7eb;
            outline: none;
            padding: 10px 14px;
            border-radius: 24px;
            font-size: 14px;
            transition: all 0.2s;
            font-family: inherit;
        }
        .amd-chat-input:focus {
            border-color: var(--amd-primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        .amd-chat-send {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: var(--amd-primary);
            color: white;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .amd-chat-send:hover {
            background: var(--amd-primary-hover);
            transform: scale(1.05);
        }
        .amd-chat-send:active {
            transform: scale(0.95);
        }
        .amd-chat-send:disabled {
            background: #cbd5e1;
            cursor: not-allowed;
            transform: none;
        }

        .amd-typing-bubble {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 12px 18px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            border: 1px solid #e5e7eb;
            align-self: flex-start;
        }
        .amd-typing-dot {
            width: 6px;
            height: 6px;
            background: #9ca3af;
            border-radius: 50%;
            animation: bounce-dot 1.4s infinite ease-in-out both;
        }
        .amd-typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .amd-typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce-dot {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1.0); }
        }

        .amd-handoff-card {
            margin-top: 8px;
            background: #eff6ff;
            border: 1px dashed #bfdbfe;
            border-radius: 12px;
            padding: 12px;
            font-size: 13px;
            color: #1e40af;
            display: flex;
            flex-direction: column;
            gap: 8px;
            width: 100%;
        }
        .amd-handoff-btn {
            background: #2563eb;
            color: white !important;
            padding: 8px 12px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            font-weight: 500;
            transition: background 0.2s;
            border: none;
            cursor: pointer;
        }
        .amd-handoff-btn:hover {
            background: #1d4ed8;
        }

        @media (max-width: 600px) {
            #amd-chat-window {
                bottom: 0;
                right: 0;
                width: 100%;
                height: 100%;
                max-height: 100%;
                border-radius: 0;
            }
            #amd-chat-fab {
                bottom: 16px;
                right: 16px;
            }
        }
    `;

    // Inject CSS
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    // Create DOM Elements
    const body = document.body;

    const fab = document.createElement("div");
    fab.id = "amd-chat-fab";
    fab.innerHTML = `<i class="fa-solid fa-comments"></i><div class="badge" id="amd-chat-badge" style="display:none;"></div>`;
    body.appendChild(fab);

    const chatWindow = document.createElement("div");
    chatWindow.id = "amd-chat-window";
    chatWindow.innerHTML = `
        <div class="amd-chat-header">
            <div class="amd-chat-header-info">
                <div class="amd-chat-avatar" id="amd-chat-avatar-text">A</div>
                <div class="amd-chat-title-group">
                    <h3 class="amd-chat-title" id="amd-chat-header-name">AMD Assistant</h3>
                    <span class="amd-chat-subtitle">
                        <span class="amd-chat-online-dot"></span> Đang hoạt động
                    </span>
                </div>
            </div>
            <button class="amd-chat-close" id="amd-chat-close-btn">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="amd-chat-messages" id="amd-chat-msg-list"></div>
        <div class="amd-chat-input-area">
            <input type="text" class="amd-chat-input" id="amd-chat-input-field" placeholder="Nhập tin nhắn..." autocomplete="off">
            <button class="amd-chat-send" id="amd-chat-send-btn" disabled>
                <i class="fa-solid fa-paper-plane"></i>
            </button>
        </div>
    `;
    body.appendChild(chatWindow);

    // DOM References
    const badge = document.getElementById("amd-chat-badge");
    const msgList = document.getElementById("amd-chat-msg-list");
    const inputField = document.getElementById("amd-chat-input-field");
    const sendBtn = document.getElementById("amd-chat-send-btn");
    const closeBtn = document.getElementById("amd-chat-close-btn");
    const headerName = document.getElementById("amd-chat-header-name");
    const avatarText = document.getElementById("amd-chat-avatar-text");

    let isChatOpen = false;
    let welcomeShown = false;

    // Helper functions
    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function parseMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    // Toggle Chat
    function toggleChat() {
        isChatOpen = !isChatOpen;
        if (isChatOpen) {
            chatWindow.classList.add("active");
            fab.classList.add("active");
            fab.innerHTML = `<i class="fa-solid fa-xmark"></i>`;
            badge.style.display = "none";
            
            // Show welcome message if list is empty
            if (msgList.children.length === 0 && !welcomeShown) {
                appendMessage("bot", config.welcome_message);
                welcomeShown = true;
            }
            inputField.focus();
        } else {
            chatWindow.classList.remove("active");
            fab.classList.remove("active");
            fab.innerHTML = `<i class="fa-solid fa-comments"></i><div class="badge" id="amd-chat-badge" style="display:none;"></div>`;
        }
    }

    // Append Message to UI
    function appendMessage(sender, text, timestamp = new Date()) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("amd-msg-wrapper", sender);

        const bubble = document.createElement("div");
        bubble.classList.add("amd-msg-bubble");
        bubble.innerHTML = parseMarkdown(text);
        wrapper.appendChild(bubble);

        const timeSpan = document.createElement("span");
        timeSpan.classList.add("amd-msg-timestamp");
        timeSpan.innerText = formatTime(timestamp);
        wrapper.appendChild(timeSpan);

        msgList.appendChild(wrapper);
        msgList.scrollTop = msgList.scrollHeight;

        // Custom handoff banner detection
        if (sender === "bot" && (text.includes(config.zalo_number) || text.toLowerCase().includes("zalo"))) {
            appendHandoffCard();
        }
    }

    // Append Handoff card with direct Zalo link
    function appendHandoffCard() {
        const card = document.createElement("div");
        card.classList.add("amd-handoff-card");
        card.innerHTML = `
            <div>Bạn muốn trò chuyện trực tiếp qua Zalo hoặc nhận báo giá nhanh?</div>
            <a href="https://zalo.me/${config.zalo_number.replace(/\s+/g, '')}" target="_blank" class="amd-handoff-btn">
                <i class="fa-solid fa-message"></i> Nhắn Zalo: ${config.zalo_number}
            </a>
        `;
        msgList.appendChild(card);
        msgList.scrollTop = msgList.scrollHeight;
    }

    // Append typing indicator
    function showTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.id = "amd-typing-indicator";
        indicator.classList.add("amd-typing-bubble");
        indicator.innerHTML = `
            <div class="amd-typing-dot"></div>
            <div class="amd-typing-dot"></div>
            <div class="amd-typing-dot"></div>
        `;
        msgList.appendChild(indicator);
        msgList.scrollTop = msgList.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById("amd-typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    // Fetch config
    async function loadConfig() {
        try {
            const res = await fetch(`${config.api_host}/api/settings/public/config`);
            if (res.ok) {
                const data = await res.json();
                config.bot_name = data.bot_name || config.bot_name;
                config.welcome_message = data.welcome_message || config.welcome_message;
                config.handoff_message = data.handoff_message || config.handoff_message;
                config.zalo_number = data.zalo_number || config.zalo_number;
                config.language = data.language || config.language;
                
                // Update UI elements
                headerName.innerText = config.bot_name;
                avatarText.innerText = config.bot_name.charAt(0);
            }
        } catch (err) {
            console.warn("Failed to load runtime configurations, using default settings.", err);
        }
    }

    // Send Message to API
    async function sendMessage() {
        const messageText = inputField.value.trim();
        if (!messageText) return;

        // Display user message
        appendMessage("user", messageText);
        inputField.value = "";
        sendBtn.disabled = true;

        showTypingIndicator();

        try {
            const response = await fetch(`${config.api_host}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: messageText
                })
            });

            removeTypingIndicator();

            if (response.ok) {
                const data = await response.json();
                appendMessage("bot", data.reply);
            } else {
                appendMessage("bot", "Rất tiếc, đã xảy ra lỗi kết nối. Vui lòng thử lại sau.");
            }
        } catch (err) {
            removeTypingIndicator();
            appendMessage("bot", "Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.");
            console.error("Chat API error:", err);
        }
    }

    // Event Listeners
    fab.addEventListener("click", toggleChat);
    closeBtn.addEventListener("click", toggleChat);

    inputField.addEventListener("input", function() {
        sendBtn.disabled = inputField.value.trim() === "";
    });

    inputField.addEventListener("keypress", function(e) {
        if (e.key === "Enter" && inputField.value.trim() !== "") {
            sendMessage();
        }
    });

    sendBtn.addEventListener("click", sendMessage);

    // Initial setup
    loadConfig();
})();
