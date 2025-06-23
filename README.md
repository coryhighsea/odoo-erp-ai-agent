# AI Agent Chatbot for Odoo

Transform your Odoo experience with intelligent AI-powered assistance.

## 🚀 Getting Started

### 1. Environment Variables

Before running the app, you need to set up your environment variables. Copy the example file and fill in your credentials:

```sh
cp .env.example .env
```

Edit the `.env` file and provide the following values:

- `ODOO_URL` - The URL of your Odoo instance (e.g., http://localhost:8069)
- `ODOO_DB` - Your Odoo database name
- `ODOO_USERNAME` - Your Odoo username
- `ODOO_PASSWORD` - Your Odoo password
- `ANTHROPIC_API_KEY` - Your Anthropic API key for AI chat

> **Note:** The app will not start unless all required variables are set.

### 2. How the App Works

The AI Agent Chatbot for Odoo connects to your Odoo database and provides intelligent, conversational assistance for managing your business data. It uses the Anthropic API for natural language understanding and interacts with Odoo via XML-RPC.

#### Core Features
- **Intelligent Database Reading:** Ask questions about your Odoo data and get real-time answers.
- **Database Editing & Updates:** Update records (like sales orders or customer info) through natural conversation.
- **Sales Order Management:** List, view, and modify sales orders using plain English.
- **Intelligent Suggestions:** Get proactive recommendations for follow-ups and workflow improvements.
- **Odoo UI Guidance:** Learn how to perform actions in Odoo with step-by-step explanations.

#### Example Workflows
- **Sales Order Management:**
  1. "List our current sales orders"
  2. "List the items in S00069"
  3. "Update item office chair to 3 quantity from 2"
  4. Refresh the Sales Order page in Odoo to see changes
- **Customer Follow-up:**
  1. "What actions should I take for customer follow-ups?"
  2. Get AI-driven recommendations
  3. Implement actions through the AI agent

#### Benefits
- Save time by using conversation instead of menus
- Reduce errors with AI validation
- Gain insights and suggestions based on your data
- Learn Odoo features through guided explanations
- Use plain English to interact with your ERP

#### Technical Note
After the AI agent makes database changes, refresh the relevant Odoo pages to see updates reflected in the UI.

---

For more details, see the in-app help or the description in `static/description/index.html`.
