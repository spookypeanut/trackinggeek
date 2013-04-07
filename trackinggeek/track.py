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
import collections

Bounds = collections.namedtuple('Bounds',
        ('min_latitude', 'max_latitude', 'min_longitude', 'max_longitude',
         'min_elevation', 'max_elevation', 'min_time', 'max_time'))

class Track(object):
    def __init__(self, path, save_memory=False):
        self.path = path
        if not os.path.exists(path):
            msg = "The gpx file '%s' does not exist"
            raise IOError(msg)
        self.save_memory = save_memory

    def get_parsed(self):
        if self.save_memory:
            with open(self.path, "r") as gpx_file:
                return gpxpy.parse(gpx_file)
        else:
            if not hasattr(self, "_parsed_track"):
                with open(self.path, "r") as gpx_file:
                    self._parsed_track = gpxpy.parse(gpx_file)
            return self._parsed_track

    def _get_bounds(self):
        parsed = self.get_parsed()
        self._min_latitude, self._max_latitude, \
                self._min_longitude, self._max_longitude = \
                parsed.get_bounds()
        self._min_elevation, self._max_elevation = \
                parsed.get_elevation_extremes()
        self._min_time, self._max_time = parsed.get_time_bounds()

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

    def _get_extreme(self, name):
        private_attr = "_%s" % name
        if not hasattr(self, private_attr):
            self._get_bounds()
        if not hasattr(self, private_attr):
            msg = "Internal error: bound '%s' is still not present" % name
            raise AttributeError(msg)
        return getattr(self, private_attr)

