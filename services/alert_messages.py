"""
Alert message templates — 15 paraphrases per alert type.
Each function returns a random variant so Telegram won't flag as spam.
"""
import random
from datetime import datetime

# ─── Helper ───────────────────────────────────────────────────────────────────

def _pick(templates: list[str], **kwargs) -> str:
    return random.choice(templates).format(**kwargs)

def _ts() -> str:
    return datetime.now().strftime("%m/%d %H:%M")

# ─── CYCLE TIME LOW (< 20 hrs) ────────────────────────────────────────────────

CYCLE_LOW_TEMPLATES = [
    "⚠️ [{ts}] {name} — Cycle vaqti {hours:.1f} soat qoldi (chegarasi 20 soat). Diqqat talab qilinadi!",
    "🔴 [{ts}] Haydovchi {name}: Cycle soati {hours:.1f} ga tushdi. 20 soatdan kam — nazorat zarur.",
    "⏰ [{ts}] {name} uchun Cycle vaqti ogohlantirishi: {hours:.1f} soat qoldi. Iltimos tekshiring.",
    "🚨 [{ts}] {name} — Cycle balans {hours:.1f} soat. Ruxsat etilgan chegaradan past (20h).",
    "📉 [{ts}] Diqqat: {name} ning Cycle vaqti {hours:.1f} soatga yetdi. Nazorat kerak.",
    "⚡ [{ts}] {name}: Qolgan Cycle soati {hours:.1f} — bu 20 soat chegarasidan past.",
    "🟠 [{ts}] {name} uchun Cycle ogohlantirishi. Joriy qoldiq: {hours:.1f} soat.",
    "⚠️ [{ts}] {name} ning Cycle vaqti kritik darajaga tushdi: {hours:.1f} soat qoldi.",
    "📢 [{ts}] {name} — Cycle limit yaqinlashmoqda. Qoldi: {hours:.1f} soat.",
    "🔔 [{ts}] {name}: Cycle soat qoldig'i {hours:.1f} h. Limit 20h — tekshiring.",
    "⏳ [{ts}] {name} haydovchisining Cycle vaqti {hours:.1f} soatga tushib ketdi.",
    "🚦 [{ts}] {name} — Cycle {hours:.1f} soat qoldi. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: Cycle balansi past — {hours:.1f} soat (min: 20h).",
    "🟡 [{ts}] {name} uchun Cycle ogohlantirish: joriy qoldiq {hours:.1f} soat.",
    "⚠️ [{ts}] {name} Cycle limiti yaqin: {hours:.1f} soat qoldi. Iltimos diqqat qiling.",
]

# ─── DRIVE TIME LOW (< 2 hrs) ─────────────────────────────────────────────────

DRIVE_LOW_TEMPLATES = [
    "🚗 [{ts}] {name} — Kunlik Drive vaqti {hours:.1f} soat qoldi. Ehtiyot bo'ling!",
    "⚠️ [{ts}] {name}: Drive limit {hours:.1f} soat. 2 soatdan kam qoldi.",
    "🔴 [{ts}] Haydovchi {name} uchun Drive vaqti ogohlantirishi: {hours:.1f} soat.",
    "🚨 [{ts}] {name} ning Drive vaqti kritik: {hours:.1f} soat qoldi (min: 2h).",
    "⏰ [{ts}] {name} — Drive balans {hours:.1f} soatga tushdi. Diqqat!",
    "📢 [{ts}] {name}: Qolgan haydash vaqti {hours:.1f} soat — nazorat zarur.",
    "🟠 [{ts}] {name} uchun Drive ogohlantirishi. Qoldiq: {hours:.1f} soat.",
    "⚡ [{ts}] {name} ning haydash vaqti {hours:.1f} soat qoldi.",
    "🔔 [{ts}] {name}: Drive time {hours:.1f} h — limit yaqin, tekshiring.",
    "📉 [{ts}] {name} — Kunlik Drive vaqtida {hours:.1f} soat qoldi.",
    "⏳ [{ts}] {name} haydovchisida Drive vaqti {hours:.1f} soatga tushdi.",
    "🚦 [{ts}] {name} — Drive {hours:.1f} soat. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: Drive balansi past — {hours:.1f} soat (min: 2h).",
    "🟡 [{ts}] {name} Drive ogohlantirish: joriy qoldiq {hours:.1f} soat.",
    "⚠️ [{ts}] {name} Drive limiti yaqin: {hours:.1f} soat qoldi.",
]

