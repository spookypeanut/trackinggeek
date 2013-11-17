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

from trackinggeek.canvas import Canvas

class CanvasGroup(object):
    def __init__(self, pixel_dimensions,
                 latitude_range, longitude_range, config):
        self.canvases = []
        if not config.do_timelapse():
            self.canvases.append(Canvas(pixel_dimensions=pixel_dimensions,
                                        latitude_range=latitude_range,
                                        longitude_range=longitude_range,
                                        config=config))
            return
        raise NotImplementedError("Not done timelapse yet")

    def draw(self):
        for canvas in self.canvases:
            canvas.draw()

    def add_path(self, inputpath):
        for i in self.canvases:
            i.add_path(inputpath)

    def save_png(self, filepath):
        for i in self.canvases:
            i.save_png(filepath)

    def save_svg(self, filepath):
        for i in self.canvases:
            i.save_svg(filepath)
