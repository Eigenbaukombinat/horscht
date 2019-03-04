def quote(event, message, bot, args):
    """Sendet den übergebenen Text als Zitat in einen Raum (!quote <zielraum> <text>)"""
    if len(args) < 2:
        bot.reply(event, 'Bitte den Raumnamen und einen Text angeben.')
    
    roomname = args[0]

    txt = " ".join(args[1:]).replace('\n', '<br/>')
    repl = '<blockquote>{}</blockquote>'.format(txt)
    
    found = False
    for room_id in bot.client.rooms:
        room = bot.client.rooms[room_id]
        if room.display_name == roomname:
            found = True
            break
    
    if found:
        room.send_html(repl)
    else:
        bot.reply(event, 'Raum {} nicht gefunden.'.format(roomname))

CMDS = {'!quote': quote}
