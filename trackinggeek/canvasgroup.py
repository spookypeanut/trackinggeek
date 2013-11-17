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

class _timelapse_options(object):
    def __init__(self, unit, number):
        self.unit = unit
        self.units_per_frame = number

class Frame(object):
    def __init__(self, canvas, paths):
        self.canvas = canvas
        self.paths = paths
        for path in paths:
            self.canvas.add_path(path)

class CanvasGroup(object):
    def __init__(self, pixel_dimensions,
                 latitude_range, longitude_range, config):
        self.pixel_dimensions = pixel_dimensions
        self.latitude_range = latitude_range
        self.longitude_range = longitude_range
        self.config = config

        self.paths = []
        if not config.do_timelapse():
            self.timelapse = None
        else:
            self.timelapse = _timelapse_options(config.get_timelapse_unit(),
                                                config.get_units_per_frame())

    def _get_canvas(self, number=None):
        return Canvas(pixel_dimensions=self.pixel_dimensions,
                      latitude_range=self.latitude_range,
                      longitude_range=self.longitude_range,
                      config=self.config, frame_num=number)

    def _prepare_frames(self):
        if self._frames_prepared:
            return
        self.frames = []
        self._sort_paths()
        if not self.timelapse:
            self.frames.append(Frame(self._get_canvas(), self.paths))
        elif self.timelapse.unit == "track":
            batchsize = self.timelapse.units_per_frame
            counter = 1
            # This splits a list into batches, ie
            # [1,2,3,4,5] -> [[1,2],[3,4],[5]]
            for pathlist in [self.paths[i:i+batchsize] for i in 
                                range(0, len(self.paths), batchsize)]:
                canvas = self._get_canvas(number=counter)
                self.frames.append(Frame(canvas, pathlist))
                counter += 1
        else:
            raise NotImplementedError("Don't know how to handle %s" %
                    self.timelapse)
        self._frames_prepared = True

    def _sort_paths(self):
        if self._paths_sorted:
            return
        self.paths.sort()
        self._paths_sorted = True

    def draw(self):
        self._prepare_frames()
        for frame in self.frames:
            frame.canvas.draw()

    def add_path(self, inputpath):
        self._paths_sorted = False
        self._frames_prepared = False
        self.paths.append(inputpath)

    def save_png(self, filepath):
        for frame in self.frames:
            frame.canvas.save_png(filepath)

    def save_svg(self, filepath):
        for frame in self.frames:
            frame.canvas.save_svg(filepath)
