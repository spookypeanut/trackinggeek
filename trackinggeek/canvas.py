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

import cairo
import gpxpy
from .point import Point

#MODE = "RGBA"
MODE = "L"
#DRAW_COLOR = (0, 0, 255, 255) 
DRAW_COLOR = 255
DEFAULT_SIZE = 1024

class Canvas(object):
    def __init__(self, latitude_range=None, longitude_range=None,
                 pixel_dimensions=None):
        # TODO: Have ability to override the automatic lat/long range
        if latitude_range:
            self.min_latitude = float(latitude_range[0])
            self.max_latitude = float(latitude_range[1])
        if longitude_range:
            self.min_longitude = float(longitude_range[0])
            self.max_longitude = float(longitude_range[1])

        self.pixel_dimensions = pixel_dimensions
        self.tracks = []

    def _calc_pixel_dimensions(self, pixel_dimensions):
        print ("Canvas._calc_pixel_dimensions(%s)" % (pixel_dimensions,))
        if pixel_dimensions is None or len(pixel_dimensions.keys()) == 0:
            pixel_dimensions = {"max":DEFAULT_SIZE}
        print pixel_dimensions
        if "width" in pixel_dimensions and "height" in pixel_dimensions:
            self.pixel_width = pixel_dimensions["width"]
            self.pixel_height = pixel_dimensions["height"]
            return
        self.aspect_ratio = (self.max_longitude - self.min_longitude) / \
                            (self.max_latitude - self.min_latitude)
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
            print(self.pixel_height)
            print(self.pixel_height)
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
        print pixel_dimensions
        raise ValueError("Could not calculate the image resolution")

    def _convert_to_fraction(self, point):
        x = (point.long - self.min_longitude) / \
            (self.max_longitude - self.min_longitude)
        y = 1 - (point.lat - self.min_latitude) / \
                (self.max_latitude - self.min_latitude)
        return (x, y)

    def _convert_to_pixels(self, point):
        x = int((self.pixel_width - 1) * (point.long - self.min_longitude) /
                                   (self.max_longitude - self.min_longitude))
        y = self.pixel_height - 1 - int((self.pixel_height - 1)*
                        (point.lat - self.min_latitude) /
                        (self.max_latitude - self.min_latitude))
        #print ("Converted to %s, %s" % (x, y))
        return (x, y)

    def _draw_point(self, point, radius=1):
        if point.long < self.min_longitude or \
           point.long > self.max_longitude or \
           point.lat < self.min_latitude or \
           point.lat > self.max_latitude:
                return

        pixel = self._convert_to_pixels(point)
        #print ("Drawing pixel %s" % (pixel,))
        try:
            self.image.putpixel(pixel, DRAW_COLOR)
        except IndexError:
            print("Putting %s failed" % (pixel,))

    def _draw_track(self, track):
        point_generator = (p for p in track.get_points_data())
        first = point_generator.next().point
        print("Starting at %s" % first)
        pixels = self._convert_to_fraction(Point(first.latitude,
            first.longitude))
        print pixels
        self.ctx.move_to(*pixels)
        for eachpoint in point_generator:
            next_point = Point(eachpoint.point.latitude,
                               eachpoint.point.longitude)
            self.ctx.line_to(*self._convert_to_fraction(next_point))

        self.ctx.set_source_rgb(0.3, 0.2, 0.5) # Solid color
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.ctx.set_line_width(1.0 / self.pixel_width)
        self.ctx.stroke()
    

    def add_track(self, path):
        gpx_file = open(path, "r")
        parsed = gpxpy.parse(gpx_file)
        self.tracks.append(parsed)
        bounds = parsed.get_bounds()
        if len(self.tracks) == 1:
            print ("Setting ranges:")
            self.min_latitude = bounds.min_latitude
            self.max_latitude = bounds.max_latitude
            print("latitude = %s - %s" % (self.min_latitude,
                self.max_latitude))
            self.min_longitude = bounds.min_longitude
            self.max_longitude = bounds.max_longitude
            print("longitude = %s - %s" % (self.min_longitude,
                self.max_longitude))
            return
        if self.min_latitude > bounds.min_latitude:
            self.min_latitude = bounds.min_latitude
        if self.max_latitude < bounds.max_latitude:
            self.max_latitude = bounds.max_latitude
        if self.min_longitude > bounds.min_longitude:
            self.min_longitude = bounds.min_longitude
        if self.max_longitude < bounds.max_longitude:
            self.max_longitude = bounds.max_longitude

    def draw(self):
        self._calc_pixel_dimensions(self.pixel_dimensions)
        self.surface = cairo.SVGSurface("/tmp/test.svg",
                                        float(self.pixel_width),
                                        float(self.pixel_height))
        self.ctx = cairo.Context(self.surface)
        self.ctx.scale (float(self.pixel_width), float(self.pixel_height))

        for track in self.tracks:
            self._draw_track(track)

    def save_png(self, path):
        self.surface.write_to_png(path)

    def save_svg(self, path):
        self.surface.finish()
        raise NotImplementedError
