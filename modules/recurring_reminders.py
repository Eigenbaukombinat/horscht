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
        bot.reply(event, f"❌ Ungültiger Wochentag: <b>{weekday_str}</b><br>Gültige Wochentage: montag, dienstag, mittwoch, donnerstag, freitag, samstag, sonntag", html=True)
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
        bot.reply(event, f"❌ Ungültiges Uhrzeitformat: <b>{time_str}</b><br>Bitte verwende das Format HH:MM (z.B. 14:30)", html=True)
        return
    
    # Get room information
    room_id = event['room_id']
    room = bot.client.rooms.get(room_id)
    room_alias = getattr(room, 'canonical_alias', room_id) if room else room_id
    sender = event['sender']
    
    # Create reminder object
    reminder = {
        'id': len(load_reminders()) + 1,
        'weekday': WEEKDAY_MAP[weekday_str],
        'weekday_name': weekday_str.capitalize(),
        'hour': hour,
        'minute': minute,
        'time_str': time_str,
        'message': reminder_text,
        'room_id': room_id,
        'room_alias': room_alias,
        'creator': sender,
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
👤 <b>Erstellt von:</b> {sender}<br><br>

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
        reminder_list += f"👤 Erstellt von: {reminder['creator']}<br><br>"
    
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
    sender = event['sender']
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
    
    # Check if user is the creator or has admin rights
    #if reminder_to_delete['creator'] != sender:
    #    # Allow room admins to delete any reminder (basic check by checking if user has sufficient power level)
    #    room = bot.client.rooms.get(room_id)
    #    if room:
    #        try:
    #            user_power = room.power_levels.get('users', {}).get(sender, 0)
    #            default_power = room.power_levels.get('users_default', 0)
    #            if user_power <= default_power:
    #                bot.reply(event, f"❌ Du kannst nur deine eigenen Reminder löschen.\nReminder #{reminder_id} wurde von {reminder_to_delete['creator']} erstellt.")
    #                return
    #        except:
    #            bot.reply(event, f"❌ Du kannst nur deine eigenen Reminder löschen.\nReminder #{reminder_id} wurde von {reminder_to_delete['creator']} erstellt.")
    #            return
    
    # Remove the reminder
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
    """Check if any reminders should be sent now or were missed recently."""
    
    now = datetime.datetime.now()
    
    # Load reminders and last check time
    reminders = load_reminders()
    last_check_file = "last_reminder_check.txt"
    
    # Get last check time
    last_check = None
    if os.path.exists(last_check_file):
        try:
            with open(last_check_file, 'r') as f:
                last_check_str = f.read().strip()
                if last_check_str:
                    last_check = datetime.datetime.fromisoformat(last_check_str)
        except (ValueError, IOError):
            pass
    
    # If no last check or more than 10 minutes ago, check for missed reminders
    if last_check is None:
        last_check = now - datetime.timedelta(minutes=5)  # Check last 5 minutes on first run
    
    # Create a list of time points to check (from last check to now)
    check_times = []
    current_check = last_check.replace(second=0, microsecond=0)
    end_time = now.replace(second=0, microsecond=0)
    
    while current_check <= end_time:
        check_times.append(current_check)
        current_check += datetime.timedelta(minutes=1)
    
    # Track which reminders we've already sent to avoid duplicates
    sent_reminders = set()
    
    for check_time in check_times:
        check_weekday = check_time.weekday()
        check_hour = check_time.hour
        check_minute = check_time.minute
        
        for reminder in reminders:
            # Create a unique identifier for this reminder at this time
            reminder_key = f"{reminder['id']}_{check_time.strftime('%Y%m%d_%H%M')}"
            
            # Skip if we already sent this reminder
            if reminder_key in sent_reminders:
                continue
            
            # Check if this reminder should fire at this time
            if (reminder['weekday'] == check_weekday and 
                reminder['hour'] == check_hour and 
                reminder['minute'] == check_minute):
                
                # Send the reminder to the appropriate room
                room_id = reminder['room_id']
                if room_id in bot.client.rooms:
                    room = bot.client.rooms[room_id]
                    
                    # Add timestamp if this is a catch-up reminder
                    time_info = ""
                    if check_time < now.replace(second=0, microsecond=0):
                        minutes_late = int((now - check_time).total_seconds() / 60)
                        if minutes_late > 0:
                            time_info = f" (verzögert um {minutes_late} Min.)"
                    
                    reminder_message = f"""🔔 <b>Reminder{time_info}</b><br><br>

{reminder['message']}<br><br>

<i>Erstellt von {reminder.get('creator', 'Unbekannt')}</i>"""
                    
                    try:
                        room.send_html(reminder_message)
                        sent_reminders.add(reminder_key)
                        print(f"Sent reminder {reminder['id']} for {check_time}")
                    except Exception as e:
                        print(f"Error sending reminder to room {room_id}: {e}")
    
    # Save current time as last check
    try:
        with open(last_check_file, 'w') as f:
            f.write(now.isoformat())
    except IOError:
        print(f"Warning: Could not save last check time to {last_check_file}")

# Register the commands and scheduled task
CMDS = {
    '!reminder': create_reminder
}

CRON = check_reminders
