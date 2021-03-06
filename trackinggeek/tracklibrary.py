import re
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from trackinggeek.track import (TrackPath, TrackError, TrackDB,
                                _TRACK_ATTRIBUTES)
from trackinggeek.util import tracks_from_path

_TYPE_LOOKUP = {str: "STRING", int: "INTEGER", float: "FLOAT",
                date: "INTEGER", datetime: "INTEGER", timedelta: "INTEGER",
                bool: "BOOLEAN"}

# This creates a translation table whereby each of these characters
# translates to nothing
_SQL_CHECK = str.maketrans(dict.fromkeys(")(][;,"))


def _date_to_int(mydate):
    """ Convert a datetime.date object to a unix timestamp """
    if mydate is None:
        return None
    return _datetime_to_int(datetime.combine(mydate, datetime.min.time()))


def _datetime_to_int(mytime):
    """ Convert a datetime.datetime object to a unix timestamp. """
    # Apparently, this is the safest way to do it (ignoring timezones)
    if mytime is None:
        return None
    origin = datetime.fromtimestamp(0, timezone.utc)
    return int((mytime - origin).total_seconds())


def _timedelta_to_int(mytimedelta):
    if mytimedelta is None:
        return None
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
    if mystr != mystr.translate(_SQL_CHECK):
        raise RuntimeError("Input '%s' looks dodgy to me" % mystr)
    return mystr


def get_library_dir():
    """ Get the file path to the sqlite database """
    return os.path.join(os.environ["HOME"], "tracklibrary")


def get_relative_vault_path(track):
    dirname = track.sha1[:3]
    basename = "%s.gpx" % track.sha1[3:]
    return (dirname, basename)


