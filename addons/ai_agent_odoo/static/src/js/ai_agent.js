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
        this.action = useService("action");
        
        // Use Owl's event handling
        this.handleOdooRecordClick = this.handleOdooRecordClick.bind(this);
        
        onMounted(() => {
            if (this.state.isOpen) {
                this.scrollToBottom();
            }
        });
    }

    // Add function to safely escape HTML
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Add function to detect and create Odoo record links
    createOdooRecordLinks(text) {
        // Define patterns for different Odoo record types
        const patterns = [
            {
                regex: /(workorder|WO)\s*#?(\d+)/gi,
                model: 'mrp.workorder',
                display: 'Work Order'
            },
            {
                regex: /(manufacturing order|MO)\s*#?(\d+)/gi,
                model: 'mrp.production',
                display: 'Manufacturing Order'
            },
            {
                regex: /(lead|opportunity)\s*#?(\d+)/gi,
                model: 'crm.lead',
                display: 'Lead'
            },
            {
                regex: /(contact|partner)\s*#?(\d+)/gi,
                model: 'res.partner',
                display: 'Contact'
            },
            {
                regex: /(sale order|SO)\s*#?(\d+)/gi,
                model: 'sale.order',
                display: 'Sale Order'
            },
            {
                regex: /(purchase order|PO)\s*#?(\d+)/gi,
                model: 'purchase.order',
                display: 'Purchase Order'
            },
            {
                regex: /(invoice)\s*#?(\d+)/gi,
                model: 'account.move',
                display: 'Invoice'
            }
        ];

        // Split the text into parts that might contain links and parts that don't
        let parts = [text];
        
        // Process each pattern
        patterns.forEach(pattern => {
            const newParts = [];
            parts.forEach(part => {
                if (part.includes('<') || part.includes('>')) {
                    // Skip parts that already contain HTML
                    newParts.push(part);
                } else {
                    // Split the part into segments that match the pattern and segments that don't
                    const segments = part.split(pattern.regex);
                    for (let i = 0; i < segments.length; i++) {
                        if (i % 3 === 0) {
                            // This is a non-matching segment, no need to escape as it's already escaped
                            newParts.push(segments[i]);
                        } else if (i % 3 === 1) {
                            // This is the prefix (group 1)
                            const id = segments[i + 1]; // The ID (group 2)
                            const displayText = `${pattern.display} #${id}`;
                            newParts.push(`<a href="#" class="odoo-record-link" data-model="${pattern.model}" data-id="${id}">${displayText}</a>`);
                            i++; // Skip the ID since we've processed it
                        }
                    }
                }
            });
            parts = newParts;
        });

        // Join all parts together
        return parts.join('');
    }

    // Add function to handle Odoo record link clicks
    async handleOdooRecordClick(event) {
        if (event.target.classList.contains('odoo-record-link')) {
            event.preventDefault();
            const model = event.target.dataset.model;
            const id = parseInt(event.target.dataset.id);
            
            try {
                // Verify the record exists before opening
                const exists = await this.rpc(`/web/dataset/call_kw/${model}/search_count`, {
                    model: model,
                    method: 'search_count',
                    args: [[['id', '=', id]]],
                    kwargs: {}
                });

                if (exists) {
                    // Use Odoo's action service to open the record
                    this.action.doAction({
                        type: 'ir.actions.act_window',
                        res_model: model,
                        res_id: id,
                        views: [[false, 'form']],
                        target: 'current'
                    });
                } else {
                    this.notification.add(`Record not found: ${model} #${id}`, { type: "warning" });
                }
            } catch (error) {
                console.error("Error opening record:", error);
                this.notification.add("Error opening record: " + error.message, { type: "danger" });
            }
        }
    }

    async sendMessage() {
        if (!this.state.inputMessage.trim() || this.state.isLoading) return;

        const message = this.state.inputMessage;
        // Only escape HTML for user messages
        this.state.messages.push({ content: this.escapeHtml(message), isUser: true });
        this.state.inputMessage = "";
        this.state.isLoading = true;

        try {
            // Prepare conversation history with unescaped content
            const conversationHistory = this.state.conversationHistory.map(msg => ({
                role: msg.isUser ? "user" : "assistant",
                content: msg.isUser ? this.escapeHtml(msg.content) : msg.content
            }));

            // Add current message to history (escaped for user messages)
            conversationHistory.push({
                role: "user",
                content: this.escapeHtml(message)
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
            
            // Format the response for better readability
            let formattedResponse = this.formatResponse(data.response);
            
            // Create clickable Odoo record links
            formattedResponse = this.createOdooRecordLinks(formattedResponse);
            
            // Check if the response contains a database operation
            if (formattedResponse.includes("DATABASE_OPERATION:")) {
                try {
                    // Extract the operation JSON
                    const operationStr = formattedResponse.split("DATABASE_OPERATION:")[1].trim().split('\n')[0];
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
                    this.action.doAction({
                        type: 'ir.actions.client',
                        tag: 'reload',
                    });
                } catch (error) {
                    console.error("Error executing database operation:", error);
                    this.notification.add("Error executing operation: " + error.message, { type: "danger" });
                }
            }
            
            // Add AI response to messages and history (unescaped)
            this.state.messages.push({ content: formattedResponse, isUser: false });
            this.state.conversationHistory = conversationHistory.concat([{
                role: "assistant",
                content: formattedResponse
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

    formatResponse(text) {
        // Split text into lines
        let lines = text.split('\n');
        
        // Process each line
        lines = lines.map(line => {
            // Handle special cases first
            // Preserve URLs and email addresses
            line = line.replace(/(https?:\/\/[^\s]+|[\w.-]+@[\w.-]+\.\w+)/g, 'URL_EMAIL_PLACEHOLDER_$1');
            
            // Preserve decimal numbers
            line = line.replace(/(\d+\.\d+)/g, 'DECIMAL_PLACEHOLDER_$1');
            
            // Preserve dates with periods
            line = line.replace(/(\d{1,2}\.\d{1,2}\.\d{2,4})/g, 'DATE_PLACEHOLDER_$1');
            
            // Preserve common abbreviations
            line = line.replace(/(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|etc\.|e\.g\.|i\.e\.)/g, 'ABBR_PLACEHOLDER_$1');
            
            // Add line breaks after sentences
            line = line.replace(/([.!?])\s+/g, '$1\n');
            
            // Add line breaks after colons
            line = line.replace(/:\s+/g, ':\n');
            
            // Add line breaks after numbered lists
            line = line.replace(/(\d+\.)\s+/g, '\n$1 ');
            
            // Add line breaks after bullet points
            line = line.replace(/([-•])\s+/g, '\n$1 ');
            
            // Restore placeholders
            line = line.replace(/URL_EMAIL_PLACEHOLDER_/g, '');
            line = line.replace(/DECIMAL_PLACEHOLDER_/g, '');
            line = line.replace(/DATE_PLACEHOLDER_/g, '');
            line = line.replace(/ABBR_PLACEHOLDER_/g, '');
            
            return line;
        });
        
        // Join lines and clean up spacing
        let formattedText = lines.join('\n')
            .replace(/\n\n+/g, '\n\n')  // Remove excessive line breaks
            .replace(/\n\s*\n/g, '\n\n')  // Clean up spaces between paragraphs
            .trim();  // Remove leading/trailing whitespace
        
        return formattedText;
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