# ─── BREAK TIME LOW (< 2 hrs) ─────────────────────────────────────────────────

BREAK_LOW_TEMPLATES = [
    "😴 [{ts}] {name} — Break vaqti {hours:.1f} soat qoldi. Dam olish kerak!",
    "⚠️ [{ts}] {name}: Break limit {hours:.1f} soat. Haydovchi dam olishni rejalashtirsin.",
    "🔴 [{ts}] {name} uchun Break ogohlantirishi: {hours:.1f} soat qoldi (min: 2h).",
    "🚨 [{ts}] {name} ning Break vaqti past: {hours:.1f} soat — majburiy to'xtash zarur.",
    "⏰ [{ts}] {name} — Break balans {hours:.1f} soatga tushdi. Diqqat!",
    "📢 [{ts}] {name}: Qolgan Break vaqti {hours:.1f} soat — tekshiring.",
    "🟠 [{ts}] {name} Break ogohlantirishi. Qoldiq: {hours:.1f} soat.",
    "⚡ [{ts}] {name} ning dam olish vaqti {hours:.1f} soat qoldi.",
    "🔔 [{ts}] {name}: Break time {hours:.1f} h — haydovchi dam olishni kechiktirmasin.",
    "📉 [{ts}] {name} — Break vaqtida {hours:.1f} soat qoldi.",
    "⏳ [{ts}] {name} haydovchisida Break {hours:.1f} soatga tushdi.",
    "🚦 [{ts}] {name} — Break {hours:.1f} soat. Dam olish kerak.",
    "📌 [{ts}] {name}: Break balansi past — {hours:.1f} soat (min: 2h).",
    "🟡 [{ts}] {name} Break ogohlantirish: joriy qoldiq {hours:.1f} soat.",
    "⚠️ [{ts}] {name} Break limiti yaqin: {hours:.1f} soat qoldi.",
]

# ─── SHIFT TIME LOW (< 2 hrs) ─────────────────────────────────────────────────

SHIFT_LOW_TEMPLATES = [
    "🕐 [{ts}] {name} — Shift vaqti {hours:.1f} soat qoldi. Nazorat zarur!",
    "⚠️ [{ts}] {name}: Shift limit {hours:.1f} soat. 2 soatdan kam.",
    "🔴 [{ts}] {name} uchun Shift ogohlantirishi: {hours:.1f} soat qoldi.",
    "🚨 [{ts}] {name} ning Shift vaqti past: {hours:.1f} soat (min: 2h).",
    "⏰ [{ts}] {name} — Shift balans {hours:.1f} soatga tushdi.",
    "📢 [{ts}] {name}: Qolgan Shift vaqti {hours:.1f} soat.",
    "🟠 [{ts}] {name} Shift ogohlantirishi. Qoldiq: {hours:.1f} soat.",
    "⚡ [{ts}] {name} ning Shift vaqti {hours:.1f} soat qoldi.",
    "🔔 [{ts}] {name}: Shift {hours:.1f} h — limit yaqin, tekshiring.",
    "📉 [{ts}] {name} — Shift vaqtida {hours:.1f} soat qoldi.",
    "⏳ [{ts}] {name} haydovchisida Shift {hours:.1f} soatga tushdi.",
    "🚦 [{ts}] {name} — Shift {hours:.1f} soat. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: Shift balansi past — {hours:.1f} soat (min: 2h).",
    "🟡 [{ts}] {name} Shift ogohlantirish: qoldiq {hours:.1f} soat.",
    "⚠️ [{ts}] {name} Shift limiti yaqin: {hours:.1f} soat qoldi.",
]

