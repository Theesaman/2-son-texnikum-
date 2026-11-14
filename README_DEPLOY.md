# Karmana tuman 2-son texnikumi — Veb-sayt va Premium Telegram Botni Serverga Joylash Qo'llanmasi

Ushbu loyiha **Veb-sayt (`index.html`)** va **Premium Telegram Bot (`bot_and_server.py`)** ni bitta serverda (Railway, Render yoki VPS) birgalikda 24/7 rejimida ishlatish uchun to'liq tayyorlangan.

## 1-qadam: Telegram Bot Tokenini Olish
1. Telegram'da **[@BotFather](https://t.me/BotFather)** ga kiring va `/newbot` buyrug'ini yuboring.
2. Botga nom bering (masalan: `Karmana 2-son Texnikumi`) va username tanlang (masalan: `karmana_2texnikum_bot`).
3. BotFather bergan **API Token**ni nusxalab oling.
4. O'zingizning Telegram ID raqamingizni bilish uchun **[@userinfobot](https://t.me/userinfobot)** ga `/start` bosing va `Id` raqamingizni nusxalab oling (bu orqali botda `/admin` paneli va yangi arizalar bildirishnomasi sizga keladi).

## 2-qadam: Railway.app Serveriga 2 Daqiqada Joylash (Tavsiya etiladi)
1. Ushbu ZIP arxiv ichidagi fayllarni GitHub'dagi yangi repozitoriyga yuklang.
2. **[Railway.app](https://railway.app)** saytiga kiring va **New Project -> Deploy from GitHub repo** ni tanlang.
3. Loyihangizning **Variables** bo'limiga kirib, quyidagi 3 ta o'zgaruvchini qo'shing:
   - `BOT_TOKEN` = BotFather bergan token
   - `ADMIN_IDS` = Sizning Telegram ID raqamingiz (masalan: `543219876`)
   - `PUBLIC_URL` = Railway bergan domeningiz (`Settings -> Networking -> Generate Domain` tugmasini bosing)
4. Railway avtomatik ravishda `Procfile` va `requirements.txt` orqali **ham Veb-saytni, ham Telegram Botni** 24/7 rejimida ishga tushiradi!

## 3-qadam: Faqat Saytni Vercel'ga, Botni Railway'ga Joylash (Ixtiyoriy)
- Agar saytni alohida **Vercel**ga qo'ymoqchi bo'lsangiz, `index.html` faylini Vercel'ga yuklashingiz kifoya.
- `bot_and_server.py` esa Railway'da ham botni, ham veb-saytni bir vaqtda ko'taradi.

## Bot Imkoniyatlari:
- **3 tilda muloqot:** O'zbek, Rus va Ingliz tillari (`/start` bosilganda yoki menyudan almashtiriladi).
- **7 ta rasmiy yo'nalish katalogi:** Har bir kasb kodi (`30610403`, `30711605`, `30720436`, `30710105`, `30710310`, `30810105`, `30711307`) va ularning barcha kvalifikatsiyalari.
- **Sayt bilan Deep-Link integratsiya:** Saytdagi har qanday yo'nalishda **"Telegram Bot"** tugmasi bosilganda `?start=apply_<KOD>` orqali bot aynan o'sha yo'nalishni tanlagan holda ariza qabul qilishni boshlaydi.
- **Onlayn Ariza (FSM):** Ism-sharif, telefon kontakt tugmasi, yo'nalish va izohni qabul qilib SQLite bazaga saqlaydi hamda darhol Admin Telegramiga xabar yuboradi.
- **Admin Panel (`/admin`):** Bot ichida `/admin` buyrug'i orqali jonli statistika, barcha arizalarni **Excel (CSV)** formatida yuklab olish va barcha foydalanuvchilarga e'lon (Broadcast) yuborish.
