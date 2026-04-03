"""
15 message variants per alert type — cycles through them to avoid Telegram spam filters.
"""

import random

VIOLATION_OVERTIME = [
    "🚨 {name} — you are exceeding your allowed drive time. Pull over safely and stop driving immediately.",
    "⛔ DRIVE TIME EXCEEDED — {name}, you've gone over your allowed hours. Stop driving now and log your break.",
    "🔴 {name}: Drive time violation detected. You are over your permitted hours. Find a safe spot and stop.",
    "‼️ Overtime alert for {name}. You are driving beyond the legal limit. Please park immediately.",
    "🚫 {name}, your drive time has exceeded FMCSA limits. Immediate stop required — find a safe location.",
    "⚠️ Hours violation — {name} has surpassed the maximum drive time. Stop driving and begin rest period.",
    "🔔 {name}: You've exceeded your drive hours. This is a serious violation. Please stop the vehicle now.",
    "ALERT: {name} is over drive time limits. Parking immediately is required to avoid further violations.",
    "📍 {name} — drive time exceeded. Pull over at the nearest safe stop. This cannot be delayed.",
    "🛑 {name}, you've crossed the drive time threshold. Stop now. Log your rest break immediately.",
    "FMCSA violation: {name} has exceeded drive time. Immediate action needed — stop driving now.",
    "🚛 {name}: Over-hours alert. Your current drive time violates federal regulations. Please stop.",
    "⏰ {name} — time's up. You've driven beyond your allowed limit. Safely park and start rest period.",
    "Critical: Drive hours exceeded for {name}. Stop the vehicle immediately and contact dispatch.",
    "🔴 Driving time limit breached — {name}, please find a truck stop or rest area right now.",
]

VIOLATION_NO_PTI = [
    "⚠️ {name} — you went on duty without completing your Pre-Trip Inspection. Please complete PTI now.",
    "🔔 {name}: PTI not found. A Pre-Trip Inspection is required before driving. Complete it in the app.",
    "📋 {name} — your Pre-Trip Inspection is missing. Please complete your PTI log right away.",
    "🚨 PTI Alert for {name}: No pre-trip inspection recorded. This is a DOT requirement — complete now.",
    "‼️ {name}, driving without a completed PTI is a violation. Please fill out your pre-trip inspection.",
    "🔴 {name}: Pre-Trip Inspection not completed. Log your PTI before continuing to drive.",
    "ALERT — {name} has not completed a Pre-Trip Inspection. Required by FMCSA. Do it in ELD app now.",
    "📝 {name}: Missing PTI. Pre-trip inspections are mandatory. Please complete yours immediately.",
    "⛔ {name} — no Pre-Trip Inspection on file for today. Please complete PTI in your ELD app.",
    "🛡️ {name}, safety reminder: PTI not completed. Take a few minutes to do your pre-trip inspection.",
    "⚠️ Pre-trip inspection missing for {name}. This is required before every drive. Complete it ASAP.",
    "🔔 {name}: Your PTI is overdue. A Pre-Trip Inspection must be done before operating the vehicle.",
    "📋 {name} — ELD shows no PTI completed. Please open the app and submit your pre-trip inspection.",
    "Missing PTI: {name} needs to complete a Pre-Trip Inspection. Required by law — do it now.",
    "🚛 {name}: No pre-trip inspection recorded today. Complete your PTI to stay compliant.",
]

