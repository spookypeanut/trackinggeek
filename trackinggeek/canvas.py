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
from point import Point
from trackinggeek.colour import DEFAULT_COLOUR, DEFAULT_PALETTE
from trackinggeek.util import mercator_adjust
from trackinggeek.config import ConfigError
from trackinggeek.tracklibrary import OldTrackLibrary


class Canvas(object):
    """ An object to draw our tracks on, and output the resulting image
    in a selection of formats
    """
    def __init__(self, resolution, latitude_range, longitude_range,
                 speed_range, elevation_range, config):
        self.pixel_width, self.pixel_height = resolution
        self.min_merc_latitude, self.max_merc_latitude = map(mercator_adjust,
                                                             latitude_range)
        self.merc_latitude_width = self.max_merc_latitude - \
                                   self.min_merc_latitude
        self.min_longitude, self.max_longitude = longitude_range
        self.min_speed, self.max_speed = speed_range
        self.min_elevation, self.max_elevation = elevation_range
        self.config = config
        self.setup_context()

    def setup_context(self):
        self.surface = cairo.SVGSurface("/tmp/test.svg",
                                        float(self.pixel_width),
                                        float(self.pixel_height))
        self.ctx = cairo.Context(self.surface)
        self.ctx.scale(float(self.pixel_width), float(self.pixel_height))

        bkg = self.config.get_background()
        if bkg:
            if len(bkg) == 3:
                self.ctx.set_source_rgb(*bkg)
            elif len(bkg) == 4:
                self.ctx.set_source_rgba(*bkg)
            self.ctx.paint()

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
        merc_lat = mercator_adjust(point.lat)
        # Subtract half a pixel width so that we're drawing in the
        # centre of a pixel, not on the edge
        y = 1 - (0.5 / self.pixel_height) - \
                (merc_lat - self.min_merc_latitude) / self.merc_latitude_width
        return (x, y)

    def _draw_track(self, track):
        base_colour = self.config.get_basecolour() or DEFAULT_COLOUR
        variabletrack = not self.config.colour_is_constant() or \
                        not self.config.linewidth_is_constant()
        for segment in track.get_segments():
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
                speed = eachpoint.speed_between(previous_point)
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

    def _get_colour(self, speed, elevation):
        lw_type = self.config.get_colour_type()
        if lw_type == "constant":
            return(self.config.get_colour())
        try:
            palette = self.config.get_palette()
        except ConfigError:
            print("Warning: no palette in config")
            palette = DEFAULT_PALETTE
        if lw_type == "elevation":
            if elevation > self.max_elevation:
                return palette.interpolate(1.0)
            if elevation < self.min_elevation:
                return palette.interpolate(0.0)
            fraction = (elevation - self.min_elevation) / \
                       (self.max_elevation - self.min_elevation)
            return palette.interpolate(fraction)
        if lw_type == "speed":
            if speed > self.max_speed:
                return palette.interpolate(1.0)
            if speed < self.min_speed:
                return palette.interpolate(0.0)
            fraction = (speed - self.min_speed) / \
                       (self.max_speed - self.min_speed)
            return palette.interpolate(fraction)
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

    def draw_tracks(self, paths):
        tl = OldTrackLibrary()
        counter = 0
        total = len(paths)
        print("Drawing %s tracks" % total)
        for path in paths:
            counter += 1
            if counter % 100 == 0:
                print("\tDrawn %s of %s" % (counter, total))
            self._draw_track(tl[path])
