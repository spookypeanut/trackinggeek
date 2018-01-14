import os
import sqlite3
from datetime import date, datetime, timedelta

_TYPE_LOOKUP = {str: "STRING", int: "INTEGER", float: "FLOAT",
                date: "INTEGER", timedelta: "INTEGER"}

_TRACK_TABLE = {"path": "STRING", "length": "FLOAT", "sha1": "STRING",
                "latitude_min": "FLOAT", "latitude_max": "FLOAT",
                "longitude_min": "FLOAT", "longitude_max": "FLOAT",
                "speed_min": "FLOAT", "speed_max": "FLOAT",
                "time_min": "INTEGER", "time_max": "INTEGER",
                "elevation_min": "FLOAT", "elevation_max": "FLOAT"}


def _date_to_int(mydate):
    """ Convert a datetime.date object to a unix timestamp """
    return _datetime_to_int(datetime.combine(mydate, datetime.min.time()))


def _datetime_to_int(mytime):
    """ Convert a datetime.datetime object to a unix timestamp. """
    # Apparently, this is the safest way to do it (ignoring timezones)
    return int((mytime - datetime(1970, 1, 1)).total_seconds())


def _timedelta_to_int(mytimedelta):
    return mytimedelta.seconds


def _int_to_timedelta(myint):
    return timedelta(seconds=myint)


def _int_to_datetime(myint):
    """ Convert a unix timestamp to a datetime.datetime object """
    return datetime.fromtimestamp(myint)


def _int_to_date(myint):
    """ Convert a unix timestamp to a datetime.date object """
    return _int_to_datetime(myint).date()

# The converters to use to put object types into and get them out of the
# database. First element is to put them in, second to get them out
_CONVERTER = {date: (_date_to_int, _int_to_date),
              datetime: (_datetime_to_int, _int_to_datetime),
              timedelta: (_timedelta_to_int, _int_to_timedelta)}


def _check(mystr):
    """ Ensure a string isn't trying to inject any dodgy SQL """
    # Although the input strings are all self-generated atm, this could
    # change in future
    if not isinstance(mystr, str):
        return [_check(s) for s in mystr]
    if mystr != mystr.translate(None, ")(][;,"):
        raise RuntimeError("Input '%s' looks dodgy to me" % mystr)
    return mystr


def get_db_path():
    """ Get the file path to the sqlite database """
    return os.path.join(os.environ["HOME"], "tracklibrary.db")


class TrackLibraryDB(object):
    """ Information about all the tracks, stored in an sqlite database """
    global_table = "global"
    track_table = "power"

    def __init__(self, path=None, debug=True):
        # If we get given a path, use it, but we can make up our own
        if path is None:
            self._dbpath = get_db_path()
        else:
            self._dbpath = path
        self._connect_db()

    def debug(self, msg):
        # The original parent class of the class this was copied from
        # had a debug method
        print(msg)

    def _connect_db(self):
        self._conn = sqlite3.connect(self._dbpath)
        self._cursor = self._conn.cursor()

    def _execute(self, sql, variables=None):
        """ Execute an sql query, after optionally printing it """
        self.debug("Executing:")
        self.debug(sql)
        if variables is None:
            return_value = self._cursor.execute(sql)
        else:
            # TODO: Check if it's a tuple / iterable
            if not isinstance(variables, list):
                variables = [variables]
            self.debug("Variables: %s" % (variables,))
            return_value = self._cursor.execute(sql, variables)
        self._conn.commit()
        return return_value

    def is_present(self):
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        self._execute(sql)
        if self._cursor.fetchall() == []:
            return False
        return True

    def destroy(self):
        if self.is_present():
            self._conn.close()
            os.remove(self._dbpath)
        else:
            self.warning("No database present at %s" % self._dbpath)

    def _create_global_table(self, library_dir=None):
        table_name = _check(self.global_table)
        lib_dir = _check(library_dir)
        columns = ["parameter STRING", "value STRING"]
        sql = ["CREATE TABLE %s (" % table_name,
               ",\n".join(columns),
               ");",
               "INSERT INTO %s (" % table_name,
               "'library_dir', '%s');" % lib_dir]
        return self._execute("\n".join(sql))

    def _create_track_table(self):
        columns = []
        for column_tuple in sorted(_TRACK_TABLE.items()):
            columns.append("%s %s" % _check(column_tuple))

        sql = """ CREATE TABLE %s (
                    %s
            );""" % (self.track_table, ",\n".join(columns))
        return self._execute(sql)

    def create(self):
        try:
            assert not self.is_present()
            self._create_global_table()
            self._create_track_table()
        except sqlite3.ProgrammingError:
            # If we've just destroyed, we need to re-connect before
            # recreating
            self._connect_db()
            self.create()

    def add_track(self, track):
        results = []
        for column in sorted(_TRACK_TABLE):
            value = getattr(track, column)
            if value.__class__ in _CONVERTER:
                results.append(_CONVERTER[value.__class__][0](value))
            else:
                results.append(value)
        question_marks = ", ".join("?" * len(results))
        sql = "INSERT INTO %s VALUES (%s)"
        sql = sql % (_check(self.site_table), question_marks)
        return self._execute(sql, results)

    """
    def get_track(self, path=None):
        sql = "SELECT * FROM %s WHERE site_id = ?"
        sql = sql % _check(self.site_table)
        self._execute(sql, site_id)
        raw_tuples = self._cursor.fetchall()
        if len(raw_tuples) == 0:
            raise ValueError("Site %s not found in local database" % site_id)
        if len(raw_tuples) != 1:
            # This should never happen, since site_id is the primary key
            raise ValueError("Some seriously weird shit happened")
        raw_tuple = list(raw_tuples)[0]
        columns = self._get_site_columns()
        tmp_dict = dict(zip(columns, raw_tuple))
        tmp_dict["start_date"] = _int_to_date(tmp_dict["start_date"])
        tmp_dict["end_date"] = _int_to_date(tmp_dict["end_date"])
        return Site(**tmp_dict)

    @classmethod
    def _get_site_columns(cls):
        return Site.list_attrs()
"""

    def _has_track(self, power):
        raise NotImplementedError

    def _get_min_time(self, site_id=None):
        sql = "SELECT MIN(start_time) FROM %s" % _check(self.power_table)
        if site_id is not None:
            sql += " WHERE site_id == ?"
        self._execute(sql, site_id)
        as_int = self._cursor.fetchone()[0]
        return _int_to_datetime(as_int)

    def _get_max_time(self, site_id=None):
        sql = "SELECT MAX(start_time), duration FROM %s"
        if site_id is not None:
            sql += " WHERE site_id == ?"
        sql = sql % _check(self.power_table)
        # Luckily, if site_id is None, variables gets passed as None
        self._execute(sql, site_id)
        start_time, duration = self._cursor.fetchone()
        return _int_to_datetime(start_time + duration)

    def get_time_limits(self, site_id=None):
        return (self._get_min_time(site_id=site_id),
                self._get_max_time(site_id=site_id))
