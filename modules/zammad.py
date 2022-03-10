import json
import html
from contextlib import suppress
import requests



def get_seen_ids():
    with open("./seen_ids") as seen_file:
        content = seen_file.read()
    return set(content.strip().split("\n"))


def write_seen_ids(ids):
    content = "\n".join(str(element) for element in ids)
    with open("./seen_ids", "w") as seen_file:
        seen_file.write(content)


def zammad_get(url, config):
    response = requests.get(
        url=config["url"] + url,
        headers={"Authorization": 'Bearer %s' % config["token"]},
    )
    return response.json()


def get_unread_notifications(config):
    response = zammad_get("/api/v1/online_notifications", config)
    return [n for n in response if n["seen"] is False]


def send_notification(bot, ticket, ticket_id, config):
    found = False
    for room_id in bot.client.rooms:
        room = bot.client.rooms[room_id]
        if room.display_name == config['room']:
            found = True
            break
    # cook quote and send to room
    ticket_from = html.escape(ticket["from"]) 
    subj = html.escape(ticket["subject"])
    txt = '<b>Neues Zammad Ticket von:</b> <i>%s</i><br>' % ticket_from 
    txt += '"%s"<br>' % subj
    txt += 'URL: <a href="https://z.eigenbaukombinat.de/#ticket/zoom/%s">https://z.eigenbaukombinat.de/#ticket/zoom/%s</a>' % ( ticket_id, ticket_id )
    bot.send_html(room, txt)


def check_zammad(bot, config):
    """holt notifications vom zammad und postet sie in einen raum"""
    seen_ids = get_seen_ids()
    notifications = get_unread_notifications(config)
    new_seen_ids = set() 
    for notification in notifications:
        ticket_id = notification["o_id"]
        ticket = zammad_get('/api/v1/ticket_articles/by_ticket/%s' % ticket_id, config)[-0]
        if ticket["to"] != config["addr"]:
            continue
        if str(notification["id"]) not in seen_ids:
            send_notification(bot, ticket, ticket_id, config)
        new_seen_ids.add(notification["id"])
    write_seen_ids(new_seen_ids.union(seen_ids))


CRON = check_zammad
