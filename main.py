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

import colorlog

locale.setlocale(locale.LC_TIME, "")

handler = colorlog.StreamHandler()
colorlog.basicConfig(level=logging.DEBUG)
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

logger = colorlog.getLogger(__name__)
logger.propagate = False
logger.addHandler(handler)

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

        self.suspend_days = 0

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

        if msg["text"].startswith("/msg") and chat_id == int(CONFIG["notify_id"]):
            logger.info("sending message to all members")
            recievers = self.usermanager.get_all_users()
            for user_id in recievers:
                logging.debug("sending to %s", user_id)
                try:
                    yield from self.sendMessage(user_id, msg["text"][4:])
                except telepot.TelegramError:
                    logging.error("failed to send /msg to {}".format(user_id))
            logging.info("sent to all members")
            return

        if msg["text"].startswith("/disable") and chat_id == int(CONFIG["notify_id"]):
            days = int(msg["text"][9:])
            logger.info("disabling for %s days", days)
            self.suspend_days = days
            yield from self.sendMessage(CONFIG["notify_id"],
                    "suspending broadcast for {} more days".format(days))
            return

        if msg["text"].startswith("/start"):
            yield from self.sendMessage(chat_id,
                "Wilkommen beim GSVPlanBot!\n"
                "Gib eine Zahl ein, wie viele Tage in der zukunft du"
                "den VPlan erhalten willst. Z.B. 0 für heute, 1 für morgen\n\n"
                "bei Fragen und Problemen an Adrian (auf tg @notafile) wenden")
            return

        try:
            num = int(msg["text"])
        except ValueError:
            num = None
            message = "Error. Bitte gib eine Zahl ein. Z.B.: 0 für heute, "
            "1 für morgen etc."

        if num is not None:
            day = date.today() + timedelta(days=num)
            try:
                result = self.reader.get_day(day)
            except reader.NoSubstError:
                logger.info("no subst available for request")
                yield from self.sendMessage(chat_id, "Für diesen Tag ist keine Vertretung verfügbar")
                return
            except Exception as e:
                logger.exception("could not get")
                yield from self.sendMessage(chat_id, "Error - could not get")
                notification = "request failed:\n{}\n{}".format(msg, e)
                yield from self.sendMessage(CONFIG["notify_id"], notification)
                return

            result.data = [x for x in result.data if "Q" in x.grade and "3" in x.grade]

            logging.info(result.headers)
            logging.info(result.data)

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
        if self.suspend_days > 0:
            yield from self.sendMessage(CONFIG["notify_id"],
                    "{} days left".format(self.suspend_days))
            logger.info("%s days left in disable", self.suspend_days)
            self.suspend_days -= 1
            return

        recievers = self.usermanager.get_broadcasters()
        logging.debug("sending daily message to: %s", recievers)

        yield from self.sendMessage(CONFIG["notify_id"], "sending daily messages")
        logging.info("sending daily messages")

        day = date.today() + timedelta(days=1)
        try:
            result = self.reader.get_day(day)
        except:
            yield from self.sendMessage(CONFIG["notify_id"], "Error getting daily")
            return

        result.data = [x for x in result.data if "Q" in x.grade and "3" in x.grade]

        message = format_subst(result, day.strftime("%A, %d. %B"))

        for chat_id in recievers:
            try:
                yield from self.sendMessage(chat_id, message)
            except telepot.TelegramError:
                logging.error("could not send message to {}".format(chat_id))

        notification = "sent daily messages to {} users".format(len(recievers))
        yield from self.sendMessage(CONFIG["notify_id"], notification)
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
