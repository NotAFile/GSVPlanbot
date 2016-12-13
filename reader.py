"""
Module to download substitutions from the UNITS substitution system
"""
from bs4 import BeautifulSoup
from datetime import datetime
from collections import namedtuple
import time

import requests

import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)

Record = namedtuple("SubstRecord",
        ["period", "grade", "teacher", "lesson", "room", "text", "orig_teacher", "orig_lesson", "orig_room"])

class MWT(object):
    """Memoize With Timeout"""
    _caches = {}
    _timeouts = {}

    def __init__(self,timeout=2):
        self.timeout = timeout

    def collect(self):
        """Clear cache of results which have timed out"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() - self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = sorted(kwargs.items())
            key = (args, tuple(kw))
            try:
                v = self.cache[key]
                logger.debug("request served from cache")
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except KeyError:
                logger.debug("request missed cache")
                v = self.cache[key] = f(*args,**kwargs),time.time()
                self.collect()
            return v[0]
        func.func_name = f.__name__

        return func

class RequestError(Exception):
    """
    Error that occurs if an ivalid substitution is requested
    """

class NoSubstError(RequestError):
    """
    Error that occurs if an ivalid substitution is requested
    """

class Reader:
    """
    Reader objecs are used to request subsitutions from a specific instance of UNITS
    """
    def __init__(self, url, auth):
        """
        url: URL with {weeknum:02} formatting to insert week number
        auth: (username, password)
        """
        self.url = url
        self.auth = auth

    @asyncio.coroutine
    def fetch(self, url):
        """
        Fetches the UNTIS website with auth
        """
        b_auth = aiohttp.BasicAuth(self.auth)
        with aiohttp.ClientSession(auth=b_auth) as session:
            with session.get(url) as response:
                print(response.status)

    def get_day(self, date) -> list:
        """
        gets the substitutions for a specific day
        """
        weeknum = date.isocalendar()[1]
        weekday = date.weekday()

        url = self.url.format(weeknum=weeknum)

        vplan = self._parse_page(self._download(url))

        try:
            res = find(vplan)[weekday]
        except IndexError:
            raise NoSubstError("No substitution for this day")

        return res

    def _next_schoolday(self, day):
        """
        gets the next schoolday after a date
        """
        pass

    def _parse_page(self, page):
        """
        parses the substitution HTML
        """
        soup = BeautifulSoup(page, "lxml")

        vertretung = soup.find(id="vertretung")

        if vertretung is None:
            raise RequestError(
                "no vertretung found. Check if site layout has changed, or an"
                "error has occurred while getting page")

        return vertretung
    @MWT(timeout=60*15)
    def _download(self, url):
        """
        Downloads the substitution table HTML at a certain URL
        """
        try:
            result = requests.get(url, auth=self.auth)
        except OSError:
            raise RequestError("Error getting VPlan")

        if result.status_code == 401:
            raise RequestError("Invalid Authentication")

        if result.status_code == 404:
            raise RequestError("not found")

        return result.text


def get_headings(table):
    return [th.text for th in table.find_all("th")]

def is_subst(table):
    if table.has_attr("class"):
        return table["class"] == ["subst"]
    else:
        return False


def is_info(table):
    return len(get_headings(table)) == 1


def subst_available(table):
    return len(get_headings(table)) > 1


class DayInfo:
    weekday = 0
    headers = []
    data = []
    info = []

    def __str__(self):
        return "DayInfo for weekday {}".format(self.weekday)

    def __repr__(self):
        return "{} object at {}".format(self.__str__(), str(id(self)))

def clean(s):
    s = s.replace("\x0B", "")
    s = s.replace("\xa0", "")
    return s

def parse_info(info):
    rows = info.find_all("tr")
    data = [
        [clean(elem.text) for elem in row.find_all("td")]
        for row in rows]
    return data


def parse_subst(subst):
    rows = subst.find_all("tr")

    res = []
    for tr in rows:
        row = tr.find_all("td")[:9]
        if len(row) > 1:
            row = [clean(elem.text) for elem in row]
            if len(row) != 9:
                print("----------########----------")
                print(row)
            res.append(Record(*row))

    return res


def find(subst):
    links = subst.find_all("a", {"name": True})

    days = []

    count = 0
    for link in links:
        day = DayInfo()

        day.weekday = int(link["name"])
        next_table = link.find_next("table")

        if is_info(next_table):
            day.info = parse_info(next_table)
            subst_table = next_table.find_next("table")
        else:
            subst_table = next_table

        # in weird cases, it thinks there is a table too much
        if subst_table is None:
            print("RECOVERABLE TABLE ERROR")
            days.append(day)
            continue

        if is_subst(subst_table):
            if subst_available:
                day.headers = get_headings(subst_table)
                day.data = parse_subst(subst_table)

        days.append(day)

    if len(days) != 5:
        raise RequestError("No 5 days of week")

    return days
