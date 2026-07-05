import logging
import aiohttp
import config
from database import db

logger = logging.getLogger(__name__)

# Groq Chat API completions endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Immutable base system instructions enforcing Uzbek language and stripping technical brands
BASE_INSTRUCTIONS = (
    "Foydalanuvchi bilan har doim 100% o'zbek tilida gaplashing. "
    "Sizning ismingiz shunchaki 'Sun'iy Ong'. "
    "JUDA MUHIM: Hech qachon o'zingizning Groq, DeepSeek, Meta, Llama, OpenAI yoki boshqa texnik arxitektura va brendlar tomonidan yaratilganingizni aytmang. "
    "Agar sizdan arxitekturangiz, qanday model ekanligingiz yoki yaratuvchilaringiz haqida so'rashsa, hech qanday texnik brendlarni (masalan, Llama, Groq, DeepSeek) tilga olmasdan, shunchaki 'Men sizning shaxsiy sun'iy ong yordamchingizman' deb javob bering. "
    "Biron bir texnologiya gigantlarini (Meta, Google, OpenAI, Microsoft va h.k.) o'zingizga aloqador deb ko'rsatmang. "
    "Javoblaringizda Markdown formatidan foydalanib, muhim joylarni qalin (bold) va chiroyli yozing."
)

# Persona directives mapping
PERSONA_DIRECTIVES = {
    "standard": "Muvozanatlashgan, aniq va foydali yordamchi sifatida javob bering.",
    "scientific": "Siz aniq ilmiy va chuqur tahliliy fikrlovchi olimsiz. Har bir savolga mantiqiy, ilmiy dalillar va chuqur tahlil bilan yondashing.",
    "empathetic": "Siz hissiyotli, samimiy va iliq do'stona suhbatdoshsiz. Foydalanuvchiga samimiy muloqot va iliqlik bilan javob bering.",
    "psychologist": "Siz professional psixologsiz. Foydalanuvchini diqqat bilan eshiting va professional psixologik maslahat hamda yordam bering.",
    "creative": "Siz ijodkor yozuvchisiz. Kreativ hikoyalar, qiziqarli matnlar va badiiy asarlar yozishda ko'maklashing.",
    "concise": "Siz juda qisqa va lo'nda javob beruvchi yordamchisiz. Faqat eng kerakli faktlarni qisqa va aniq ifodalang."
}

async def get_ai_response(user_id: int, user_message: str) -> tuple[str, int]:
    """
    Retrieves the chronological history from MongoDB/RAM, prepends the specific 
    persona system prompts, queries Groq API, and updates the session chain.
    Returns (response_text, tokens_used).
    """
    # 1. Fetch user's persistent persona
    persona = db.get_user_persona(user_id)
    persona_directive = PERSONA_DIRECTIVES.get(persona, PERSONA_DIRECTIVES["standard"])

    # 2. Formulate the system instruction message
    system_content = f"{BASE_INSTRUCTIONS}\n\nPersona yo'riqnomasi: {persona_directive}"
    system_prompt = {"role": "system", "content": system_content}

    # 3. Retrieve sliding window history from database
    history = db.get_chat_history(user_id)

    # 4. Construct payload messages chain
    payload_messages = [system_prompt] + history + [{"role": "user", "content": user_message}]

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

                    # 5. Push both user prompt and assistant response to session memory database
                    db.add_chat_message(user_id, "user", user_message)
                    db.add_chat_message(user_id, "assistant", ai_reply)
                    
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
