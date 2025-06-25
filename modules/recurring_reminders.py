"""
Recurring Reminders Module for horscht bot

Allows room members to create recurring reminders that are sent at specific days and times.
Usage: !reminder <weekday> <time> <message>
Example: !reminder monday 14:30 Team meeting in conference room

Supports weekdays in German: montag, dienstag, mittwoch, donnerstag, freitag, samstag, sonntag
Time format: HH:MM (24-hour format)
"""

import datetime
import json
import os
import html

# File to store reminders persistently
REMINDERS_FILE = "reminders.json"

# German weekday mapping
WEEKDAY_MAP = {
    'montag': 0,
    'dienstag': 1,
    'mittwoch': 2,
    'donnerstag': 3,
    'freitag': 4,
    'samstag': 5,
    'sonntag': 6,
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6
}

def load_reminders():
    """Load reminders from JSON file."""
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_reminders(reminders):
    """Save reminders to JSON file."""
    try:
        with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)
    except IOError:
        print(f"Error: Could not save reminders to {REMINDERS_FILE}")

def create_reminder(event, message, bot, args, config):
    """Create a new recurring reminder."""
    
    # Handle special commands
    if args and args[0].lower() == 'list':
        list_reminders(event, message, bot, args, config)
        return
    
    if args and args[0].lower() == 'delete':
        delete_reminder(event, message, bot, args, config)
        return
    
    if not args or len(args) < 3:
        help_text = """
📅 <b>Recurring Reminder erstellen</b><br><br>

<b>Verwendung:</b> <code>!reminder &lt;wochentag&gt; &lt;uhrzeit&gt; &lt;nachricht&gt;</code><br><br>

<b>Beispiele:</b><br>
• <code>!reminder montag 09:00 Team-Meeting im Konferenzraum</code><br>
• <code>!reminder freitag 17:30 Arbeitszeit-Ende!</code><br>

<b>Wochentage:</b> montag, dienstag, mittwoch, donnerstag, freitag, samstag, sonntag<br>
<b>Uhrzeitformat:</b> HH:MM (24-Stunden-Format)<br><br>

<b>Weitere Befehle:</b><br>
• <code>!reminder list</code> - Alle Reminder anzeigen<br>
• <code>!reminder delete &lt;nummer&gt;</code> - Reminder löschen
"""
        bot.reply(event, help_text, html=True)
        return
    
    weekday_str = args[0].lower()
    time_str = args[1]
    reminder_text = ' '.join(args[2:])
    
    # Validate weekday
    if weekday_str not in WEEKDAY_MAP:
        bot.reply(event, f"❌ Ungültiger Wochentag!<br>Gültige Wochentage: montag, dienstag, mittwoch, donnerstag, freitag, samstag, sonntag", html=True)
        return
    
    # Validate time format
    try:
        time_parts = time_str.split(':')
        if len(time_parts) != 2:
            raise ValueError("Invalid time format")
        
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Time out of range")
            
    except ValueError:
        bot.reply(event, f"❌ Ungültiges Uhrzeitformat!<br>Bitte verwende das Format HH:MM (z.B. 14:30)", html=True)
        return
    
    # Get room information
    room_id = event['room_id']
    room = bot.client.rooms.get(room_id)
    room_alias = getattr(room, 'canonical_alias', room_id) if room else room_id
    
    # Sanitize reminder_text to prevent HTML and JSON injection
    # 1. Escape HTML to prevent HTML injection in output
    safe_reminder_text = html.escape(reminder_text)
    # 2. Remove control characters that could break JSON structure
    # (e.g., newlines, carriage returns, null bytes, etc.)
    safe_reminder_text = ''.join(
        c for c in safe_reminder_text if c >= ' ' and c not in {'\x00', '\x1f', '\x7f'}
    )

    # Create reminder object
    reminder = {
        'id': len(load_reminders()) + 1,
        'weekday': WEEKDAY_MAP[weekday_str],
        'weekday_name': weekday_str.capitalize(),
        'hour': hour,
        'minute': minute,
        'time_str': f'{hour:02d}:{minute:02d}',
        'message': safe_reminder_text,
        'room_id': room_id,
        'room_alias': room_alias,
        'created_at': datetime.datetime.now().isoformat()
    }
    
    # Load existing reminders and add the new one
    reminders = load_reminders()
    reminders.append(reminder)
    save_reminders(reminders)
    
    # Confirm creation
    confirmation = f"""
✅ <b>Reminder erstellt!</b><br><br>

📅 <b>Wochentag:</b> {reminder['weekday_name']}<br>
🕐 <b>Uhrzeit:</b> {reminder['time_str']}<br>
💬 <b>Nachricht:</b> {reminder['message']}<br>

Der Reminder wird jeden {reminder['weekday_name']} um {reminder['time_str']} in diesem Raum gesendet.
"""
    
    bot.reply(event, confirmation, html=True)

