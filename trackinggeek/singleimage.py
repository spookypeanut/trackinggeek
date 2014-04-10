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

from trackinggeek.genericimageoutput import GenericImageOutput
from trackinggeek.canvas import Canvas

class SingleImage(GenericImageOutput):
    def __init__(self, latitude_range=None, longitude_range=None,
                 elevation_range=None, speed_range=None,
                 pixel_dimensions=None, config=None):
        GenericImageOutput.__init__(self, latitude_range=latitude_range,
                                    longitude_range=longitude_range,
                                    elevation_range=elevation_range,
                                    speed_range=speed_range,
                                    pixel_dimensions=pixel_dimensions,
                                    config=config)

    def draw(self):
        self.prepare_to_draw()
        resolution = (self.pixel_width, self.pixel_height)
        latitude_range = (self.min_latitude, self.max_latitude)
        longitude_range = (self.min_longitude, self.max_longitude)
        elevation_range = (self.min_elevation, self.max_elevation)
        speed_range = (self.min_speed, self.max_speed)
        self.canvas = Canvas(resolution=resolution,
                             latitude_range=latitude_range,
                             longitude_range=longitude_range,
                             speed_range=speed_range,
                             elevation_range=elevation_range,
                             config=self.config)

        self.canvas.draw_tracks(self.tracks)

    def save_png(self, path):
        """ Save the canvas as a png file
        """
        self.draw()
        print("Saving png: %s" % path)
        self.canvas.surface.write_to_png(path)

    def save_svg(self, path):
        #self.surface.finish()
        raise NotImplementedError