# ─── DOCUMENT INCOMPLETE ─────────────────────────────────────────────────────

DOCUMENT_INCOMPLETE_TEMPLATES = [
    "📄 [{ts}] {name} — Hujjat to'ldirilmagan! Iltimos tekshiring.",
    "⚠️ [{ts}] {name}: Logbook hujjati to'liq emas. Zudlik bilan to'ldiring.",
    "🔴 [{ts}] {name} uchun hujjat ogohlantirishi: form to'ldirilmagan.",
    "🚨 [{ts}] {name} ning hujjati incomplete. Compliance xavfi bor!",
    "📋 [{ts}] {name} — Driver form to'liq emas. Diqqat!",
    "📢 [{ts}] {name}: Hujjat to'ldirilmagan — FMCSA compliance uchun zarur.",
    "🟠 [{ts}] {name} uchun logbook ogohlantirishi: form incomplete.",
    "⚡ [{ts}] {name} ning hujjati to'ldirilmagan. Zudlik bilan hal qiling.",
    "🔔 [{ts}] {name}: Document form incomplete — iltimos to'ldiring.",
    "📉 [{ts}] {name} — Hujjat holati: to'ldirilmagan. Xabar bering.",
    "⏳ [{ts}] {name} haydovchisida hujjat to'liq emas.",
    "🚦 [{ts}] {name} — Form incomplete. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: Driver logbook form to'liq emas.",
    "🟡 [{ts}] {name} document ogohlantirish: form yetarli emas.",
    "⚠️ [{ts}] {name} uchun hujjat to'liq emas — iltimos tekshiring.",
]

# ─── DRIVER DISCONNECT ───────────────────────────────────────────────────────

DISCONNECT_TEMPLATES = [
    "📡 [{ts}] {name} — ELD ulanish uzildi! Qurilma offline.",
    "⚠️ [{ts}] {name}: ELD disconnect. Ulanishni tekshiring.",
    "🔴 [{ts}] {name} uchun disconnect ogohlantirishi: ELD offline.",
    "🚨 [{ts}] {name} ning ELD qurilmasi uzilgan. Zudlik bilan tekshiring!",
    "📡 [{ts}] {name} — Haydovchi ELD dan chiqib ketdi. Diqqat!",
    "📢 [{ts}] {name}: ELD signal yo'q — ulanish muammosi.",
    "🟠 [{ts}] {name} uchun ELD ogohlantirishi: qurilma disconnect.",
    "⚡ [{ts}] {name} ning ELD ulanishi uzildi. Haydovchi bilan bog'laning.",
    "🔔 [{ts}] {name}: ELD offline — ulanishni tiklash zarur.",
    "📉 [{ts}] {name} — ELD holati: uzilgan. Tekshiring.",
    "⏳ [{ts}] {name} haydovchisining ELD qurilmasi offline.",
    "🚦 [{ts}] {name} — ELD disconnect. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: ELD ulanish uzildi — nazorat zarur.",
    "🟡 [{ts}] {name} ELD ogohlantirish: qurilma offline.",
    "⚠️ [{ts}] {name} ELD ulanishi yo'q — iltimos tekshiring.",
]

# ─── ON BREAK ────────────────────────────────────────────────────────────────

