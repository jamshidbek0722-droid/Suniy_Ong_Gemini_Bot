import logging
import aiohttp
import config

logger = logging.getLogger(__name__)

# Dictionary to hold rolling chat history in RAM: {user_id: [messages]}
# Each message is a dict with keys "role" and "content"
rolling_history: dict[int, list[dict]] = {}

# Groq Chat API completions endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# System instructions to enforce Uzbek language responses and assistant persona
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Siz foydali, aqlli va samimiy AI yordamchisiz. "
        "Foydalanuvchi bilan har doim 100% o'zbek tilida so'zlashing. "
        "Javoblaringizda Markdown formatidan foydalanib, muhim joylarni qalin (bold) "
        "va chiroyli ko'rinishda yozing."
    )
}

async def get_ai_response(user_id: int, user_message: str) -> tuple[str, int]:
    """
    Sends the message to DeepSeek API along with rolling chat history.
    Returns a tuple of (response_text, tokens_used).
    """
    # Initialize rolling history for user if not exists
    if user_id not in rolling_history:
        rolling_history[user_id] = []

    # Append user's new message to rolling history
    rolling_history[user_id].append({"role": "user", "content": user_message})

    # Enforce maximum rolling history of 15 messages (approx. 7 turns)
    if len(rolling_history[user_id]) > 15:
        # Dynamically slice history to keep only the last 15 messages to preserve RAM
        rolling_history[user_id] = rolling_history[user_id][-15:]
        logger.info(f"Cleaned older history chunks for user {user_id} to keep context size under 15.")

    # Prepare payload with the system prompt and rolling history
    payload_messages = [SYSTEM_PROMPT] + rolling_history[user_id]
    
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": payload_messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_API_URL, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_reply = data["choices"][0]["message"]["content"]
                    tokens_used = data.get("usage", {}).get("total_tokens", 0)
                    
                    # Append assistant reply to the rolling context
                    rolling_history[user_id].append({"role": "assistant", "content": ai_reply})
                    return ai_reply, tokens_used
                else:
                    error_text = await response.text()
                    logger.error(f"Groq API error (Status: {response.status}): {error_text}")
                    return (
                        "⚠️ Kechirasiz, sun'iy ong xizmatida vaqtincha uzilish yuz berdi. "
                        "Iltimos, birozdan so'ng qayta urinib ko'ring.", 0
                    )
    except Exception as e:
        logger.error(f"Error calling Groq API for user {user_id}: {e}")
        return "⚠️ Tarmoq xatoligi yuz berdi. Groq API bilan bog'lanib bo'lmadi.", 0

def clear_history(user_id: int):
    """Clears the rolling chat history context for a specific user."""
    if user_id in rolling_history:
        del rolling_history[user_id]
        logger.info(f"Rolling history cleared for user {user_id}")
