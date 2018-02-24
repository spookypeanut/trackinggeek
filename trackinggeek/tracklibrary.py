import os
import sqlite3
import shutil
from datetime import date, datetime, timedelta
from trackinggeek.track import TrackPath, TrackError, TrackDB, _TRACK_ATTRIBUTES
from trackinggeek.util import tracks_from_path

_TYPE_LOOKUP = {str: "STRING", int: "INTEGER", float: "FLOAT",
                date: "INTEGER", datetime: "INTEGER", timedelta: "INTEGER",
                bool: "BOOLEAN"}


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


def get_relative_vault_path(track):
    dirname = track.sha1[:3]
    basename = "%s.gpx" % track.sha1[3:]
    return (dirname, basename)


def _convert_to_track_object(self, raw_tuple):
    columns = sorted(_TRACK_ATTRIBUTES.keys())
    tmp_dict = dict(zip(columns, raw_tuple))
    tmp_dict["min_time"] = _int_to_date(tmp_dict["min_time"])
    tmp_dict["max_time"] = _int_to_date(tmp_dict["max_time"])
    return TrackDB(tmp_dict)


class TrackLibraryDB(object):
    """ Information about all the tracks, stored in an sqlite database """
    global_table = "global"
    track_table = "track"

    def __init__(self, library_dir=None, db_path=None, vault_dir=None,
                 debug=False):
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

    def add_track_directory(self, path):
        tracks = tracks_from_path(path)
        print("Adding %s tracks to database" % len(tracks))
        for counter, eachtrack in enumerate(tracks):
            if counter and counter % 20 == 0:
                print("Added %s/%s tracks" % (counter, len(tracks)))
            t = TrackPath(eachtrack)
            if self.has_track(t):
                print("Skipping %s, already in database" % eachtrack)
                continue
            self.add_track(t)

    def add_track(self, track):
        results = []
        for column in sorted(_TRACK_ATTRIBUTES):
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
        self._execute(sql, results)
        self.move_track_to_vault(track)

        if not self.check_vault(track):
            raise IOError("Failed to store track %s in vault" % track.path)
        # TODO: Check there's only one result
        sql = "UPDATE %s SET stored_in_vault = 1 WHERE sha1 == '%s'"
        sql = sql % (_check(self.track_table), _check(track.sha1))
        self._execute(sql)
        return self.get_track(track.sha1)

    def get_vault_path(self, track):
        dirname, basename = get_relative_vault_path(track)
        return os.path.join(self.vault_dir, dirname), basename

    def move_track_to_vault(self, track):
        """ Copy the given track into the vault of the track library """
        dirname, basename = self.get_vault_path(track)
        try:
            os.makedirs(dirname)
        except OSError:
            if not os.path.isdir(dirname):
                raise
        destpath = os.path.join(dirname, basename)
        if os.path.isfile(destpath):
            raise IOError("Path %s already exists!" % destpath)
        self._debug("Moving %s to %s" % (track.path, destpath))
        shutil.move(track.path, destpath)

    def check_vault(self, track):
        """ Check that the file for the given track is in the vault """
        dirname, basename = self.get_vault_path(track)
        fullpath = os.path.join(dirname, basename)
        if not os.path.exists(fullpath):
            return False
        return True

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
            return_list.append(_convert_to_track_object(raw_tuple))
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
        pass


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
