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

import os
import cairo
import gpxpy
import math
from .point import Point
from .config import ConfigError

#MODE = "RGBA"
MODE = "L"
DEFAULT_COLOUR = (0.3, 0.2, 0.5)
DEFAULT_SIZE = 1024

class Canvas(object):
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
        self._all_tracks = []
        self._track_objects = []
        self._track_paths = []

        # TODO: Have these settable in the config 
        self.min_elevation = None
        self.max_elevation = None

        # TODO: Have these settable in the config 
        self.min_speed = None
        self.max_speed = None

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
                            (self._merc_lat(self.max_latitude) -
                                    self._merc_lat(self.min_latitude))
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

    def _merc_lat(self, lat):
        """ Create a mercator projection-adjusted latitude
        """
        return 180 / math.pi * math.log(math.tan(math.pi / 4 + lat *
                                                    (math.pi / 180) / 2))

    def _convert_to_fraction(self, point):
        """ Convert a lat/long point into an (x,y) fraction of the drawing area
        """
        # TODO: this could be neater. The addition / subtraction should
        # be (a) consistently one or the other, and (b) we should adjust
        # the image width to take it into account.
        # Add half a pixel width so that we're drawing in the centre of
        # a pixel, not on the edge
        x = 0.5 / self.pixel_width + (point.long - self.min_longitude) / \
            (self.max_longitude - self.min_longitude)
        merc_lat = self._merc_lat(point.lat)
        merc_min = self._merc_lat(self.min_latitude)
        merc_max = self._merc_lat(self.max_latitude)
        # Subtract half a pixel width so that we're drawing in the centre of
        # a pixel, not on the edge
        y = 1 - (0.5 / self.pixel_height) - (merc_lat - merc_min) / \
                (merc_max - merc_min)
        #print ("Converted to %s, %s)" % (x, y))
        return (x, y)

    def _colour_is_constant(self):
        if self.config.get_colour_type() == "constant":
            return True
        return False

    def _linewidth_is_constant(self):
        if self.config.get_linewidth_type() == "constant":
            return True
        return False
        
    def _get_colour(self, speed, elevation):
        lw_type = self.config.get_colour_type() 
        if lw_type == "constant":
            return(self.config.get_colour())
        try:
            palette = self.config.get_palette()
        except ConfigError:
            print("Warning: no palette in config")
            palette = {0.0:(0,0,0), 1.0:(1,1,1)}
        if lw_type == "elevation":
            if elevation > self.max_elevation:
                return _interpolate_palette(1.0, palette)
            if elevation < self.min_elevation:
                return _interpolate_palette(0.0, palette)
            fraction = (elevation - self.min_elevation) / \
                       (self.max_elevation - self.min_elevation)
            return _interpolate_palette(fraction, palette)
        raise NotImplementedError
            
    def _get_linewidth(self, speed, elevation):
        lw_type = self.config.get_linewidth_type() 
        if lw_type == "constant":
            return(self.config.get_linewidth())
        lw_min = self.config.get_linewidth_min()
        lw_max = self.config.get_linewidth_max()
        if lw_type == "elevation":
            if elevation > self.max_elevation:
                return lw_max
            if elevation < self.min_elevation:
                return lw_min
            fraction = 1.0 * (elevation - self.min_elevation) / \
                             (self.max_elevation - self.min_elevation)
            width = lw_min + fraction * (lw_max - lw_min)
            return(width)
        if lw_type == "speed":
            if speed > self.max_speed:
                return lw_max
            if speed < self.min_speed:
                return lw_min
            fraction = 1.0 * (speed - self.min_speed) / \
                             (self.max_speed - self.min_speed)
            width = lw_min + fraction * (lw_max - lw_min)
            return(width)

        raise NotImplementedError

    def _draw_track(self, parsed_gpx):
        base_colour = self.config.get_basecolour() or DEFAULT_COLOUR
        variabletrack = not self._colour_is_constant() or \
                        not self._linewidth_is_constant()
        for track in parsed_gpx.tracks:
            for segment in track.segments:
                point_generator = (p for p in segment.points)
                first = point_generator.next()
                pixels = self._convert_to_fraction(Point(first.latitude,
                    first.longitude))
                self.ctx.move_to(*pixels)
                previous_point = first

                for eachpoint in point_generator:
                    next_point = Point(eachpoint.latitude,
                                       eachpoint.longitude)
                    pixels = self._convert_to_fraction(next_point)
                    self.ctx.line_to(*pixels)
                    if not variabletrack:
                        continue
                    speed = eachpoint.speed(previous_point)
                    elevation = eachpoint.elevation
                    current_colour = self._get_colour(speed, elevation)
                    current_width = self._get_linewidth(speed, elevation)
                    self.ctx.set_source_rgb(*current_colour) # Solid color
                    self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                    self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    self.ctx.set_line_width(current_width / self.pixel_width)
                    self.ctx.stroke()
                    # Start next line
                    self.ctx.move_to(*pixels)
                    previous_point = eachpoint

                if not variabletrack:
                    self.ctx.set_source_rgb(*base_colour) # Solid color
                    self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                    self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    self.ctx.set_line_width(1.0 / self.pixel_width)
                    self.ctx.stroke()
    
    def get_tracks(self):
        if self.config.savememory():
            for path in self._track_paths:
                with open(path, "r") as gpx_file:
                    yield gpxpy.parse(gpx_file)
        else:
            for track in self._track_objects:
                yield track

    @property
    def numtracks(self):
        if self.config.savememory():
            return len(self._track_paths)
        else:
            return len(self._track_objects)

    def add_track(self, path):
        with open(path, "r") as gpx_file:
            try:
                parsed = gpxpy.parse(gpx_file)
            except Exception:
                print("File did not parse correctly, skipping")
                return
            bounds = parsed.get_bounds()
            if self.max_latitude:
                if bounds.min_latitude > self.max_latitude or \
                        bounds.max_latitude < self.min_latitude or \
                        bounds.min_longitude > self.max_longitude or \
                        bounds.max_longitude < self.min_longitude:
                    print("Outside our specified area")
                    return
            min_date = self.config.get_min_date()
            max_date = self.config.get_max_date()
            if min_date or max_date:
                time_bounds = parsed.get_time_bounds()
                end_date = time_bounds.end_time.date()
                start_date = time_bounds.start_time.date()
                if min_date and end_date < min_date:
                    print("Before the specified time range")
                    return
                if max_date and start_date > max_date:
                    print("After the specified time range")
                    return
            if self.config.savememory():
                self._track_paths.append(path)
            else:
                self._track_objects.append(parsed)

            elev_extremes = parsed.get_elevation_extremes()

            if self.numtracks == 1:
                self.auto_min_latitude = bounds.min_latitude
                self.auto_max_latitude = bounds.max_latitude
                self.auto_min_longitude = bounds.min_longitude
                self.auto_max_longitude = bounds.max_longitude
                self.auto_min_elevation = elev_extremes.minimum
                self.auto_max_elevation = elev_extremes.maximum
                self.auto_min_elevation = elev_extremes.minimum
                self.auto_max_elevation = elev_extremes.maximum
                return

            if not self.min_latitude:
                if self.auto_min_latitude > bounds.min_latitude:
                    self.auto_min_latitude = bounds.min_latitude
                if self.auto_max_latitude < bounds.max_latitude:
                    self.auto_max_latitude = bounds.max_latitude
                if self.auto_min_longitude > bounds.min_longitude:
                    self.auto_min_longitude = bounds.min_longitude
                if self.auto_max_longitude < bounds.max_longitude:
                    self.auto_max_longitude = bounds.max_longitude

            if not self.min_elevation:
                if self.auto_min_elevation > elev_extremes.minimum:
                    self.auto_min_elevation = elev_extremes.minimum
                if self.auto_max_elevation < elev_extremes.maximum:
                    self.auto_max_elevation = elev_extremes.maximum

    def add_path(self, path):
        if os.path.isdir(path):
            self.add_directory(path)
        else:
            self.add_track(path)

    def add_directory(self, directory):
        print("Getting tracks from %s" % directory)
        for dir_path, _, filenames in os.walk(directory):
            gpxfiles = [filename for filename in filenames if
                    os.path.splitext(filename)[-1] == ".gpx"]
            print("Found %s gpx files from %s files in %s" % (len(gpxfiles),
                len(filenames), dir_path))
            for i in gpxfiles:
                self._all_tracks.append(os.path.join(dir_path, i))
        counter = 1
        for i in self._all_tracks:
            print("Adding file %4d/%4d: %s" % (counter,
                                               len(self._all_tracks), i))
            self.add_track(i)
            counter += 1

    def _detect_speeds(self):
        # In km/h
        self.min_speed = 1
        self.max_speed = 160

    def _detect_elevations(self):
        if self._colour_is_constant() and \
                self._linewidth_is_constant():
            print("Elevation detection not required")
            return
        currmin = None
        currmax = None
        print("Detecting min & max elevation (%s tracks)" % self.numtracks)
        for track in self.get_tracks():
            if not currmin:
                elev_extremes = track.get_elevation_extremes()
                currmin = elev_extremes.minimum
                currmax = elev_extremes.maximum
                continue
            currmin = min(currmin, elev_extremes.minimum)
            currmax = max(currmax, elev_extremes.maximum)
        self.min_elevation = currmin
        self.max_elevation = currmax
        print("Detected minimum elevation is %s" % self.min_elevation)
        print("Detected maximum elevation is %s" % self.max_elevation)

    def draw(self):
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
        self.surface = cairo.SVGSurface("/tmp/test.svg",
                                        float(self.pixel_width),
                                        float(self.pixel_height))
        self.ctx = cairo.Context(self.surface)
        self.ctx.scale (float(self.pixel_width), float(self.pixel_height))

        bkg = self.config.get_background()
        if bkg:
            if len(bkg) == 3:
                self.ctx.set_source_rgb(*bkg)
            elif len(bkg) == 4:
                self.ctx.set_source_rgba(*bkg)
            self.ctx.paint()

        print("Drawing %s tracks" % self.numtracks)
        counter = 0
        total = self.numtracks
        for track in self.get_tracks():
            counter += 1
            if counter % 10 == 0:
                print("Drawn %s of %s" % (counter, total))
            self._draw_track(track)

    def save_png(self, path):
        self.surface.write_to_png(path)

    def save_svg(self, path):
        self.surface.finish()
        raise NotImplementedError

def _interpolate_palette(fraction, palette):
    value_list = sorted(palette.keys())
    if fraction in value_list:
        return palette[fraction]
    previous_value = value_list[0]
    for value in value_list:
        if fraction > value:
            previous_value = value
            continue
        colour_fraction = (fraction - previous_value) / \
                          (value - previous_value)
        return _interpolate_colours(colour_fraction, palette[previous_value],
                                    palette[value])


def _interpolate_colours(fraction, start, end):
    output = []
    for i in range(3):
        diff = end[i] - start[i]
        output.append(start[i] + diff * fraction)
    return tuple(output)