HOS_SHIFT_LOW = [
    "⏳ {name} — shift time is running low. Only {time} left in your 14-hour window. Plan your stop.",
    "🕐 {name}: {time} left on your shift clock. Start looking for a place to rest soon.",
    "⚠️ Shift time alert — {name}, you have {time} remaining. Find a spot to park soon.",
    "🔔 {name}: Shift window nearly over. {time} left. Wrap up and find a safe stop.",
    "📍 {name} — only {time} on your 14-hour shift. Begin planning your rest stop now.",
    "⏰ Heads up {name}: shift expires in {time}. Locate a truck stop or rest area soon.",
    "🟡 {name}, shift clock warning: {time} left. You need to be parked before your shift ends.",
    "SHIFT ALERT: {name} has {time} left in current shift. Pull over before time expires.",
    "🔴 {name}: {time} on your shift. Start end-of-day routine and find parking.",
    "⚠️ Time check for {name} — 14-hour shift has {time} left. Don't push it — find rest now.",
    "🕑 {name}: Shift ends in {time}. Head toward a safe stopping point.",
    "⏳ SHIFT LOW — {name}, {time} left. Stop driving before your shift clock hits zero.",
    "📢 {name}: {time} remaining. Begin winding down and looking for a stop.",
    "🟠 Shift warning for {name}: {time} left. Plan your route to a rest area immediately.",
    "⚠️ {name} — shift clock at {time}. Get to safe parking before your shift expires.",
]

HOS_DRIVE_LOW = [
    "⏳ {name} — only {time} of drive time left. Start planning your 30-min break or final stop.",
    "🕐 {name}: Drive clock at {time}. Consider taking your break now to reset.",
    "⚠️ Drive time low for {name}. {time} remaining before you must stop. Plan accordingly.",
    "🔔 {name}: {time} left on drive clock. Take your 30-minute break to stay compliant.",
    "📍 {name} — drive time almost up. {time} remaining. Find a safe place to stop.",
    "⏰ {name}: Your 11-hour limit has {time} left. Start your break planning now.",
    "🟡 Drive alert — {name}, {time} of drive time left. Don't wait too long to stop.",
    "DRIVE LOW: {name} has {time} remaining. Locate a rest stop ahead.",
    "🔴 {name}: {time} of drive time left. Stop soon — look for parking.",
    "⚠️ {name} — drive clock warning. {time} left. Stop at the next available rest area.",
    "🕑 {name}: Only {time} left to drive. Take your required break before time runs out.",
    "⏳ DRIVE TIME — {name}, {time} remaining. Begin your rest break to stay within limits.",
    "📢 {name}: Drive time almost exhausted. {time} left. Park and take your 30-minute break.",
    "🟠 {name}: Drive hours low — {time} remaining. Find a safe stop.",
    "⚠️ {name} — drive limit approaching. {time} left. Time to pull over and take a break.",
]

HOS_BREAK_LOW = [
    "⏳ {name}: Only {time} left before a 30-min break is required. Plan your stop.",
    "🔔 {name} — break clock reminder. {time} left before mandatory 30-minute break.",
    "⚠️ {name}: Break window closing in {time}. Schedule your 30-minute break soon.",
    "📋 {name}: {time} before mandatory break. Plan your stop — 30 min off duty needed.",
    "🕐 Break alert for {name}: {time} remaining before required 30-minute break.",
    "🟡 {name} — take a 30-minute break in {time}. Find a good spot and plan your stop.",
    "BREAK REMINDER: {name} must take a 30-min break in {time}.",
    "⏰ {name}: Break window expires in {time}. A 30-minute off-duty break is coming up.",
    "🔴 {name}: {time} until mandatory break. Pull over for 30-minute rest to stay legal.",
    "📍 {name} — break needed in {time}. Find a truck stop for your required 30-minute break.",
    "⚠️ {name}: Only {time} left in your break window. Schedule your stop ahead of time.",
    "🕑 Heads up {name}: {time} before mandatory 30-min break. Make sure you can stop safely.",
    "⏳ {name}: Break clock running out — {time} left. Don't drive past your mandatory break.",
    "📢 {name}: Required break in {time}. Find safe parking and take your 30-minute rest.",
    "🟠 {name} — break window closing. {time} remaining. Take your 30-min break before driving further.",
]

