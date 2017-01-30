"""
Database Module. Used to manage users and their settings
"""

import sqlite3
import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

class SubstManager:
    def __init__(self, connection):
        """
        connection: SQLITE database connection
        """
        self.conn = connection
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS messages("
                         "id INTEGER PRIMARY KEY,"
                         "hash TEXT NOT NULL,"
                         "time INT NOT NULL);")

    @staticmethod
    def hash_subst(subst, date) -> str:
        d_fmt = date.strftime("%Y%j") # %Y = year ("2016"), %j = day ("129")
        prehash = "".join(subst) + d_fmt
        return hashlib.md5(prehash.encode("utf-8")).digest()

    def check_new_and_register(self, subst, date):
        subst_hash = SubstManager.hash_subst(subst, date)
        self.cur.execute("SELECT id FROM messages WHERE hash=?", (subst_hash, ))
        res = self.cur.fetchone()

        if res is None:
            self.cur.execute("INSERT INTO messages(hash,time) VALUES (?, ?)",
                            (subst_hash, date.strftime("%s")))
            return True
        else:
            return False

    def prune_older_than(self, date):
        """
        DELETEs any records in the db that have a time < date
        """
        self.cur.execute("DELETE FROM messages WHERE time < ?",
                         (date.strftime("%s"),)) # %s: UNIX epoch

class User:
    pass

class Subject:
    @classmethod
    def new_subject(sub_id: str, human_name: str=None):
        pass
    pass

class UserManager:
    def __init__(self, connection):
        """
        connection: SQLITE database connection
        """
        self.conn = connection
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS "
        "users(id INTEGER PRIMARY KEY, recieve_broadcast BOOLEAN);")
        self.conn.commit()

    def is_user(self, chat_id):
        self.cur.execute("SELECT * FROM users WHERE id=?;", (chat_id,))
        return self.cur.fetchone() is not None

    def get_broadcasters(self):
        self.cur.execute("SELECT id FROM users WHERE recieve_broadcast=1")
        return [i[0] for i in self.cur.fetchall()]

    def get_all_users(self):
        self.cur.execute("SELECT id FROM users")
        return [i[0] for i in self.cur.fetchall()]

    def set_broadcast(self, chat_id, b):
        self.cur.execute("UPDATE users SET recieve_broadcast=? WHERE id=?",
                (b, chat_id))
        self.conn.commit()

    def create_user(self, chat_id):
        logger.info("created new user {}".format(chat_id))
        self.cur.execute("INSERT INTO users VALUES (?, ?)", (chat_id, False))
        self.conn.commit()

    def get_subjects(self, chat_id):
        raise NotImplementedError
        self.cur.execute("SELECT * FROM users_lessons where id=?",
                (chat_id,))