class TrackLibraryDB(object):
    """ Information about all the tracks, stored in an sqlite database """
    global_table = "global"
    track_table = "track"

    def __init__(self, library_dir=None, db_path=None, debug=False):
        # If we get given a path, use it, but we can make up our own
        if db_path is None:
            if library_dir is None:
                self.library_dir = get_library_dir()
            else:
                self.library_dir = library_dir
            try:
                os.makedirs(self.library_dir)
            except Exception:
                if not os.path.isdir(self.library_dir):
                    raise
            self._dbpath = os.path.join(self.library_dir, "tracklibrary.db")
        else:
            self._dbpath = os.path.realpath(db_path)
            self.library_dir = None
        self._debug = debug
        self._connect_db()
        if self.library_dir is None:
            self.update_library_dir_from_database()
        self.library_dir = os.path.realpath(self.library_dir)
        if not os.path.isdir(self.library_dir):
            msg = "Library directory %s doesn't exist"
            raise IOError(msg % self.library_dir)

    def _get_track_object_from_tuple(self, raw_tuple):
        try:
            columns = sorted(_TRACK_ATTRIBUTES.keys())
            tmp_dict = dict(zip(columns, raw_tuple))
            tmp_dict["min_time"] = _int_to_datetime(tmp_dict["min_time"])
            tmp_dict["max_time"] = _int_to_datetime(tmp_dict["max_time"])
            tmp_dict["path"] = os.path.join(self.library_dir, tmp_dict["path"])
            track_object = TrackDB(tmp_dict)
            return track_object
        except:
            print("Error parsing: %s" % (raw_tuple,))
            raise

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

    def update_library_dir_from_database(self):
        table_name = _check(self.global_table)
        sql = 'SELECT value FROM %s WHERE parameter = "library_dir"'
        sql = sql % table_name
        self._execute(sql)
        raw_tuple = self._cursor.fetchone()
        self.library_dir = raw_tuple[0]
        return self.library_dir

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
        for name in sorted(_TRACK_ATTRIBUTES):
            name = _check(name)
            type_ = _TRACK_ATTRIBUTES[name]
            sqltype = _check(_TYPE_LOOKUP[type_])
            columns.append("%s %s" % (name, sqltype))

        sql = """ CREATE TABLE %s (
                    %s,
                    PRIMARY KEY (sha1)
            );""" % (self.track_table, ",\n".join(columns))
        return self._execute(sql)

    def create(self):
        assert not self.is_present()
        self._create_global_table()
        self._create_track_table()

    def clean_tracks(self, execute=False):
        to_delete = set()
        for eachtrack in self.get_tracks():
            if self.check_vault(eachtrack) is False:
                to_delete.add(eachtrack)
        print("\n".join([a.path for a in sorted(to_delete)]))

    def remove_sha(self, sha):
        sql = 'DELETE FROM %s WHERE sha1 = "%s"'
        sql = sql % (self.track_table, _check(sha))
        return self._execute(sql)

    def add_new_tracks(self):
        return self.add_track_directory(self.library_dir)

    def add_track_directory(self, path):
        tracks = tracks_from_path(path)
        print("Adding %s tracks to database" % len(tracks))
        actual_added = 0
        for counter, eachtrack in enumerate(tracks):
            if counter and counter % 100 == 0:
                print("Scanned %s/%s tracks" % (counter, len(tracks)))
            t = TrackPath(os.path.realpath(eachtrack))
            if self.has_track(t):
                continue
            actual_added += 1
            self.add_track(t)
        print("Added %s new tracks" % actual_added)

    def add_track(self, track):
        self.assert_vault(track)
        results = []
        for column in sorted(_TRACK_ATTRIBUTES):
            value = getattr(track, column)
            if column == "path":
                # Store relative paths
                value = value[len(self.library_dir) + 1:]
            if value.__class__ in _CONVERTER:
                results.append(_CONVERTER[value.__class__][0](value))
            else:
                results.append(value)
        if None in results:
            raise ValueError("Track %s has None values" % track.path)
        question_marks = ", ".join("?" * len(results))
        sql = "INSERT INTO %s VALUES (%s)"
        sql = sql % (_check(self.track_table), question_marks)
        self._execute(sql, results)
        return self.get_track(track.sha1)

    def get_vault_path(self, track):
        dirname, basename = get_relative_vault_path(track)
        return os.path.join(self.library_dir, dirname), basename

    def assert_vault(self, track):
        if self.check_vault(track) is False:
            msg = "%s is not in the vault (%s)"
            raise RuntimeError(msg % (track.path, self.library_dir))

    def check_vault(self, track):
        """ Check that the file for the given track is in the vault """
        if track.path.startswith(self.library_dir):
            if os.path.exists(track.path):
                return True
        return False

    def has_track(self, track):
        """ Check if the given track is in the database (not necessarily the
        vault) """
        try:
            self._get_track(track.sha1, allow_multiple=True)
        except Exception:
            return False
        return True

    def get_track(self, sha1):
        return self._get_track(sha1, allow_multiple=False)

    def _get_track(self, sha1, allow_multiple=False):
        """ When we only care if the track is in the database, it's "fine"* if
        there are multiple tracks with the same sha1 in the database. That
        should be impossible, so this is probably overkill, but I done it
        anyway.

        * Fine as in, it will break everything else, but this should work.
        """
        sql = "SELECT * FROM %s WHERE sha1 = ?"
        sql = sql % _check(self.track_table)
        self._execute(sql, sha1)
        raw_tuples = self._cursor.fetchall()
        if len(raw_tuples) == 0:
            raise ValueError("Track %s not found in local database" % sha1)
        if len(raw_tuples) != 1:
            if allow_multiple is False:
                # This should never happen, since sha1 should be unique
                raise ValueError("Multiple tracks found with hash %s" % sha1)
        return_list = []
        for raw_tuple in raw_tuples:
            return_list.append(self._get_track_object_from_tuple(raw_tuple))
        if allow_multiple is True:
            return return_list
        return return_list[0]

    def get_tracks(self, **kwargs):
        """ Each argument should be the name of an attribute of the track. The
        value of each argument should be a range, as a tuple. E.g.
          min_elevation = (0, 100)
        Will narrow down searches to those tracks whose minimum elevation is
        between 0 and 100.
        To specify a one-ended range, use None:
          length_3d=(None, 1000)
        Will narrow down to all tracks that are less than 1000 long.
        """
        sql = "SELECT * FROM %s" % _check(self.track_table)
        clauses = []
        min_template = "%s >= ?"
        max_template = "%s <= ?"
        for key, value in kwargs.items():
            if key == "namefilter":
                # TODO: This could be more specific
                clauses.append(("path like ?", "%%%s%%" % value))
                continue
            if key == "nameregex":
                def regexp(y, x, search=re.search):
                    return 1 if search(y, x) else 0
                self._conn.create_function('regexp', 2, regexp)
                clauses.append(("path regexp ?", value))
                continue
            param_class = value[0].__class__
            if param_class in _CONVERTER:
                converter = _CONVERTER[param_class][0]
                value = tuple(map(converter, list(value)))
            min_, max_ = value
            if min_ is not None:
                clauses.append((min_template % key, min_))
            if max_ is not None:
                clauses.append((max_template % key, max_))
        if clauses:
            sql += " WHERE "
            sql += " AND ".join([c[0] for c in clauses])
            self._execute(sql, [c[1] for c in clauses])
        else:
            self._execute(sql)
        raw_tuples = self._cursor.fetchall()
        return_set = set()
        for raw_tuple in raw_tuples:
            _track_object = self._get_track_object_from_tuple(raw_tuple)
            return_set.add(_track_object)
        return return_set


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
            self[path] = TrackPath(path, save_memory=save_memory)
            if self[path].min_time is None:
                raise TrackError("%s has bad date" % path)
        except Exception as e:
            print("Error reading %s: %s" % (path, e))

    def sort_tracks_by_time(self):
        """ Sort by value, but return keys """
        return [item[0] for item in sorted(self.items(),
                                           key=lambda t: t[1].min_time)]
