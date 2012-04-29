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

import Image
import gpxpy
from .point import Point

#MODE = "RGBA"
MODE = "L"
#DRAW_COLOR = (0, 0, 255, 255) 
DRAW_COLOR = 255

class Canvas(object):
    def __init__(self, latitude_range=None, longitude_range=None,
                 pixel_dimensions=None, max=True):
        self.image = Image.new(MODE, pixel_dimensions)
        self.pixel_width, self.pixel_height = pixel_dimensions

        if latitude_range:
            self.min_latitude = float(latitude_range[0])
            self.max_latitude = float(latitude_range[1])
        if longitude_range:
            self.min_longitude = float(longitude_range[0])
            self.max_longitude = float(longitude_range[1])

        self.tracks = []

    def _convert_to_pixels(self, point):
        x = int((self.pixel_width - 1) * (point.long - self.min_longitude) /
                                   (self.max_longitude - self.min_longitude))
        y = self.pixel_height - 1 - int((self.pixel_height - 1)*
                        (point.lat - self.min_latitude) /
                        (self.max_latitude - self.min_latitude))
        return (x, y)

    def _draw_point(self, point, radius=1):
        if point.long < self.min_longitude or \
           point.long > self.max_longitude or \
           point.lat < self.min_latitude or \
           point.lat > self.max_latitude:
                return

        pixel = self._convert_to_pixels(point)
        print ("Drawing pixel %s" % (pixel,))
        try:
            self.image.putpixel(pixel, DRAW_COLOR)
        except IndexError:
            print("Putting %s failed" % (pixel,))

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
        for track in self.tracks:
            for eachpoint in track.get_points_data():
                p = Point(eachpoint.point.latitude, eachpoint.point.longitude)
                self._draw_point(p)

    def save(self, path):
        self.image.save(path)