ON_BREAK_TEMPLATES = [
    "☕ [{ts}] {name} — Hozirda Break holatida ({duration} min).",
    "😴 [{ts}] {name}: Dam olmoqda. Break davomiyligi: {duration} min.",
    "🟢 [{ts}] {name} Break boshladi ({duration} daqiqa).",
    "☕ [{ts}] {name} — Break {duration} daqiqadan beri davom etmoqda.",
    "📢 [{ts}] {name}: Haydovchi hozir dam olmoqda ({duration} min).",
    "🟠 [{ts}] {name} Break holatida, davomiyligi {duration} daqiqa.",
    "⏰ [{ts}] {name} — Break {duration} daqiqa o'tdi.",
    "🔔 [{ts}] {name}: Joriy holat — Break ({duration} min).",
    "📌 [{ts}] {name} dam olmoqda — {duration} daqiqa.",
    "😴 [{ts}] {name}: Break davom etmoqda ({duration} min).",
    "☕ [{ts}] {name} — Haydovchi break holatida, {duration} min.",
    "🟢 [{ts}] {name} ni joriy holati: Break — {duration} daqiqa.",
    "⏳ [{ts}] {name}: Dam olish vaqti — {duration} min davom etmoqda.",
    "📢 [{ts}] {name} Break: {duration} daqiqa.",
    "🔔 [{ts}] {name} haydovchisi hozir break olmoqda ({duration} min).",
]

# ─── PROFILE FORM ISSUE ───────────────────────────────────────────────────────

PROFILE_FORM_TEMPLATES = [
    "👤 [{ts}] {name} — Driver profile formida muammo: {issue}.",
    "⚠️ [{ts}] {name}: Profile form to'liq emas — {issue}.",
    "🔴 [{ts}] {name} uchun profile ogohlantirishi: {issue}.",
    "🚨 [{ts}] {name} ning driver profile formi noto'g'ri: {issue}.",
    "📋 [{ts}] {name} — Profile form muammosi: {issue}. Tekshiring.",
    "📢 [{ts}] {name}: Driver profile — {issue}.",
    "🟠 [{ts}] {name} uchun profile ogohlantirishi: {issue}.",
    "⚡ [{ts}] {name} ning profile formi: {issue}. Hal qiling.",
    "🔔 [{ts}] {name}: Profile form — {issue}.",
    "📉 [{ts}] {name} — Profile holati: {issue}.",
    "⏳ [{ts}] {name} haydovchisida profile muammosi: {issue}.",
    "🚦 [{ts}] {name} — Profile {issue}. Haydovchiga xabar bering.",
    "📌 [{ts}] {name}: Driver profile — {issue}.",
    "🟡 [{ts}] {name} profile ogohlantirish: {issue}.",
    "⚠️ [{ts}] {name} uchun profile form muammosi: {issue}.",
]

# ─── Public API ───────────────────────────────────────────────────────────────

def get_cycle_low_msg(name: str, hours: float) -> str:
    return _pick(CYCLE_LOW_TEMPLATES, ts=_ts(), name=name, hours=hours)

def get_drive_low_msg(name: str, hours: float) -> str:
    return _pick(DRIVE_LOW_TEMPLATES, ts=_ts(), name=name, hours=hours)

def get_break_low_msg(name: str, hours: float) -> str:
    return _pick(BREAK_LOW_TEMPLATES, ts=_ts(), name=name, hours=hours)

def get_shift_low_msg(name: str, hours: float) -> str:
    return _pick(SHIFT_LOW_TEMPLATES, ts=_ts(), name=name, hours=hours)

def get_document_incomplete_msg(name: str) -> str:
    return _pick(DOCUMENT_INCOMPLETE_TEMPLATES, ts=_ts(), name=name)

def get_disconnect_msg(name: str) -> str:
    return _pick(DISCONNECT_TEMPLATES, ts=_ts(), name=name)

def get_on_break_msg(name: str, duration: int) -> str:
    return _pick(ON_BREAK_TEMPLATES, ts=_ts(), name=name, duration=duration)

def get_profile_form_msg(name: str, issue: str) -> str:
    return _pick(PROFILE_FORM_TEMPLATES, ts=_ts(), name=name, issue=issue)
