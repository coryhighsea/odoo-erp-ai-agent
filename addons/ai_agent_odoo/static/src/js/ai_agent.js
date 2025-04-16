/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

class AIAgentForm extends Component {
    setup() {
        this.state = useState({
            messages: [],
            inputMessage: "",
            isOpen: false,
            isLoading: false,
            conversationHistory: []
        });
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
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

            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ 
                    message: message,
                    conversation_history: conversationHistory
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Check if the response contains a database operation
            if (data.response.includes("DATABASE_OPERATION:")) {
                try {
                    // Extract the operation JSON
                    const operationStr = data.response.split("DATABASE_OPERATION:")[1].trim().split('\n')[0];
                    const operation = JSON.parse(operationStr);
                    
                    // Execute the operation through Odoo's RPC
                    await this.rpc(`/web/dataset/call_kw/${operation.model}/${operation.method}`, {
                        model: operation.model,
                        method: operation.method,
                        args: operation.args,
                        kwargs: operation.kwargs
                    });
                    
                    // Show success notification
                    this.notification.add("Operation completed successfully", { type: "success" });
                    
                    // Trigger a reload of the current view to reflect changes
                    this.env.services.action.doAction({
                        type: 'ir.actions.client',
                        tag: 'reload',
                    });
                } catch (error) {
                    console.error("Error executing database operation:", error);
                    this.notification.add("Error executing operation: " + error.message, { type: "danger" });
                }
            }
            
            // Add AI response to messages and history
            this.state.messages.push({ content: data.response, isUser: false });
            this.state.conversationHistory = conversationHistory.concat([{
                role: "assistant",
                content: data.response
            }]);

            // Scroll to bottom of chat
            this.scrollToBottom();
        } catch (error) {
            this.notification.add("Error sending message: " + error.message, { type: "danger" });
            console.error("Error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    extractOdooCommands(text) {
        const commands = [];
        const codeBlockRegex = /```(?:python)?\s*([\s\S]*?)\s*```/g;
        let match;
        
        while ((match = codeBlockRegex.exec(text)) !== null) {
            const code = match[1].trim();
            if (code.startsWith('write(') || code.startsWith('create(')) {
                commands.push(code);
            }
        }
        
        return commands;
    }

    async executeOdooCommand(command) {
        // Extract model and values from the command
        const modelMatch = command.match(/write\('([^']+)'/);
        if (!modelMatch) return;
        
        const model = modelMatch[1];
        const valuesMatch = command.match(/values=\s*({[\s\S]*?})/);
        if (!valuesMatch) return;
        
        try {
            const values = JSON.parse(valuesMatch[1]);
            await this.rpc(`/web/dataset/call_kw/${model}/write`, {
                model: model,
                method: 'write',
                args: [[parseInt(values.id)], values],
                kwargs: {}
            });
        } catch (error) {
            console.error("Error parsing command:", error);
            throw error;
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

AIAgentForm.template = "ai_agent_odoo.AIAgentForm";
AIAgentForm.props = {};

// Add the widget to the systray
registry.category("systray").add("ai_agent.AIAgentForm", {
    Component: AIAgentForm,
}); 