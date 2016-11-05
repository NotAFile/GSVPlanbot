"""
Main module for the VPlanBot
"""
import locale
import logging
import asyncio
import time
from datetime import date, timedelta

import telepot
import telepot.async

import sqlite3

import aiocron

import reader
import database

locale.setlocale(locale.LC_TIME, "")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CONFIG = {}

with open("../keyfile", "r") as f:
    for line in f:
        if not line.startswith("#") or line.strip() == "":
            key, value = line.split("=")
            CONFIG[key.strip()] = value.strip()

def format_subst(subst, subst_date):
    """
    Formats a Subst object and adds a preformatted date
    """
    root = "Vertretungen für den {subst_date}\n\n{subst}\n\nNachrichten:\n{news}"
    sub = "\n".join([format_subst_row(i) for i in subst.data])
    news = "\n".join([" ".join(i) for i in subst.info])
    return root.format(subst_date=subst_date, subst=sub, news=news)

# SubstRecord(period='4', grade='Q12', teacher='Mu', lesson='pw76', room='D107', text='',
# orig_lesson='pw76', orig_room='D108')


def format_subst_row(row):
    """
    formats a specific SubstRecord as a single row
    """
    message = []
    message.append("In der {period}. Stunde".format(period=row.period))

    if row.lesson == "---":
        message.append(" fällt {lesson} aus".format(lesson=row.orig_lesson))

    else:
        if row.orig_room != row.room:
            message.append(" findet {lesson} in raum {room} statt".format(
                lesson=row.lesson, room=row.room))

        if row.lesson == row.orig_lesson and row.room == row.orig_room:
            message.append(" wird {lesson} von {teacher} vertreten".format(
                lesson=row.lesson, teacher=row.teacher))

    if len(message) < 2:
        return " ".join(row)

    if row.text != "":
        message.append(". Nachricht: „{}“".format(row.text))

    message.append(".")

    return "".join(message)


class VPlanBot(telepot.async.Bot):
    """
    Main class of the VPlanBot
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.reader = reader.Reader(CONFIG["url"], (CONFIG["user"], CONFIG["pass"]))

        @aiocron.crontab("0 18 * * 0-4")
        #@aiocron.crontab("* * * * * */5")
        @asyncio.coroutine
        def on_broadcast_timer():
            yield from self.broadcast_message()

        self.connection = sqlite3.connect("users.db")
        self.usermanager = database.UserManager(self.connection)

    @asyncio.coroutine
    def on_chat_message(self, msg):
        """
        Function called on message arrival
        """
        starttime = time.time()
        content_type, chat_type, chat_id = telepot.glance(msg)

        logger.info("%s %s message from %s", chat_type, content_type, chat_id)

        logger.debug(msg)

        if not self.usermanager.is_user(chat_id):
            self.usermanager.create_user(chat_id)

        # ideally I would use msg.entities, but I'm a lazy fuck
        if msg["text"].startswith("/broadcast"):
            self.usermanager.set_broadcast(chat_id, True)
            yield from self.sendMessage(chat_id,
                "Du wirst in Zukunft jeden Tag um 20:00 den Stundenplan erhalten")
            return

        try:
            num = int(msg["text"])
        except ValueError:
            num = None
            message = "Error"

        if num is not None:
            day = date.today() + timedelta(days=num)
            try:
                result = self.reader.get_day(day)
            except:
                yield from self.sendMessage(chat_id, "Error - could not get")
                return

            result.data = [x for x in result.data if "Q" in x.grade and "3" in x.grade]

            message = format_subst(result, day.strftime("%A, %d. %B"))

        logger.info("Sending message - %ss", time.time()-starttime)
        yield from self.sendMessage(chat_id, message)
        logger.info("Sent message - %s", time.time()-starttime)

    @asyncio.coroutine
    def send_timetable(self):
        """
        Stub method to send the timetable — not implemented yet due to lazyness
        """

    @asyncio.coroutine
    def broadcast_message(self):
        recievers = self.usermanager.get_broadcasters()
        print(recievers)

        yield from self.sendMessage(219241265, "sending daily messages")
        print("sending daily messages")

        day = date.today() + timedelta(days=1)
        try:
            result = self.reader.get_day(day)
        except:
            yield from self.sendMessage(219241265, "Error getting daily")
            return

        result.data = [x for x in result.data if "Q" in x.grade and "3" in x.grade]

        message = format_subst(result, day.strftime("%A, %d. %B"))

        for chat_id in recievers:
            yield from self.sendMessage(chat_id, message)

        notification = "sent daily messages to {} users".format(len(recievers))
        yield from self.sendMessage(219241265, notification)
        logger.info(notification)

    @asyncio.coroutine
    def on_start(self, glance, msg):
        """
        Method run when the /start command is recieved
        """
        yield from self.sendMessage(glance[2], "Hallo {name}".format(
            name=msg["from"]["first_name"]))

if __name__ == "__main__":
    bot = VPlanBot(CONFIG["token"])

    loop = asyncio.get_event_loop()

    loop.create_task(bot.messageLoop())

    logger.info("Listening for messages...")
    loop.run_forever()