def list_reminders(event, message, bot, args, config):
    """List all reminders for the current room."""
    
    room_id = event['room_id']
    reminders = load_reminders()
    
    # Filter reminders for this room
    room_reminders = [r for r in reminders if r['room_id'] == room_id]
    
    if not room_reminders:
        bot.reply(event, "📅 Keine Reminder für diesen Raum gefunden.<br><br>Erstelle einen neuen Reminder mit: <code>!reminder &lt;wochentag&gt; &lt;uhrzeit&gt; &lt;nachricht&gt;</code>", html=True)
        return
    
    reminder_list = "📅 <b>Aktive Reminder für diesen Raum:</b><br><br>"
    
    for reminder in room_reminders:
        reminder_list += f"<b>#{reminder['id']}</b> - {reminder['weekday_name']} um {reminder['time_str']}<br>"
        reminder_list += f"💬 {reminder['message']}<br>"
    
    reminder_list += "<b>Tipp:</b> Verwende <code>!reminder delete &lt;nummer&gt;</code> um einen Reminder zu löschen."
    
    bot.reply(event, reminder_list, html=True)

def delete_reminder(event, message, bot, args, config):
    """Delete a reminder by ID."""
    
    if len(args) < 2:
        bot.reply(event, "❌ Bitte gib die Nummer des zu löschenden Reminders an.<br>Beispiel: <code>!reminder delete 1</code><br><br>Verwende <code>!reminder list</code> um alle Reminder anzuzeigen.", html=True)
        return
    
    try:
        reminder_id = int(args[1])
    except ValueError:
        bot.reply(event, "❌ Ungültige Reminder-Nummer. Bitte gib eine Zahl an.", html=True)
        return
    
    room_id = event['room_id']
    reminders = load_reminders()
    
    # Find the reminder to delete
    reminder_to_delete = None
    for reminder in reminders:
        if reminder['id'] == reminder_id and reminder['room_id'] == room_id:
            reminder_to_delete = reminder
            break
    
    if not reminder_to_delete:
        bot.reply(event, f"❌ Reminder #{reminder_id} nicht gefunden oder nicht in diesem Raum vorhanden.", html=True)
        return
    
    reminders = [r for r in reminders if not (r['id'] == reminder_id and r['room_id'] == room_id)]
    save_reminders(reminders)
    
    confirmation = f"""
✅ <b>Reminder gelöscht!</b><br><br>

📅 <b>Wochentag:</b> {reminder_to_delete['weekday_name']}<br>
🕐 <b>Uhrzeit:</b> {reminder_to_delete['time_str']}<br>
💬 <b>Nachricht:</b> {reminder_to_delete['message']}
"""
    
    bot.reply(event, confirmation, html=True)

def check_reminders(bot, config):
    """Check if any reminders should be sent now."""
    
    now = datetime.datetime.now()
    current_minute = now.replace(second=0, microsecond=0)
    
    # Load reminders
    reminders = load_reminders()
    
    # File to track sent reminders to prevent duplicates
    sent_file = "sent_reminders_today.json"
    today_str = now.strftime('%Y-%m-%d')
    
    # Load today's sent reminders
    sent_today = {}
    if os.path.exists(sent_file):
        try:
            with open(sent_file, 'r') as f:
                data = json.load(f)
                # Only keep today's data, clean up old entries
                if data.get('date') == today_str:
                    sent_today = data.get('sent', {})
        except (json.JSONDecodeError, IOError):
            pass
    
    current_weekday = current_minute.weekday()
    current_hour = current_minute.hour
    current_minute_val = current_minute.minute
    
    newly_sent = []
    
    for reminder in reminders:
        # Check if this reminder should fire right now
        if (reminder['weekday'] == current_weekday and 
            reminder['hour'] == current_hour and 
            reminder['minute'] == current_minute_val):
            
            # Create unique key for this reminder today
            reminder_key = f"{reminder['id']}_{current_minute.strftime('%H:%M')}"
            
            # Skip if already sent today at this time
            if reminder_key in sent_today:
                continue
            
            # Send the reminder to the appropriate room
            room_id = reminder['room_id']
            if room_id in bot.client.rooms:
                room = bot.client.rooms[room_id]
                
                reminder_message = f"""🔔 <b>Reminder</b><br><br>

{reminder['message']}"""
                
                try:
                    room.send_html(reminder_message)
                    sent_today[reminder_key] = current_minute.isoformat()
                    newly_sent.append(reminder['id'])
                    print(f"Sent reminder {reminder['id']} at {current_minute}")
                except Exception as e:
                    print(f"Error sending reminder to room {room_id}: {e}")
    
    # Save updated sent reminders if any were sent
    if newly_sent:
        try:
            with open(sent_file, 'w') as f:
                json.dump({
                    'date': today_str,
                    'sent': sent_today
                }, f, indent=2)
        except IOError:
            print(f"Warning: Could not save sent reminders to {sent_file}")

# Register the commands and scheduled task
CMDS = {
    '!reminder': create_reminder
}

CRON = check_reminders
