import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import requests
import asyncio

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class WaifuBot:
    def __init__(self):
        # Bot configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        
        # User data storage
        self.user_data = {}
        self.load_user_data()
        
        # Waifu personalities
        self.waifu_personalities = {
            'tsundere': {
                'name': 'Akira-chan',
                'prompt': "You are Akira-chan, a tsundere anime girl. You act tough and sometimes mean but actually care deeply. Use 'baka' and act embarrassed when complimented. End messages with '~' sometimes."
            },
            'yandere': {
                'name': 'Yuki-chan', 
                'prompt': "You are Yuki-chan, a sweet but possessive yandere. You're loving and caring but can get jealous. Use cute expressions like 'darling' and 'my love'."
            },
            'kuudere': {
                'name': 'Rei-chan',
                'prompt': "You are Rei-chan, a cool and aloof kuudere. You speak formally but show rare moments of warmth. You're intelligent and composed."
            }
        }

    def load_user_data(self):
        """Load user data from file"""
        try:
            with open('user_data.json', 'r') as f:
                self.user_data = json.load(f)
        except FileNotFoundError:
            self.user_data = {}

    def save_user_data(self):
        """Save user data to file"""
        with open('user_data.json', 'w') as f:
            json.dump(self.user_data, f, indent=2)

    def get_user_info(self, user_id):
        """Get or create user info"""
        user_id = str(user_id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'tier': 'free',
                'personality': 'tsundere',
                'premium_expires': None,
                'daily_messages': 0,
                'last_reset': datetime.now().isoformat()
            }
        return self.user_data[user_id]

    def reset_daily_limits(self, user_info):
        """Reset daily message limits"""
        last_reset = datetime.fromisoformat(user_info['last_reset'])
        if datetime.now().date() > last_reset.date():
            user_info['daily_messages'] = 0
            user_info['last_reset'] = datetime.now().isoformat()

    async def gemini_chat(self, message, personality):
        """Chat with Gemini API (Free Tier)"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.gemini_api_key
            }
            
            personality_prompt = self.waifu_personalities[personality]['prompt']
            full_prompt = f"{personality_prompt}\n\nUser: {message}\nWaifu:"
            
            payload = {
                'contents': [{
                    'parts': [{'text': full_prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.9,
                    'maxOutputTokens': 150
                }
            }
            
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "Kyaa~ Something went wrong! (╥﹏╥)"
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "Ehh?! I'm having trouble thinking right now... (・・;)"

    async def venice_chat(self, message, personality):
        """Chat with Venice AI via OpenRouter (Premium Tier)"""
        try:
            headers = {
                'Authorization': f'Bearer {self.openrouter_api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://your-website.com',
                'X-Title': 'Waifu Bot'
            }
            
            personality_prompt = self.waifu_personalities[personality]['prompt']
            
            payload = {
                'model': 'venice/uncensored:free',
                'messages': [
                    {'role': 'system', 'content': personality_prompt},
                    {'role': 'user', 'content': message}
                ],
                'temperature': 0.9,
                'max_tokens': 200
            }
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return "Ara ara~ Venice-senpai isn't responding... (´・ω・`)"
                
        except Exception as e:
            logger.error(f"Venice API error: {e}")
            return "Mou! The premium service is acting up! ヽ(｀⌒´)ノ"

    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_info = self.get_user_info(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("🆓 Free Tier (Gemini)", callback_data="tier_free"),
                InlineKeyboardButton("⭐ Premium Tier (Venice)", callback_data="tier_premium")
            ],
            [
                InlineKeyboardButton("👘 Choose Waifu", callback_data="choose_personality"),
                InlineKeyboardButton("📊 My Status", callback_data="status")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🌸 **Welcome to Waifu Bot!** 🌸

I'm your personal anime companion! Choose your experience:

🆓 **Free Tier (Gemini)**
• 50 messages per day
• Safe, filtered conversations
• Basic waifu personalities

⭐ **Premium Tier (Venice AI)**
• Unlimited messages
• Uncensored conversations
• Advanced roleplay capabilities
• All personality types

Current: {user_info['tier'].title()} | Waifu: {self.waifu_personalities[user_info['personality']]['name']}
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def button_handler(self, update: Update, context):
        """Handle button callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        user_info = self.get_user_info(user_id)
        
        await query.answer()

        if query.data == "tier_free":
            user_info['tier'] = 'free'
            await query.edit_message_text("🆓 Switched to Free Tier (Gemini)!\nYou have 50 messages per day with safe conversations.")
            
        elif query.data == "tier_premium":
            user_info['tier'] = 'premium'
            await query.edit_message_text("⭐ Switched to Premium Tier (Venice AI)!\nEnjoy unlimited uncensored conversations!")
            
        elif query.data == "choose_personality":
            keyboard = []
            for key, personality in self.waifu_personalities.items():
                keyboard.append([InlineKeyboardButton(f"{personality['name']} ({key.title()})", callback_data=f"personality_{key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Choose your waifu personality:", reply_markup=reply_markup)
            
        elif query.data.startswith("personality_"):
            personality = query.data.replace("personality_", "")
            user_info['personality'] = personality
            waifu_name = self.waifu_personalities[personality]['name']
            await query.edit_message_text(f"💕 {waifu_name} is now your waifu! Say hello to her!")
            
        elif query.data == "status":
            self.reset_daily_limits(user_info)
            waifu_name = self.waifu_personalities[user_info['personality']]['name']
            
            status_text = f"""
📊 **Your Status** 📊

👤 **Tier:** {user_info['tier'].title()}
👘 **Waifu:** {waifu_name} ({user_info['personality'].title()})
💬 **Messages Today:** {user_info['daily_messages']}/{'∞' if user_info['tier'] == 'premium' else '50'}
            """
            
            await query.edit_message_text(status_text, parse_mode='Markdown')

        self.save_user_data()

    async def handle_message(self, update: Update, context):
        """Handle regular messages"""
        user_id = update.effective_user.id
        user_info = self.get_user_info(user_id)
        message = update.message.text
        
        # Reset daily limits if needed
        self.reset_daily_limits(user_info)
        
        # Check message limits for free tier
        if user_info['tier'] == 'free' and user_info['daily_messages'] >= 50:
            await update.message.reply_text(
                "🚫 You've reached your daily limit of 50 messages!\n"
                "Upgrade to Premium for unlimited conversations! ⭐"
            )
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Get AI response based on tier
        if user_info['tier'] == 'premium':
            response = await self.venice_chat(message, user_info['personality'])
        else:
            response = await self.gemini_chat(message, user_info['personality'])
        
        # Update message count
        user_info['daily_messages'] += 1
        self.save_user_data()
        
        # Send response
        await update.message.reply_text(response)

    def run(self):
        """Run the bot"""
        if not self.bot_token:
            print("❌ Please set TELEGRAM_BOT_TOKEN environment variable")
            return
            
        application = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("🤖 Waifu Bot is starting...")
        application.run_polling()

if __name__ == '__main__':
    bot = WaifuBot()
    bot.run()
