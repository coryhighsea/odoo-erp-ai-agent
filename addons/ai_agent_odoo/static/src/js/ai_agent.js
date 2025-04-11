/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

class AIAgentWidget extends Component {
    setup() {
        this.state = useState({
            messages: [],
            inputMessage: "",
            isOpen: false,
        });
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    }

    async sendMessage() {
        if (!this.state.inputMessage.trim()) return;

        const message = this.state.inputMessage;
        this.state.messages.push({ content: message, isUser: true });
        this.state.inputMessage = "";

        try {
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message: message }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.state.messages.push({ content: data.response, isUser: false });
        } catch (error) {
            this.notification.add("Error sending message: " + error.message, { type: "danger" });
            console.error("Error:", error);
        }
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
    }
}

AIAgentWidget.template = "ai_agent_odoo.AIAgentWidget";
AIAgentWidget.props = {};

// Add the widget to the systray
registry.category("systray").add("ai_agent.AIAgentWidget", {
    Component: AIAgentWidget,
}); 