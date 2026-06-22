# Telegram AI Assistant Bot (DeepSeek API + aiogram 3.x)

A production-ready, highly optimized Telegram AI Assistant Bot written in Python using the `aiogram 3.x` framework and integrated with the DeepSeek API. The bot interacts 100% in Uzbek while using an optimized English codebase.

## Features

- **High-Performance In-Memory DB Sync**: Uses a local RAM cache synced with a Telegram channel database by editing the pinned message (`index.json`) to prevent rate limits and message clutter.
- **DeepSeek AI Chat Integration**: Integrated with the `deepseek-chat` model with dynamic context trimming (rolling 15 messages) to limit RAM consumption.
- **Forced Subscription Middleware**: Gently blocks unsubscribed users with subscription prompts and inline checking.
- **Guided FSM Surveys**: Collects demographic details (Gender, Age, Region, Occupation) from users to structure their profiles.
- **Bi-directional Support**: Allows users to send feedback and admins to reply directly to messages.
- **Admin Dashboard**: Comprehensive breakdowns of registered users by gender, region, and age groups, and dynamic advertising footer configuration.

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone <your-repository-url>
cd Suniy_Ong_Gemini_Bot
```

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env` and fill in your actual credentials:
```bash
cp .env.example .env
```
Open `.env` and populate the values:
```env
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=YOUR_TELEGRAM_ID
DATABASE_CHANNEL_ID=YOUR_SYNC_CHANNEL_ID
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
```
> [!IMPORTANT]
> The `.env` file contains sensitive information and is excluded from git commits via `.gitignore`. Never commit `.env` to GitHub!

### 3. Install Dependencies
Ensure you have the required packages installed:
```bash
pip install aiogram aiohttp python-dotenv
```

### 4. Running the Bot
Start the polling loop of the bot:
```bash
python main.py
```