HOS_CYCLE_LOW = [
    "⚠️ {name}: Your 70-hour cycle has {time} left. Approaching your weekly limit.",
    "🔴 {name} — cycle time alert. Only {time} left in your 8-day cycle. Coordinate with dispatch.",
    "⏳ {name}: Cycle clock running low — {time} remaining. Plan your schedule accordingly.",
    "🔔 Heads up {name}: {time} left on your weekly cycle. You'll need reset time soon.",
    "📋 {name}: Cycle limit approaching. {time} remaining before 34-hour restart may be needed.",
    "🕐 {name} — only {time} left in your 70-hour/8-day cycle. Plan rest with dispatch.",
    "⚠️ CYCLE WARNING — {name}: {time} remaining. Contact dispatch for schedule.",
    "📍 {name}: Cycle almost full. {time} left. A 34-hour restart may be needed soon.",
    "🟠 {name}: Cycle time running low — {time} left. Review upcoming trips with dispatch.",
    "⏰ {name} — weekly cycle alert: {time} remaining. Plan your rest period.",
    "CYCLE LOW: {name} has {time} left in the 70-hour window. Dispatch coordination needed.",
    "🔴 {name}: {time} of cycle time left. You'll be due for a 34-hour reset soon.",
    "⚠️ {name} — cycle clock at {time}. Plan ahead for your mandatory reset period.",
    "📢 {name}: Only {time} remaining in your weekly cycle. Schedule your 34-hour restart.",
    "🟡 {name}: Cycle warning — {time} left in the 8-day window. Talk to dispatch about schedule.",
]

DRIVER_DISCONNECT = [
    "📵 {name} — your ELD device appears disconnected. Please check your device and reconnect.",
    "🔌 DISCONNECT ALERT: {name}'s ELD is offline. Reconnect your device as soon as possible.",
    "⚠️ {name}: ELD connection lost. Make sure your device is plugged in and Bluetooth is on.",
    "🔴 {name} — ELD device not communicating. Check tablet/phone and reconnect to the truck.",
    "📡 Connection lost for {name}. Your ELD is showing offline. Please reconnect immediately.",
    "❌ {name}: ELD offline detected. Check your device connection — Bluetooth or cable may be loose.",
    "DISCONNECT: {name}'s ELD has gone offline. Reconnect your device to resume logging.",
    "🔌 {name} — device disconnected from ELD. Check hardware and reconnect ASAP.",
    "⚠️ {name}: No ELD signal. Check if your device is connected to the ECM port.",
    "📵 ELD disconnect for {name}. Reconnect your device to stay compliant.",
    "🔴 {name} — ELD showing offline status. Please reconnect your tablet/device now.",
    "📡 {name}: Connection to ELD lost. Ensure device is paired and connected properly.",
    "❌ ELD offline — {name}, check your device. Make sure it's connected to truck ECM.",
    "ALERT: {name}'s ELD is disconnected. Reconnect before driving further.",
    "🔌 {name} — ELD not responding. Check connection, restart app if needed.",
]

STATUS_STUCK_ON_DUTY = [
    "👋 {name} — you've been On Duty (not driving) for {duration}. Everything okay? Update your status when ready.",
    "🤙 {name}: Still On Duty for {duration}. If loading or waiting — that's fine! Just checking in.",
    "📋 {name} — on duty for {duration}. Just a check-in. Update your ELD status when things change.",
    "👀 Hey {name}, you've been in On Duty status for {duration}. Let us know everything's good!",
    "✅ Status check for {name}: On Duty for {duration}. If status changed, update in the app.",
    "🟡 {name} — On Duty for {duration}. Just making sure everything is okay with you.",
    "📍 {name}: {duration} in On Duty. If situation changed, please update your ELD.",
    "🤝 Checking in on {name} — On Duty for {duration}. Please update your status if changed.",
    "⏰ {name} has been On Duty for {duration}. Status update appreciated when available.",
    "👋 Hi {name}! Check-in — you've been On Duty for {duration}. How's it going?",
    "📞 {name} — {duration} in On Duty. All good? Update your status in ELD when ready.",
    "🔔 {name}: On Duty check-in. {duration} in this status. Please update when done.",
    "✅ Status reminder for {name}: {duration} as On Duty. Change when situation changes.",
    "👀 {name} — still On Duty after {duration}. Please update your status when you can.",
    "🤙 Hey {name}, {duration} on On Duty. Just checking in — update ELD when ready!",
]

