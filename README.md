# 🚛 ELD Monitor — Algo Group LLC

Real-time ELD monitoring + Telegram avtomatik alertlar.
Sizning Telegram accountingizdan driver guruhlarga xabar yuboradi (bot emas!).

---

## 📁 Fayl Strukturasi

```
eld-monitor/
├── main.py                    # FastAPI app (entry point)
├── config.py                  # Settings (.env yuklash)
├── database.py                # SQLite modellari
├── requirements.txt
├── render.yaml                # Render.com deploy config
├── .env.example               # Environment o'zgaruvchilar
├── start.sh                   # Local ishga tushirish
├── services/
│   ├── eld_client.py          # Factor/Leader ELD API clients
│   ├── telegram_client.py     # Telethon (user account)
│   ├── monitor.py             # Monitoring engine + alert logic
│   └── alert_messages.py      # 15x paraphrase templates
├── routers/
│   └── api.py                 # REST API endpoints
└── frontend/
    └── index.html             # Liquid Glass Dashboard
```

---

## 🚀 Local Ishga Tushirish

```bash
# 1. Papkaga kiring
cd eld-monitor

# 2. .env yarating
cp .env.example .env
# .env ni tahrirlang — tokenlarni kiriting

# 3. Ishga tushiring
chmod +x start.sh
./start.sh

# Yoki to'g'ridan-to'g'ri:
pip install -r requirements.txt
python main.py
```

Dashboard: http://localhost:8000

---

## ⚙️ .env Sozlash

```env
TELEGRAM_API_ID=35507477
TELEGRAM_API_HASH=201ab47b2a808cc66c3ef61529dba649
TELEGRAM_PHONE=+998775013234
TELEGRAM_SESSION_STRING=   # Birinchi logindan keyin avtomatik to'ldiriladi

ELD_BASE_URL=https://api.drivehos.app/api/v1
ELD_BEARER_TOKEN=eyJ...    # Factor ELD bearer token
ELD_TENANT_ID=96335ac3-5a93-4a29-af8b-08d874801325

POLL_INTERVAL_SECONDS=300  # 5 daqiqa
```

---

## 📱 Telegram Birinchi Login

1. Dasturni ishga tushiring
2. Dashboard → **Telegram** sahifasiga o'ting
3. **SMS Yuborish** tugmasini bosing
4. Telefoningizga kelgan kodni kiriting
5. Session saqlandi — keyingi ishga tushirishda OTP so'ralmaydi

**Session string** ni `.env` ga qo'shib qo'ying (dastur avtomatik ko'rsatadi):
```
TELEGRAM_SESSION_STRING=1BVtsOK8Bu...
```

---

## 👤 Driver Qo'shish

**Usul 1 — Avtomatik (ELD dan Sync):**
- Drivers → "ELD dan Sync" → Factor ELD tanlang → Sync

**Usul 2 — Qo'lda:**
- Drivers → "Driver qo'shish" → Ma'lumotlarni kiriting

**Telegram guruh ulash:**
- Driver tahrirlash → Telegram Guruh dropdown → Tanlang

---

## 🔔 Alert Turlari

| Alert | Holat | Paraphrase |
|-------|-------|-----------|
| `cycle_low` | Cycle < 20 soat | 15 ta variant |
| `drive_low` | Drive < 2 soat | 15 ta variant |
| `shift_low` | Shift < 2 soat | 15 ta variant |
| `break_low` | Break < 2 soat | 15 ta variant |
| `document_incomplete` | Hujjat to'liq emas | 15 ta variant |
| `disconnect` | ELD offline | 15 ta variant |
| `on_break` | Break holatida | 15 ta variant |
| `profile_form` | Profile muammosi | 15 ta variant |

**Cooldown**: Bir xil alert 90 daqiqa ichida qayta yuborilmaydi.

---

## 📡 Yangi ELD Qo'shish

**Leader ELD API tayyor bo'lganda:**
1. `services/eld_client.py` → `LeaderEldClient` klassini to'ldiring
2. Dashboard → ELD Sources → "+ ELD qo'shish"
3. Leader ELD ma'lumotlarini kiriting

---

## 🌐 Render.com Deploy

```bash
# GitHub ga push qiling
git init
git add .
git commit -m "ELD Monitor v2"
git remote add origin https://github.com/Shobola2910/eld-monitor
git push -u origin main
```

Render.com:
1. New Web Service → GitHub repo tanlang
2. `render.yaml` avtomatik o'qiladi
3. Environment variables → TELEGRAM_SESSION_STRING, ELD_BEARER_TOKEN qo'shing

---

## 🔧 API Endpoints

```
GET  /api/drivers              — Barcha driverlar
POST /api/drivers              — Driver qo'shish
PUT  /api/drivers/{id}         — Driver yangilash
DELETE /api/drivers/{id}       — Driver o'chirish
POST /api/drivers/sync-from-eld — ELD dan import

GET  /api/eld-sources          — ELD manbalar
POST /api/eld-sources          — ELD manba qo'shish

GET  /api/telegram/status      — Telegram holati
POST /api/telegram/auth/send-code — OTP yuborish
POST /api/telegram/auth/verify — OTP tasdiqlash
GET  /api/telegram/groups      — Guruhlar ro'yxati
POST /api/telegram/send        — Test xabar

POST /api/monitor/run          — Monitor qo'lda ishlatish
GET  /api/monitor/alerts       — Alert tarixi
GET  /api/monitor/alerts/stats — Statistika
```

---

## 📞 Qo'llab-quvvatlash

- Algo Group LLC
- ELD: Factor (drivehos.app), Leader (kelgusida)
