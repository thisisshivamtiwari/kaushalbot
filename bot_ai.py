#!/usr/bin/env python3
"""
Kaushal - LinkedIn Growth Companion Bot
Enhanced with AI Content Creation Engine
"""

import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, DEBUG
from database import db
from linkedin_oauth import linkedin_oauth
from ai_content_engine import create_linkedin_content, get_content_suggestions, ContentTemplates, refine_linkedin_content

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO
)
logger = logging.getLogger(__name__)

# User session storage for content creation
user_sessions = {}

def get_time_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 22:
        return "Good evening"
    return "Hello"

async def maybe_send_connect_greeting(user_id: int, first_name: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If connected and not yet welcomed after connect, greet once
    if not linkedin_oauth.is_connected(user_id):
        return
    user_doc = db.get_user(user_id) or {}
    if user_doc.get('welcomed_after_connect'):
        return
    greeting = get_time_greeting()
    await context.bot.send_message(
        chat_id=user_id,
        text=f"{greeting}, {first_name}! You're connected to LinkedIn. Tell me what you need and I'll craft a LinkedIn-ready post for you.\n\nExamples:\n• 'Create a post about yesterday's AI meetup'\n• 'Turn this into a post: launched our new feature today'\n• 'Make a short post with a friendly tone'\n\nReply 'regenerate' anytime to get another version."
    )
    # Mark welcomed
    db.db.users.update_one({'user_id': user_id}, {'$set': {'welcomed_after_connect': True, 'updated_at': datetime.utcnow()}})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with interactive menu"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    # Save user to database
    db.save_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Determine connection status
    connected = linkedin_oauth.is_connected(user.id)

    # Create main menu keyboard (hide Connect if already connected)
    keyboard = []
    if not connected:
        keyboard.append([InlineKeyboardButton("🔗 Connect LinkedIn", callback_data="connect_linkedin")])
    keyboard.extend([
        [InlineKeyboardButton("📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton("🤖 AI Content Creator", callback_data="ai_content")],
        [InlineKeyboardButton("📝 Create Post", callback_data="create_post")],
        [InlineKeyboardButton("📋 View Drafts", callback_data="view_drafts")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Welcome to **Kaushal** - Your AI LinkedIn Growth Companion!

Hi {user.first_name}! I'm here to help you:
• 🤖 Generate AI-powered LinkedIn content
• 📈 Grow your professional network
• 📊 Optimize your LinkedIn presence
• 🎯 Create engaging posts automatically

What would you like to do today?
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    # Proactive greet if already connected
    await maybe_send_connect_greeting(user.id, user.first_name, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button callback from user {user_id}: {data}")
    
    if data == "ai_content":
        await handle_ai_content(query)
    elif data == "connect_linkedin":
        await handle_connect_linkedin(query)
    elif data == "check_status":
        await handle_check_status(query)
    elif data == "view_drafts":
        await handle_view_drafts(query)
    elif data == "help":
        await handle_help(query)
    elif data == "main_menu":
        await handle_main_menu(query)
    elif data.startswith("ai_industry_"):
        await handle_industry_selection(query)
    elif data.startswith("ai_tone_"):
        await handle_tone_selection(query)
    elif data.startswith("ai_length_"):
        await handle_length_selection(query)
    elif data == "ai_generate":
        await handle_ai_generate(query)
    else:
        await query.edit_message_text("❌ Unknown button pressed")

async def handle_ai_content(query):
    """Handle AI content creation button"""
    user_id = query.from_user.id
    
    # Initialize user session for AI content creation
    user_sessions[user_id] = {
        'step': 'industry_selection',
        'content_request': {}
    }
    
    # Get industry options
    industries = ContentTemplates.get_industry_templates()
    
    keyboard = []
    for industry, description in industries.items():
        keyboard.append([InlineKeyboardButton(f"🏢 {industry.title()}", callback_data=f"ai_industry_{industry}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🤖 **AI Content Creator**\n\nLet's create amazing LinkedIn content together!\n\n**Step 1: Choose your industry**\n\nWhat industry do you work in?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_industry_selection(query):
    """Handle industry selection for AI content"""
    user_id = query.from_user.id
    industry = query.data.replace("ai_industry_", "")
    
    # Update user session
    if user_id in user_sessions:
        user_sessions[user_id]['content_request']['industry'] = industry
        user_sessions[user_id]['step'] = 'tone_selection'
    
    # Get tone options
    tones = ContentTemplates.get_tone_templates()
    
    keyboard = []
    for tone, description in tones.items():
        keyboard.append([InlineKeyboardButton(f"🎭 {tone.title()}", callback_data=f"ai_tone_{tone}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Industries", callback_data="ai_content")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🤖 **AI Content Creator**\n\n**Step 2: Choose your tone**\n\nIndustry: **{industry.title()}**\n\nWhat tone would you like for your content?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_tone_selection(query):
    """Handle tone selection for AI content"""
    user_id = query.from_user.id
    tone = query.data.replace("ai_tone_", "")
    
    # Update user session
    if user_id in user_sessions:
        user_sessions[user_id]['content_request']['tone'] = tone
        user_sessions[user_id]['step'] = 'length_selection'
    
    keyboard = [
        [InlineKeyboardButton("📝 Short (100-200 words)", callback_data="ai_length_short")],
        [InlineKeyboardButton("📄 Medium (200-400 words)", callback_data="ai_length_medium")],
        [InlineKeyboardButton("📚 Long (400-600 words)", callback_data="ai_length_long")],
        [InlineKeyboardButton("⬅️ Back to Tones", callback_data="ai_content")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    industry = user_sessions.get(user_id, {}).get('content_request', {}).get('industry', 'Unknown')
    
    await query.edit_message_text(
        f"🤖 **AI Content Creator**\n\n**Step 3: Choose content length**\n\nIndustry: **{industry.title()}**\nTone: **{tone.title()}**\n\nHow long would you like your content to be?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_length_selection(query):
    """Handle length selection for AI content"""
    user_id = query.from_user.id
    length = query.data.replace("ai_length_", "")
    
    # Update user session
    if user_id in user_sessions:
        user_sessions[user_id]['content_request']['length'] = length
        user_sessions[user_id]['step'] = 'topic_input'
    
    keyboard = [
        [InlineKeyboardButton("🎯 Generate Content", callback_data="ai_generate")],
        [InlineKeyboardButton("⬅️ Back to Lengths", callback_data="ai_content")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    session = user_sessions.get(user_id, {})
    content_req = session.get('content_request', {})
    industry = content_req.get('industry', 'Unknown')
    tone = content_req.get('tone', 'Unknown')
    
    await query.edit_message_text(
        f"🤖 **AI Content Creator**\n\n**Step 4: Ready to Generate**\n\nIndustry: **{industry.title()}**\nTone: **{tone.title()}**\nLength: **{length.title()}**\n\nClick 'Generate Content' to create your AI-powered LinkedIn post!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_ai_generate(query):
    """Handle AI content generation"""
    user_id = query.from_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text("❌ Session expired. Please start over.")
        return
    
    session = user_sessions[user_id]
    content_req = session.get('content_request', {})
    
    # Show generating message
    await query.edit_message_text(
        "🤖 **Generating AI Content...**\n\nPlease wait while I create your LinkedIn post...\n\nThis may take a few moments.",
        parse_mode='Markdown'
    )
    
    try:
        # Generate content using AI
        content_response = await create_linkedin_content(
            user_id=user_id,
            topic="Professional insights and industry trends",  # Default topic
            industry=content_req.get('industry', 'general'),
            tone=content_req.get('tone', 'professional'),
            length=content_req.get('length', 'medium')
        )
        
        # Format the response
        hashtags_text = " ".join([f"#{tag}" for tag in content_response.hashtags])
        
        content_text = f"""
🤖 **AI-Generated LinkedIn Post**

{content_response.content}

{hashtags_text}

⏰ **Best Time to Post**: {content_response.suggested_time}

💡 **Engagement Tips**:
"""
        
        for i, tip in enumerate(content_response.engagement_tips[:3], 1):
            content_text += f"{i}. {tip}\n"
        
        content_text += f"""
🔧 **LinkedIn Tips**:
"""
        
        for i, tip in enumerate(content_response.linkedin_tips[:2], 1):
            content_text += f"{i}. {tip}\n"
        
        await query.edit_message_text(content_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"AI content generation failed: {e}")
        await query.edit_message_text(
            "❌ **Content Generation Failed**\n\nSorry, I couldn't generate content right now. Please try again later.",
            parse_mode='Markdown'
        )

async def handle_connect_linkedin(query):
    """Handle LinkedIn connection button"""
    user_id = query.from_user.id

    # If already connected, don't push to connect again
    if linkedin_oauth.is_connected(user_id):
        connection = linkedin_oauth.get_linkedin_connection(user_id)
        profile = connection.get('profile_data', {}) if connection else {}
        name = profile.get('name') or " ".join(filter(None, [profile.get('given_name'), profile.get('family_name')])).strip() or 'N/A'
        auth_url = linkedin_oauth.get_auth_url(f"user_{user_id}")
        keyboard = [
            [InlineKeyboardButton("📊 Check Status", callback_data="check_status")],
            [InlineKeyboardButton("🔄 Reconnect", url=auth_url)],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ **Already Connected as {name}!**\n\nYou can view status, or reconnect if you want to re-authorize.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    # Not connected → show connect URL
    auth_url = linkedin_oauth.get_auth_url(f"user_{user_id}")
    keyboard = [
        [InlineKeyboardButton("🔗 Connect LinkedIn", url=auth_url)],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 **LinkedIn Authentication**\n\nClick the button below to connect your LinkedIn account:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_check_status(query):
    """Handle status check button"""
    user_id = query.from_user.id
    is_connected = linkedin_oauth.is_connected(user_id)
    
    if is_connected:
        connection = linkedin_oauth.get_linkedin_connection(user_id)
        profile = connection.get('profile_data', {}) if connection else {}
        # Try name, else build from given/family name
        name = profile.get('name') or " ".join(filter(None, [profile.get('given_name'), profile.get('family_name')])).strip() or 'N/A'
        email = profile.get('email', 'N/A')
        company = profile.get('company', 'N/A')  # May not be available from userinfo
        status_text = f"""
✅ **LinkedIn Connected!**

👤 **Profile**: {name}
🏢 **Company**: {company}
📧 **Email**: {email}

You're all set to create AI-powered content!
        """
    else:
        status_text = """
❌ **LinkedIn Not Connected**

To use all features, please connect your LinkedIn account.
        """
    
    keyboard = [
        [InlineKeyboardButton("🔗 Connect LinkedIn", callback_data="connect_linkedin")] if not is_connected else [],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_view_drafts(query):
    """Handle viewing draft posts"""
    user_id = query.from_user.id
    drafts = db.get_user_posts(user_id, 'draft')
    
    if not drafts:
        await query.edit_message_text(
            "📋 **No Drafts Found**\n\nYou don't have any draft posts yet.\n\nCreate your first post!",
            parse_mode='Markdown'
        )
        return
    
    # Show first few drafts
    drafts_text = "📋 **Your Draft Posts**\n\n"
    for i, draft in enumerate(drafts[:3], 1):
        content_preview = draft.get('content', '')[:100] + "..." if len(draft.get('content', '')) > 100 else draft.get('content', '')
        drafts_text += f"{i}. {content_preview}\n\n"
    
    if len(drafts) > 3:
        drafts_text += f"... and {len(drafts) - 3} more drafts"
    
    await query.edit_message_text(drafts_text, parse_mode='Markdown')

async def handle_help(query):
    """Handle help menu"""
    keyboard = [
        [InlineKeyboardButton("🤖 AI Content Guide", callback_data="ai_guide")],
        [InlineKeyboardButton("🔗 LinkedIn Setup", callback_data="linkedin_setup")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = """
📚 **Kaushal Help Center**

Choose a topic to learn more:

🤖 **AI Content Creator**
- Generate professional LinkedIn posts
- Industry-specific content optimization
- Engagement tips and best practices

🔗 **LinkedIn Integration**
- Connect your LinkedIn account
- Check connection status
- Manage your profile

🔧 **Content Tools**
- Draft management
- Post scheduling
- Content templates
    """
    
    await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_main_menu(query):
    """Handle return to main menu"""
    user = query.from_user

    connected = linkedin_oauth.is_connected(user.id)
    
    keyboard = []
    if not connected:
        keyboard.append([InlineKeyboardButton("🔗 Connect LinkedIn", callback_data="connect_linkedin")])
    keyboard.extend([
        [InlineKeyboardButton("📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton("🤖 AI Content Creator", callback_data="ai_content")],
        [InlineKeyboardButton("📝 Create Post", callback_data="create_post")],
        [InlineKeyboardButton("📋 View Drafts", callback_data="view_drafts")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Welcome to **Kaushal** - Your AI LinkedIn Growth Companion!

Hi {user.first_name}! I'm here to help you:
• 🤖 Generate AI-powered LinkedIn content
• 📈 Grow your professional network
• 📊 Optimize your LinkedIn presence
• 🎯 Create engaging posts automatically

What would you like to do today?
    """
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def generate_and_reply_post(user_id: int, first_name: str, text: str, context: ContextTypes.DEFAULT_TYPE, include_note: str = ""):
    topic = text.strip()
    prefs = user_sessions.get(user_id, {}).get('last_request', {})
    industry = prefs.get('industry', 'general')
    tone = prefs.get('tone', 'professional')
    length = prefs.get('length', 'medium')

    # If we have an existing draft and the user provided a refinement-style instruction, refine instead
    last_draft = user_sessions.get(user_id, {}).get('last_draft')
    refine_cues = any(k in topic.lower() for k in ["from a student perspective", "student perspective", "shorter", "more casual", "more professional", "enthusiastic", "longer", "change tone", "rewrite", "refine", "adjust"])

    if last_draft and refine_cues:
        # Update tone/length quick modifiers
        if "shorter" in topic.lower():
            length = 'short'
        if "longer" in topic.lower():
            length = 'long'
        if "more casual" in topic.lower():
            tone = 'casual'
        if "more professional" in topic.lower():
            tone = 'professional'
        if "enthusiastic" in topic.lower():
            tone = 'enthusiastic'

        refined = await refine_linkedin_content(
            previous_content=last_draft,
            instruction=topic,
            industry=industry,
            tone=tone,
            length=length
        )
        content_text = refined.content
        hashtags = refined.hashtags
    else:
        content_response = await create_linkedin_content(
            user_id=user_id,
            topic=topic,
            industry=industry,
            tone=tone,
            length=length
        )
        content_text = content_response.content
        hashtags = content_response.hashtags

    # Save as draft
    db.save_post(
        user_id=user_id,
        content=content_text,
        post_type='text',
        status='draft',
        ai_generated=True,
        topic=topic,
        industry=industry,
        tone=tone,
        hashtags=hashtags,
    )

    # Store last request and draft
    user_sessions.setdefault(user_id, {})['last_request'] = {
        'topic': topic,
        'industry': industry,
        'tone': tone,
        'length': length,
    }
    user_sessions[user_id]['last_draft'] = content_text

    hashtags_text = " ".join([f"#{tag}" for tag in hashtags])

    reply = f"""
🤖 Draft based on your request:

{content_text}

{hashtags_text}
{include_note}
If you'd like a different version, reply "regenerate" or refine with follow-ups like "shorter", "more casual", or specific instructions (e.g., "from a student perspective").
"""
    await context.bot.send_message(chat_id=user_id, text=reply.strip())

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conversational text flow: greet, understand request, generate, support regenerate"""
    user = update.effective_user
    user_id = user.id
    message_text = (update.message.text or "").strip()

    # Proactive greet after connection (once)
    await maybe_send_connect_greeting(user_id, user.first_name, context)

    lower = message_text.lower()
    # Regenerate flow
    if any(k in lower for k in ["regenerate", "recreate", "again", "another version"]):
        last = user_sessions.get(user_id, {}).get('last_request')
        if not last:
            await update.message.reply_text("I don't have your last request yet. Please describe what you'd like me to write.")
            return
        await generate_and_reply_post(user_id, user.first_name, last.get('topic', ''), context, include_note="\n(🔄 Regenerated)")
        return

    # Interpret message as a new content request
    if message_text:
        await generate_and_reply_post(user_id, user.first_name, message_text, context)
        return

    await update.message.reply_text("Please describe what you'd like me to write for your LinkedIn post.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages by using caption as context"""
    user = update.effective_user
    user_id = user.id
    caption = (update.message.caption or "").strip()

    await maybe_send_connect_greeting(user_id, user.first_name, context)

    if not caption:
        await update.message.reply_text("Got the photo! Please add a caption describing the event or key details, and I'll craft a post.")
        return

    topic_with_photo = f"Photo attached. Context: {caption}"
    await generate_and_reply_post(user_id, user.first_name, topic_with_photo, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add photo handler first
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Add message handler for text messages (conversational)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting Kaushal AI Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
