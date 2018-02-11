# Tracking Geek: A tool for visualizing swathes of gpx files at once
# Copyright (C) 2012, Henry Bush
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gpxpy
import os.path
import hashlib

BUF_SIZE = 65536


def get_track(path):
    """ If the track is in the database, return a TrackDB. If not, return a
    TrackPath.
    """
    raise NotImplementedError


def get_track_from_db(hash):
    """ Get a track from the database using it's sha1 hash """
    raise NotImplementedError


class TrackError(IOError):
    pass


class Track(object):
    def __hash__(self):
        return self.sha1

    def get_parsed(self):
        if self.save_memory:
            with open(self.path, "r") as gpx_file:
                return gpxpy.parse(gpx_file)
        else:
            if not hasattr(self, "_parsed_track"):
                with open(self.path, "r") as gpx_file:
                    try:
                        self._parsed_track = gpxpy.parse(gpx_file)
                    except:
                        # We can do a bare except, as we're re-raising
                        print("Errored path: %s" % self.path)
                        raise
            return self._parsed_track

    def get_segments(self):
        segments = []
        for track in self.get_parsed().tracks:
            segments.extend(track.segments)
        return segments

    def _extract_stats_from_gpx(self):
        parsed = self.get_parsed()
        self._min_latitude, self._max_latitude, \
            self._min_longitude, self._max_longitude = parsed.get_bounds()
        self._min_elevation, self._max_elevation = \
            parsed.get_elevation_extremes()
        self._min_time, self._max_time = parsed.get_time_bounds()
        self._min_speed = 0
        self._max_speed = parsed.get_moving_data().max_speed
        self._length_2d = parsed.length_2d()
        self._length_3d = parsed.length_3d()

    def __getattr__(self, name):
        valid_attrs = ["min_latitude", "max_latitude",
                       "min_longitude", "max_longitude",
                       "min_elevation", "max_elevation",
                       "min_time", "max_time",
                       "min_speed", "max_speed",
                       "length_2d", "length_3d"]
        if name in valid_attrs:
            private_attr = "_%s" % name
            if not hasattr(self, private_attr):
                # Note that we *should* never have to do this for a
                # TrackDB, but you never know.
                # TODO: Maybe put a warning in?
                self._extract_stats_from_gpx()
            if not hasattr(self, private_attr):
                msg = "Internal error: bound '%s' is still not present" % name
                raise AttributeError(msg)
            return getattr(self, private_attr)
        raise AttributeError("No %s attribute present" % name)

    @property
    def min_date(self):
        return self.min_time.date()

    @property
    def max_date(self):
        return self.max_time.date()

    @property
    def length(self):
        """ Get the length of the track. This gets the 3D length. To get the
        flat length (as measured on a map), use length_2d.
        """
        return self.length_3d

    @property
    def sha1(self):
        if hasattr(self, "_sha1"):
            return self._sha1.hexdigest()
        self._sha1 = hashlib.sha1()
        with open(self.path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                self._sha1.update(data)
        return self._sha1.hexdigest()

    @property
    def _filepath(self):
        """ The db track has a different "path" (the original path of the file)
        to "_filepath" (the actual path to the file). But by default, they're
        the same.
        """
        return self.path


class TrackDB(Track):
    def __init__(self, data):
        """ Instantiate a track object using the data retrieved from the
        database. Note that the "path" in the database isn't the actual path to
        the file on disk, it's now stored in the database vault. Thus we have
        "original_path" for that, and "path" for the actual vault path (based
        on sha1).
        """
        # Open up the data parameter (is it a dict? that would be nice)
        # and store its contents in private variables
        raise NotImplementedError


class TrackPath(Track):
    def __init__(self, path, save_memory=False):
        # TODO: ability to give it a vault path, and it detect it as such
        if not os.path.exists(path):
            msg = "The gpx file '%s' does not exist"
            raise IOError(msg)
        self.save_memory = save_memory
        self.stored_in_vault = False
        self.path = path
