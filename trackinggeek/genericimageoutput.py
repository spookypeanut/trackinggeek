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

from trackinggeek.tracklibrary import TrackLibraryDB, OldTrackLibrary
from trackinggeek.util import mercator_adjust, tracks_from_path

DEFAULT_SIZE = 1024


class GenericImageOutput(object):
    def __init__(self, latitude_range=None, longitude_range=None,
                 elevation_range=None, speed_range=None,
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

        # TODO: Have these settable in the config
        if elevation_range:
            self.min_elevation, self.max_elevation = elevation_range
        else:
            self.min_elevation = None
            self.max_elevation = None

        # TODO: Have these settable in the config
        if speed_range:
            self.min_speed, self.max_speed = speed_range
        else:
            self.min_speed = None
            self.max_speed = None
        self.old_track_library = OldTrackLibrary()

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
        if self.min_speed is None:
            self._detect_speeds()
        if self.min_elevation is None:
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
        if self.config.colour_is_constant() and \
                self.config.linewidth_is_constant():
            print("Speed detection not required")
            return
        currmin = None
        currmax = None
        print("Detecting min & max speed (%s tracks)" % len(self.tracks))
        for path in self.tracks:
            print(dir(path))
            if not currmin:
                currmin = path.min_speed
                currmax = path.max_speed
                continue
            currmin = min(currmin, path.min_speed)
            currmax = max(currmax, path.max_speed)
        self.min_speed = currmin
        self.max_speed = currmax
        print("Detected range is %s - %s" % (currmin, currmax))


    def add_track(self, path):
        tl = self.old_track_library
        tl.add_track(path, save_memory=self.config.savememory())
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
                # print("Before the specified time range")
                return
            if max_date and tl[path].min_date > max_date:
                # print("After the specified time range")
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
            self.auto_min_speed = tl[path].min_speed
            self.auto_max_speed = tl[path].max_speed
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

        # Likewise, grow the auto-speed bounds
        if self.min_speed is None:
            if self.auto_min_speed > tl[path].min_speed:
                self.auto_min_speed = tl[path].min_speed
            if self.auto_max_speed < tl[path].max_speed:
                self.auto_max_speed = tl[path].max_speed

    def _detect_elevations(self):
        if self.config.colour_is_constant() and \
                self.config.linewidth_is_constant():
            print("Elevation detection not required")
            return
        currmin = None
        currmax = None
        print("Detecting min & max elevation (%s tracks)" % len(self.tracks))
        for path in self.tracks:
            if not currmin:
                currmin = path.min_elevation
                currmax = path.max_elevation
                continue
            currmin = min(currmin, path.min_elevation)
            currmax = max(currmax, path.max_elevation)
        self.min_elevation = currmin
        self.max_elevation = currmax
        print("Detected range is %s - %s" % (currmin, currmax))

    def add_path(self, path):
        tracklist = tracks_from_path(path)
        total = len(tracklist)
        counter = 0
        print("Parsing %i tracks" % total)
        for track in tracklist:
            self.add_track(track)
            counter += 1
            if counter % 100 == 0:
                print("\tParsed %i/%i tracks" % (counter, total))

    def add_database(self, database_path):
        self.track_library = TrackLibraryDB(library_dir=database_path)
        num_tracks = len(self.track_library.get_tracks())
        print("Database contains %i tracks" % num_tracks)
        self.get_refined_tracks()
        print("Found %i tracks to use" % len(self.tracks))

    def get_refined_tracks(self):
        self.tracks = []
        kwargs = {}
        kwargs["min_latitude"] = (None, self.max_latitude)
        kwargs["max_latitude"] = (self.min_latitude, None)
        kwargs["min_longitude"] = (None, self.max_longitude)
        kwargs["max_longitude"] = (self.min_longitude, None)
        if self.min_speed is not None:
            kwargs["max_speed"] = (self.min_speed, None)
        if self.max_speed is not None:
            kwargs["min_speed"] = (None, self.max_speed)

        self.tracks = self.track_library.get_tracks(**kwargs)
