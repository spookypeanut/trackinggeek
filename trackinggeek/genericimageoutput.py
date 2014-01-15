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

from trackinggeek.track import TrackLibrary
from trackinggeek.util import mercator_adjust, tracks_from_path

DEFAULT_SIZE = 1024

class GenericImageOutput(object):
    def __init__(self, latitude_range=None, longitude_range=None,
                 pixel_dimensions=None, config=None):
        # TODO: Have ability to override the automatic lat/long range
        if latitude_range:
            self.min_latitude = float(latitude_range[0])
            self.max_latitude = float(latitude_range[1])
        else:
            self.min_latitude = None
            self.max_latitude = None

        if longitude_range:
            self.min_longitude = float(longitude_range[0])
            self.max_longitude = float(longitude_range[1])
        else:
            self.min_longitude = None
            self.max_longitude = None

        self.config = config
        self.pixel_dimensions = pixel_dimensions
        self.tracks = []

        # TODO: Have these settable in the config 
        self.min_elevation = None
        self.max_elevation = None

        # TODO: Have these settable in the config 
        self.min_speed = None
        self.max_speed = None

    def draw(self):
        raise NotImplementedError

    def prepare_to_draw(self):
        # This doesn't do the whole job, hence it's private
        if not self.min_latitude:
            self.min_latitude = self.auto_min_latitude
        if not self.max_latitude:
            self.max_latitude = self.auto_max_latitude
        if not self.min_longitude:
            self.min_longitude = self.auto_min_longitude
        if not self.max_longitude:
            self.max_longitude = self.auto_max_longitude
        if not self.min_speed:
            self._detect_speeds()
        if not self.min_elevation:
            self._detect_elevations()
        self._calc_pixel_dimensions(self.pixel_dimensions)

    def _calc_pixel_dimensions(self, pixel_dimensions):
        """ Calculate the size of the image in pixels, given whatever
        minimum / maximums we've been given.
        """
        if pixel_dimensions is None or len(pixel_dimensions.keys()) == 0:
            pixel_dimensions = {"max":DEFAULT_SIZE}
        if "width" in pixel_dimensions and "height" in pixel_dimensions:
            self.pixel_width = pixel_dimensions["width"]
            self.pixel_height = pixel_dimensions["height"]
            return
        self.aspect_ratio = (self.max_longitude - self.min_longitude) / \
                            (mercator_adjust(self.max_latitude) -
                             mercator_adjust(self.min_latitude))
        if "width" in pixel_dimensions:
            self.pixel_width = pixel_dimensions["width"]
            self.pixel_height = int(float(self.pixel_width) / self.aspect_ratio)
            return
        if "height" in pixel_dimensions:
            self.pixel_height = pixel_dimensions["height"]
            self.pixel_width = int(float(self.pixel_height) * self.aspect_ratio)
            return
        if "max" in pixel_dimensions:
            if self.aspect_ratio > 1:
                self.pixel_width = pixel_dimensions["max"]
                self.pixel_height = int(float(self.pixel_width) / self.aspect_ratio)
                return
            self.pixel_height = pixel_dimensions["max"]
            self.pixel_width = int(float(self.pixel_height) * self.aspect_ratio)
            return
        if "min" in pixel_dimensions:
            if self.aspect_ratio < 1:
                self.pixel_width = pixel_dimensions["min"]
                self.pixel_height = int(float(self.pixel_width) / self.aspect_ratio)
                return
            self.pixel_height = pixel_dimensions["min"]
            self.pixel_width = int(float(self.pixel_height) * self.aspect_ratio)
            return
        raise ValueError("Could not calculate the image resolution")

    def _detect_speeds(self):
        # In km/h
        self.min_speed = 1
        self.max_speed = 100

    def add_track(self, path):
        tl = TrackLibrary()
        tl.add_track(path)
        if self.max_latitude:
            if tl[path].min_latitude > self.max_latitude or \
                    tl[path].max_latitude < self.min_latitude or \
                    tl[path].min_longitude > self.max_longitude or \
                    tl[path].max_longitude < self.min_longitude:
                #print("Outside our specified area")
                return
        min_date = self.config.get_min_date()
        max_date = self.config.get_max_date()
        if min_date or max_date:
            if min_date and tl[path].max_date < min_date:
                #print("Before the specified time range")
                return
            if max_date and tl[path].min_date > max_date:
                #print("After the specified time range")
                return

        # At this point we know the track is one that we want
        self.tracks.append(path)

        # If we only have one track, we use its bounds as our
        # auto-detected bounds
        if len(self.tracks) == 1:
            self.auto_min_latitude = tl[path].min_latitude
            self.auto_max_latitude = tl[path].max_latitude
            self.auto_min_longitude = tl[path].min_longitude
            self.auto_max_longitude = tl[path].max_longitude
            self.auto_min_elevation = tl[path].min_elevation
            self.auto_max_elevation = tl[path].max_elevation
            return

        # If we don't have a minimum latitude specified, grow our
        # auto-detected bounds accordingly
        if not self.min_latitude:
            if self.auto_min_latitude > tl[path].min_latitude:
                self.auto_min_latitude = tl[path].min_latitude
            if self.auto_max_latitude < tl[path].max_latitude:
                self.auto_max_latitude = tl[path].max_latitude
            if self.auto_min_longitude > tl[path].min_longitude:
                self.auto_min_longitude = tl[path].min_longitude
            if self.auto_max_longitude < tl[path].max_longitude:
                self.auto_max_longitude = tl[path].max_longitude

        # Likewise, grow the auto-elevation bounds
        if not self.min_elevation:
            if self.auto_min_elevation > tl[path].min_elevation:
                self.auto_min_elevation = tl[path].min_elevation
            if self.auto_max_elevation < tl[path].max_elevation:
                self.auto_max_elevation = tl[path].max_elevation

    def _detect_elevations(self):
        tl = TrackLibrary()
        if self.config.colour_is_constant() and \
                self.config.linewidth_is_constant():
            print("Elevation detection not required")
            return
        currmin = None
        currmax = None
        print("Detecting min & max elevation (%s tracks)" % len(self.tracks))
        for path in self.tracks:
            if not currmin:
                currmin = tl[path].min_elevation
                currmax = tl[path].max_elevation
                continue
            currmin = min(currmin, tl[path].min_elevation)
            currmax = max(currmax, tl[path].max_elevation)
        self.min_elevation = currmin
        self.max_elevation = currmax
        print("Detected range is %s - %s" % (currmin, currmax))

    def add_path(self, path):
        for track in tracks_from_path(path):
            self.add_track(track)

