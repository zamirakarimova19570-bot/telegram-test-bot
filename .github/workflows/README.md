# 🧹 CleanGroupBot — Spamga Qarshi Guruh Tozalovchi Bot

Ushbu bot **Telegram guruhlarida spam, reklama, linklar va nojo'ya tarkibni avtomatik o'chirib tashlaydi**.  
Botni **Replit**da 24/7 ishlatish juda oson!

---

## 🌟 Xususiyatlar

- 🔗 Barcha linklarni blokirovka qiladi (`t.me/`, `https://`, `www.`)
- 📢 Spam so'zlarni aniqlaydi: "pul ishlash", "kredit", "18+", "reklama" va boshqalar
- 🧹 Xabarni avtomatik o'chiradi + 10 soniya ogohlantirish
- 👤 Faqat guruhda ishlaydi (shaxsiy chatlarda faol emas)

---

## ▶️ Replitda Botni Sozlash (2 daqiqa)

### 1. GitHub repozitoriyasini yarating
- Ushbu fayllarni GitHubga qo'ying:
  - `bot.py`
  - `requirements.txt`
  - `.gitignore`
  - `README.md` (shu fayl)

> ❗ **Muhim**: Hech qachon `BOT_TOKEN`ni GitHubda saqlamang!

### 2. Replit.com ga kiring
- [replit.com](https://replit.com) ga kiring (GitHub hisobingiz bilan kiring).
- **+ Create Repl** → **Import from GitHub**.
- Sizning `clean-group-bot` repozitoriyangizni tanlang.

### 3. `.env` faylini sozlang (Replitda)
- Replit loyiha ochilganda chap tomonda **"Secrets"** (🔒) tugmasini bosing.
- Yangi **Secret** qo'shing:
  - **Key**: `BOT_TOKEN`
  - **Value**: `8577664982:AAFIz8yMn-4SHLCCtFXvDOmHYG8PkIz5SEg` (sizning token)

### 4. `bot.py` dagi koddan token o'chirilganligiga ishonch hosil qiling:
```python
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Replit Secrets orqali ishlaydi
