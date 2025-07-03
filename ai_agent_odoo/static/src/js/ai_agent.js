/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onMounted} from "@odoo/owl";

// Password modal component
export class PasswordModal extends Component {
    setup() {
        this.state = useState({ password: "" });
    }
    onInput(ev) {
        this.state.password = ev.target.value;
    }
    onOk() {
        this.props.onSubmit(this.state.password);
    }
    onCancel() {
        this.props.onCancel();
    }
}
PasswordModal.template = "ai_agent_odoo.PasswordModal";
PasswordModal.props = ["onSubmit", "onCancel"];

class AIAgentSystray extends Component {
    setup() {
        this.state = useState({
            messages: [],
            inputMessage: "",
            isOpen: false,
            isLoading: false,
            conversationHistory: [],
            odooPassword: null, // Store password in memory only
            showPasswordModal: false,
            passwordPromise: null,
        });
        onMounted(() => {
            if (this.state.isOpen) {
                this.scrollToBottom();
            }
        });
    }

    async promptForPassword() {
        this.state.showPasswordModal = true;
        return new Promise((resolve, reject) => {
            this.state.passwordPromise = { resolve, reject };
        });
    }

    onPasswordSubmit(password) {
        this.state.odooPassword = password;
        this.state.showPasswordModal = false;
        if (this.state.passwordPromise) {
            this.state.passwordPromise.resolve(password);
            this.state.passwordPromise = null;
        }
    }
    onPasswordCancel() {
        this.state.showPasswordModal = false;
        if (this.state.passwordPromise) {
            this.state.passwordPromise.reject(new Error("Password is required to use the AI agent."));
            this.state.passwordPromise = null;
        }
    }

    async sendMessage() {
        if (!this.state.inputMessage.trim() || this.state.isLoading) return;

        const message = this.state.inputMessage;
        this.state.messages.push({ content: message, isUser: true, isHtml: false });
        this.state.inputMessage = "";
        this.state.isLoading = true;

        try {
            // Prepare conversation history
            const conversationHistory = this.state.conversationHistory.map(msg => ({
                role: msg.isUser ? "user" : "assistant",
                content: msg.content
            }));

            // Add current message to history
            conversationHistory.push({
                role: "user",
                content: message
            });

            // Use rpc to get the configuration from the Odoo backend.
            const config = await rpc("/ai_agent_odoo/get_config", {});
            if (!config || !config.ai_agent_url || !config.ai_agent_api_key || !config.db || !config.login) {
                throw new Error("AI Agent URL or Odoo credentials are not configured in Odoo's System Parameters.");
            }

            // Prompt for password if not already set
            let password = this.state.odooPassword;
            if (!password) {
                password = await this.promptForPassword();
            }

            // Compose the payload for the new endpoint
            const payload = {
                odoo_credentials: {
                    url: window.location.origin, // Use current Odoo instance URL
                    db: config.db,
                    username: config.login,
                    password: password,
                },
                prompt: message,
                conversation_history: conversationHistory,
            };

            // Make the call to your Python AI service (new endpoint)
            const response = await fetch(`${config.ai_agent_url}/api/v1/agent/invoke`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "api-Key": config.ai_agent_api_key },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("API error details:", errorData);
                throw new Error(JSON.stringify(errorData));
            }

            const data = await response.json();

            // Render AI response as HTML (sanitize only, since LLM returns HTML)
            const html = window.DOMPurify.sanitize(data.response);
            this.state.messages.push({ content: html, isUser: false, isHtml: true });
            this.state.conversationHistory = conversationHistory.concat([{
                role: "assistant",
                content: data.response
            }]);

            // Scroll to bottom of chat after DOM update
            setTimeout(() => this.scrollToBottom(), 0);
        } catch (error) {
            const errorMessage = "Error: " + error.message;
            this.state.messages.push({ content: errorMessage, isUser: false, isHtml: false });
            console.error("Error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    handleKeyPress(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    scrollToBottom() {
        if (!this.el) return;
        const chatContainer = this.el.querySelector(".o_chat_container");
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            // Use setTimeout to ensure the DOM is updated before scrolling
            setTimeout(() => this.scrollToBottom(), 0);
        }
    }
}

AIAgentSystray.template = "ai_agent_odoo.AIAgentSystray";
AIAgentSystray.props = {};
AIAgentSystray.components = { PasswordModal };

// Add the widget to the systray
registry.category("systray").add("ai_agent_odoo.AIAgentSystray", {
    Component: AIAgentSystray,
});