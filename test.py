import unittest
import reader
import main
from datetime import date, datetime, timedelta
import sqlite3
import database
import os

CONFIG = {}

with open("../keyfile", "r") as f:
    for line in f:
        if not line.startswith("#") or line.strip() == "":
            key, value = line.split("=")
            CONFIG[key.strip()] = value.strip()

class ReaderTest(unittest.TestCase):
    def setUp(self):
        self.reader = reader.Reader(CONFIG["url"], (CONFIG["user"], CONFIG["pass"]))

    def test_simple_download(self):
        url = self.reader.url.format(weeknum=1)
        self.reader._download(url)

    def test_get_day(self):
        d = date(day=17, month=8, year=2016)
        day = self.reader.get_day(d)

    @unittest.skipIf(datetime.today().weekday() > 4,
            "skipping today on weekends")
    def test_get_today(self):
        d = date.today()
        day = self.reader.get_day(d)
        assert len(day.data) > 1


class SubstManagerTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.subst_manager = database.SubstManager(self.connection)
        self.subst_ex = ["test¹²⅛£¤¡'!\"\]", "test"]

    def test_day_hash(self):
        subst = ["test¹²⅛£¤¡'!\"\]", "test"]
        h1 = self.subst_manager.hash_subst(subst, date.today())
        h2 = self.subst_manager.hash_subst(subst, datetime.now().date())
        self.assertEqual(h1, h2)

    def test_new_subst(self):
        subst = ["test¹²⅛£¤¡'!\"\]", "test"]
        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertTrue(ret)

        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertFalse(ret)

        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertFalse(ret)

    def test_prune(self):
        subst = ["test¹²⅛£¤¡'!\"\]", "test"]

        self.subst_manager.check_new_and_register(
                subst, date.today())

        self.subst_manager.prune_older_than(date.today())

        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertFalse(ret)

        self.subst_manager.prune_older_than(date(1960, 1, 1))

        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertFalse(ret)

        self.subst_manager.prune_older_than(
                date.today() + timedelta(days=1))

        ret = self.subst_manager.check_new_and_register(
                subst, date.today())
        self.assertTrue(ret)

class UserManagerTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.users = database.UserManager(self.connection)

    def test_user_creation(self):
        self.users.create_user(192192219241265)
        self.assertTrue(self.users.is_user(192192219241265))

    def test_invalid_creation(self):
        self.users.create_user(11111119241265)
        self.assertFalse(self.users.is_user(222222219241265))

    def test_broadcast_query(self):
        self.users.create_user(10)
        self.assertEqual(len(self.users.get_broadcasters()), 0)
        self.assertNotIn(10, self.users.get_broadcasters())
        self.users.set_broadcast(10, True)
        self.assertEqual(len(self.users.get_broadcasters()), 1)
        self.assertIn(10, self.users.get_broadcasters())

class BroadcastTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.bot = main.VPlanBot("DUMMY_TOKEN")

    @unittest.skip
    def test_broadcast(self):
        usermanager = self.bot.usermanager
        usermanager.create_user(15)
        usermanager.set_broadcast(15, True)

        def override_send_message(chat_id, message):
            self.assertTrue(message)
            self.assertEqual(chat_id, 15)

        self.bot.broadcast_message =override_send_message

if __name__ == "__main__":
    unittest.main()
