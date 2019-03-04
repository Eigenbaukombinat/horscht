def quote(event, message, bot, args):
    """Sendet den übergebenen Text als Zitat in einen Raum (!quote <zielraum> <text>)"""
    if len(args) < 2:
        bot.reply(event, 'Bitte den Raumnamen und einen Text angeben.')
        return

    # search given room
    roomname = args[0]    
    found = False
    for room_id in bot.client.rooms:
        room = bot.client.rooms[room_id]
        if room.display_name == roomname:
            found = True
            break
    
    if not found:
        bot.reply(event, 'Raum {} nicht gefunden.'.format(roomname))
        return

    # cook quote and send to room
    txt = " ".join(args[1:]).replace('\n', '<br/>')
    repl = '<blockquote>{}</blockquote>'.format(txt)
    room.send_html(repl)


CMDS = {'!quote': quote}
