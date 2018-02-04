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


class TrackError(IOError):
    pass


class Track(object):
    def __init__(self, path, save_memory=False):
        self.path = path
        if not os.path.exists(path):
            msg = "The gpx file '%s' does not exist"
            raise IOError(msg)
        self.save_memory = save_memory

    def __hash__(self):
        return hash(self.path)

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

    def _get_bounds(self):
        parsed = self.get_parsed()
        self._min_latitude, self._max_latitude, \
            self._min_longitude, self._max_longitude = parsed.get_bounds()
        self._min_elevation, self._max_elevation = \
            parsed.get_elevation_extremes()
        self._min_time, self._max_time = parsed.get_time_bounds()
        self._min_speed = 0
        self._max_speed = parsed.get_moving_data().max_speed

    # Is there a way to create these procedurally, just from a list?

    @property
    def min_latitude(self):
        return self._get_extreme("min_latitude")

    @property
    def max_latitude(self):
        return self._get_extreme("max_latitude")

    @property
    def min_longitude(self):
        return self._get_extreme("min_longitude")

    @property
    def max_longitude(self):
        return self._get_extreme("max_longitude")

    @property
    def min_elevation(self):
        return self._get_extreme("min_elevation")

    @property
    def max_elevation(self):
        return self._get_extreme("max_elevation")

    @property
    def min_time(self):
        return self._get_extreme("min_time")

    @property
    def max_time(self):
        return self._get_extreme("max_time")

    @property
    def min_speed(self):
        return self._get_extreme("min_speed")

    @property
    def max_speed(self):
        return self._get_extreme("max_speed")

    @property
    def min_date(self):
        return self.min_time.date()

    @property
    def max_date(self):
        return self.max_time.date()

    def _get_extreme(self, name):
        private_attr = "_%s" % name
        if not hasattr(self, private_attr):
            self._get_bounds()
        if not hasattr(self, private_attr):
            msg = "Internal error: bound '%s' is still not present" % name
            raise AttributeError(msg)
        return getattr(self, private_attr)

    @property
    def length(self):
        """ Get the length of the track. This gets the 3D length. To get the
        flat length (as measured on a map), use length_2d.
        """

    @property
    def length_2d(self):
        return self.get_parsed().length_2d()

    @property
    def length_3d(self):
        return self.get_parsed().length_3d()

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
