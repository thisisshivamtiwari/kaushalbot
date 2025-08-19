# 🤖 Kaushal – AI LinkedIn Growth Companion (Telegram Bot)

Kaushal is a conversational Telegram bot that helps you create high‑quality LinkedIn content. It connects to your LinkedIn account (OIDC), drafts posts using Google Gemini, refines them from your follow‑ups, and stores drafts in MongoDB.

## ✨ What You Get
- **Conversational content creation**: Just describe what you need; Kaushal drafts your LinkedIn post.
- **Smart refinement**: Send follow‑ups like “shorter”, “more casual”, or “from a student perspective” and get an updated draft (no context lost).
- **Photo → Post**: Send a photo with a caption; Kaushal turns it into a LinkedIn‑ready post.
- **Time‑based greeting**: Welcomes connected users with Good morning/afternoon/evening and guidance.
- **LinkedIn OIDC connect**: Modern, secure authentication.
- **MongoDB drafts**: Every AI draft is saved as a draft in MongoDB for your records.

## 🧱 Architecture (high‑level)
- **bot_ai.py**: Telegram entrypoint; conversational flow; inline buttons for status/help.
- **ai_content_engine.py**: Orchestrator + Workers (Create, Optimize, Refine, Tips) powered by LangChain + Google Gemini.
- **linkedin_oauth.py**: LinkedIn OIDC (auth URL, token exchange, userinfo, connection status).
- **database.py**: MongoDB client and helpers (`save_user`, `save_post`, `get_user_posts`).
- **config.py**: Loads environment variables.

## 📦 Requirements
- Python 3.9+
- Telegram Bot Token
- MongoDB Atlas (or compatible URI)
- LinkedIn Developer app with OIDC
- Google API key (Gemini)

## ⚙️ Installation
```bash
# 1) Clone
git clone <your-repo-url>
cd kaushal

# 2) Install deps
pip install -r requirements.txt
```

`requirements.txt` (core):
- `python-telegram-bot==21.6`
- `langchain`, `langchain-google-genai`, `google-generativeai`
- `pymongo`, `python-dotenv`, `requests`, `PyJWT`

## 🔐 Environment Variables (.env)
Create a `.env` file in the project root:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
MONGODB_URI=your_mongodb_uri
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/linkedin/callback
GOOGLE_API_KEY=your_google_gemini_api_key
DEBUG=False
```

## 🔗 LinkedIn (OIDC) Setup
- In LinkedIn Developer Portal:
  - Create an app
  - Add product: “Sign in with LinkedIn using OpenID Connect”
  - Add a redirect URL matching your `.env` (e.g., `http://localhost:8000/linkedin/callback`)
- Scopes used: `openid profile email`

## 🧠 Google Gemini Setup
- Go to Google AI Studio and create an API key
- Ensure Gemini is enabled
- Put the key in `.env` as `GOOGLE_API_KEY`

## 🗄️ MongoDB Setup
- Create a free Atlas cluster
- Get the connection string for a database (e.g., `kaushal_bot`)
- Put it in `.env` as `MONGODB_URI`

## ▶️ Run the Bot
```bash
python bot_ai.py
```
You should see logs indicating the bot started and polling updates.

## 📱 Use It (Conversational Flow)
1. In Telegram, open your bot and send `/start`.
2. If you’re not connected yet, use the **Connect LinkedIn** button.
3. Once connected, just type what you need. Examples:
   - “Write a LinkedIn post that it was great to attend a fresher’s party in IIT Madras”
   - “Make it shorter and more casual”
   - “From a student perspective”
   - “Create a post about launching our new feature today”
4. To get a fresh variant, reply: **“regenerate”**.
5. Send a photo with a caption to generate a post from it.

### What the bot does
- Saves each AI draft to MongoDB (status `draft`).
- Greets you once after connecting (Good morning/afternoon/evening).
- Remembers your last draft and applies refinements to it.

## 🧩 Buttons & Status
- **Check Status**: Shows LinkedIn name/email if connected.
- **Connect LinkedIn**: Hidden when already connected; shows “Already Connected” with options if tapped again.
- **Help**: Quick overview of features.

## 🧪 Refinement Cues (natural language)
- **Length**: “shorter”, “longer”
- **Tone**: “more casual”, “more professional”, “enthusiastic”
- **Perspective**: “from a student perspective”
- You can chain them: “shorter, more casual, student perspective”.

## 🧰 Project Structure
```
kaushal/
├── bot_ai.py               # Telegram bot (conversational flow)
├── ai_content_engine.py    # Orchestrator + Workers (Create/Optimize/Refine)
├── linkedin_oauth.py       # LinkedIn OIDC
├── database.py             # MongoDB helpers
├── config.py               # Env config loader
├── requirements.txt        # Dependencies
└── README.md               # This guide
```

## 🛟 Troubleshooting
- **Bot says Updater error / AttributeError**
  - Ensure `python-telegram-bot==21.6` is installed; re‑install requirements.
- **“Conflict: terminated by other getUpdates request”**
  - Another bot instance is running. Kill with `pkill -f "python bot"` and restart.
- **LinkedIn redirect error**
  - Redirect URI must match exactly what you registered in LinkedIn.
- **Status shows N/A**
  - OIDC userinfo returns name/email; make sure scopes are `openid profile email` and token is valid.
- **Gemini key problems**
  - Set `GOOGLE_API_KEY` in `.env`. Ensure Gemini is enabled in your Google project.
- **MongoDB connection issues**
  - Verify `MONGODB_URI`. Check IP allowlist / network access in Atlas.

## 🔒 Security Notes
- Never commit `.env` or tokens.
- Rotate API keys and LinkedIn credentials if shared.

## 🗺️ Roadmap (suggestions)
- **Inline refiners**: add quick buttons (Shorter, More casual, Student perspective)
- **Style memory**: remember preferred tone/length per user automatically
- **Approve & Post**: in‑bot “Approve & Post to LinkedIn” with confirmation
- **Scheduling**: schedule posts with reminders
- **Analytics**: fetch performance stats (once LinkedIn APIs allow)

## 📄 License
 
## DEVELOPED BY - SHIVAM TIWARI
github.com/thisisshivamtiwari
---
**Built with**: Telegram Bot API, Python, LangChain, Google Gemini, LinkedIn OIDC, MongoDB.