PROFILE_STALE = [
    "📝 {name} — your profile/form has not been updated in {days} days. Please review and update your BOL.",
    "🗂️ {name}: Form data unchanged for {days} days. Please check and update your Bill of Lading.",
    "📋 Reminder for {name}: Profile form is {days} days old. Please update your BOL.",
    "🔔 {name} — no form updates in {days} days. If you have new load info, update your BOL now.",
    "📄 {name}: Your form hasn't been updated since {days} days ago. Please update BOL details.",
    "✏️ Update needed — {name}, profile form is {days} days unchanged. Please update your BOL.",
    "🗃️ {name}: Form data is {days} days old. If load details changed, please update your BOL.",
    "📝 {name} — {days}-day form reminder. Take a few minutes to review and update your BOL.",
    "📋 BOL Update: {name}, form hasn't changed in {days} days. Please verify and update.",
    "🔔 {name}: {days} days since last form update. Check your profile and update the BOL.",
    "📄 Form check for {name}: {days} days no updates. Please review your BOL and make changes.",
    "✏️ {name} — reminder: form data is {days} days unchanged. Please update your BOL.",
    "🗂️ {name}: Profile form reminder — {days} days since last update. Update your BOL now.",
    "📝 BOL reminder for {name}: update your form — not changed in {days} days.",
    "🔔 Update request for {name}: {days} days since form update. Review and update BOL.",
]

CERTIFICATION_MISSING = [
    "✍️ {name} — your logs have not been certified. Please certify your ELD logs in the app.",
    "📋 {name}: Log certification required. Open your ELD app and certify your recent logs.",
    "🔔 Certification needed — {name}, your ELD logs are not certified. Please do this now.",
    "⚠️ {name}: Uncertified logs detected. Please certify your logs in the ELD app immediately.",
    "✅ {name} — your logs need certification. Open the app and certify to stay compliant.",
    "📝 Reminder for {name}: Certify your ELD logs. Required under FMCSA regulations.",
    "🔴 {name}: Log certification missing. Please certify recent ELD logs as soon as possible.",
    "CERTIFY LOGS: {name}, ELD logs are pending certification. Please certify them now.",
    "✍️ {name} — certify logs reminder. Open ELD app and certify your daily records.",
    "📋 {name}: Logs from past day(s) need certification. Please do so in your ELD app.",
    "⚠️ {name}: ELD certification required. Uncertified logs cause violations — certify now.",
    "✅ Certification alert for {name}: ELD logs need your signature. Please certify ASAP.",
    "🔔 {name} — certify logs: Open ELD app → Logs → Certify. Takes under a minute.",
    "📝 {name}: Logs uncertified for {days} day(s). Required daily — please certify now.",
    "LOGS: {name}, certify your ELD records. Required by FMCSA — open app and certify.",
]

ALERT_TEMPLATES = {
    "violation_overtime":    VIOLATION_OVERTIME,
    "violation_no_pti":      VIOLATION_NO_PTI,
    "hos_shift_low":         HOS_SHIFT_LOW,
    "hos_drive_low":         HOS_DRIVE_LOW,
    "hos_break_low":         HOS_BREAK_LOW,
    "hos_cycle_low":         HOS_CYCLE_LOW,
    "driver_disconnect":     DRIVER_DISCONNECT,
    "status_stuck_on_duty":  STATUS_STUCK_ON_DUTY,
    "profile_stale":         PROFILE_STALE,
    "certification_missing": CERTIFICATION_MISSING,
}


def get_message(alert_type: str, **kwargs) -> str:
    templates = ALERT_TEMPLATES.get(alert_type, [])
    if not templates:
        raise ValueError(f"Unknown alert type: {alert_type}")
    return random.choice(templates).format(**kwargs)


def get_message_at_index(alert_type: str, index: int, **kwargs) -> str:
    templates = ALERT_TEMPLATES.get(alert_type, [])
    if not templates:
        raise ValueError(f"Unknown alert type: {alert_type}")
    return templates[index % len(templates)].format(**kwargs)
