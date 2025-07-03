/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onMounted } from "@odoo/owl";

class AIAgentSystray extends Component {
    setup() {
        this.state = useState({
            messages: [],
            inputMessage: "",
            isOpen: false,
            isLoading: false,
            conversationHistory: []
        });
        onMounted(() => {
            if (this.state.isOpen) {
                this.scrollToBottom();
            }
        });
    }

    async sendMessage() {
        if (!this.state.inputMessage.trim() || this.state.isLoading) return;

        const message = this.state.inputMessage;
        this.state.messages.push({ content: message, isUser: true });
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
            const config = await rpc("/ai_agent/get_config", {});
            if (!config || !config.ai_agent_url || !config.ai_agent_api_key) {
                throw new Error("AI Agent URL is not configured in Odoo's System Parameters.");
            }

            // Make the call to your Python AI service
            const response = await fetch(`${config.ai_agent_url}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "api-Key": config.ai_agent_api_key },
                body: JSON.stringify({
                    message: message,
                    conversation_history: conversationHistory,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();

            // Add AI response to messages and history
            this.state.messages.push({ content: data.response, isUser: false });
            this.state.conversationHistory = conversationHistory.concat([{
                role: "assistant",
                content: data.response
            }]);

            // Scroll to bottom of chat
            this.scrollToBottom();
        } catch (error) {
            const errorMessage = "Error: " + error.message;
            this.state.messages.push({ content: errorMessage, isUser: false });
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

AIAgentSystray.template = "ai_agent.AIAgentSystray";
AIAgentSystray.props = {};

// Add the widget to the systray
registry.category("systray").add("ai_agent.AIAgentSystray", {
    Component: AIAgentSystray,
});