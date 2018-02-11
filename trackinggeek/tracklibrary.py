import os
import sqlite3
from datetime import date, datetime, timedelta
from trackinggeek.track import Track, TrackError

_TYPE_LOOKUP = {str: "STRING", int: "INTEGER", float: "FLOAT",
                date: "INTEGER", timedelta: "INTEGER", bool: "BOOLEAN"}

_TRACK_TABLE = {"path": "STRING", "sha1": "STRING",
                "length_3d": "FLOAT", "length_2d": "FLOAT",
                "min_elevation": "FLOAT", "max_elevation": "FLOAT",
                "min_latitude": "FLOAT", "max_latitude": "FLOAT",
                "min_longitude": "FLOAT", "max_longitude": "FLOAT",
                "min_speed": "FLOAT", "max_speed": "FLOAT",
                "min_time": "INTEGER", "max_time": "INTEGER",
                "stored_in_vault": "BOOLEAN"}


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
    """ Ensure a string isn't trying to inject any dodgy SQL.

    Note that though this also accepts any iterable of strings as input, if
    given one it always outputs a list
    """
    # Although the input strings are all self-generated atm, this could
    # change in future
    if not isinstance(mystr, str):
        return [_check(s) for s in mystr]
    if mystr != mystr.translate(None, ")(][;,"):
        raise RuntimeError("Input '%s' looks dodgy to me" % mystr)
    return mystr


def get_library_dir():
    """ Get the file path to the sqlite database """
    return os.path.join(os.environ["HOME"], "tracklibrary")


class TrackLibraryDB(object):
    """ Information about all the tracks, stored in an sqlite database """
    global_table = "global"
    track_table = "track"

    def __init__(self, library_dir=None, db_path=None, vault_dir=None,
                 debug=True):
        # If we get given a path, use it, but we can make up our own
        if library_dir is None:
            self.library_dir = get_library_dir()
        else:
            self.library_dir = library_dir
        if vault_dir is None:
            self.vault_dir = os.path.join(self.library_dir, "vault")
        else:
            self.vault_dir = vault_dir
        try:
            os.makedirs(self.library_dir)
        except Exception:
            if not os.path.isdir(self.library_dir):
                raise
        try:
            os.makedirs(self.vault_dir)
        except Exception:
            if not os.path.isdir(self.vault_dir):
                raise
        if db_path is None:
            self._dbpath = os.path.join(self.library_dir, "tracklibrary.db")
        else:
            self._dbpath = db_path
        self._debug = debug
        self._connect_db()

    def debug(self, msg):
        # The original parent class of the class this was copied from
        # had a debug method
        if self._debug:
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
            # Reconnect, so we can recreate
            self._connect_db()
        else:
            self.warning("No database present at %s" % self._dbpath)

    def _create_global_table(self):
        table_name = _check(self.global_table)
        lib_dir = _check(self.library_dir)
        columns = ["parameter STRING", "value STRING"]
        sql = ["CREATE TABLE %s (" % table_name,
               ",\n".join(columns),
               ");"]
        self._execute("\n".join(sql))
        sql = ["INSERT INTO %s (" % table_name,
               "'parameter', 'value') "
               "VALUES ('library_dir', '%s');" % lib_dir]
        return self._execute("\n".join(sql))

    def _create_track_table(self):
        columns = []
        for name in sorted(_TRACK_TABLE):
            name = _check(name)
            type_ = _check(_TRACK_TABLE[name])
            columns.append("%s %s" % (name, type_))

        sql = """ CREATE TABLE %s (
                    %s
            );""" % (self.track_table, ",\n".join(columns))
        return self._execute(sql)

    def create(self):
        assert not self.is_present()
        self._create_global_table()
        self._create_track_table()

    def add_track(self, track):
        results = []
        for column in sorted(_TRACK_TABLE):
            if column == "stored_in_vault":
                results.append(False)
                continue
            value = getattr(track, column)
            if value.__class__ in _CONVERTER:
                results.append(_CONVERTER[value.__class__][0](value))
            else:
                results.append(value)
        question_marks = ", ".join("?" * len(results))
        sql = "INSERT INTO %s VALUES (%s)"
        sql = sql % (_check(self.track_table), question_marks)
        result = self._execute(sql, results)
        self.copy_track_to_vault(track)
        if not self.check_vault(track):
            raise IOError("Failed to store track %s in vault" % track.path)
        # TODO: Check there's only one result
        sql = "UPDATE %s SET stored_in_vault = true WHERE sha1 == '%s'"
        sql = sql % (_check(self.track_table), _check(track.sha1))
        return self._execute(sql)

    def copy_track_to_vault(self, track):
        """ Copy the given track into the vault of the track library """
        raise NotImplementedError

    def check_vault(self, track):
        """ Check that the file for the given track is in the vault """
        raise NotImplementedError

    def has_track(self, track):
        raise NotImplementedError

    def get_track(self, sha1):
        sql = "SELECT * FROM %s WHERE sha1 = ?"
        sql = sql % _check(self.track_table)
        self._execute(sql, sha1)
        raw_tuples = self._cursor.fetchall()
        if len(raw_tuples) == 0:
            raise ValueError("Track %s not found in local database" % sha1)
        if len(raw_tuples) != 1:
            # This should never happen, since sha1 should be unique
            raise ValueError("Multiple tracks found with hash %s" % sha1)
        raw_tuple = list(raw_tuples)[0]
        columns = _TRACK_TABLE.keys()
        tmp_dict = dict(zip(columns, raw_tuple))
        tmp_dict["start_date"] = _int_to_date(tmp_dict["start_date"])
        tmp_dict["end_date"] = _int_to_date(tmp_dict["end_date"])
        return tmp_dict
    """

    @classmethod
    def _get_site_columns(cls):
        return Site.list_attrs()
"""


class OldTrackLibrary(dict):
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(OldTrackLibrary, cls).__new__(cls)
        return cls._instance

    def add_track(self, path, save_memory=False):
        if path in self:
            return
        try:
            self[path] = Track(path, save_memory=save_memory)
            if self[path].min_time is None:
                raise TrackError("%s has bad date" % path)
        except Exception as e:
            print("Error reading %s: %s" % (path, e))

    def sort_tracks_by_time(self):
        """ Sort by value, but return keys """
        return [item[0] for item in sorted(self.items(),
                                           key=lambda t: t[1].min_time)]
