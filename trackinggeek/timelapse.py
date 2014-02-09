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

from copy import deepcopy
from trackinggeek.genericimageoutput import GenericImageOutput
from trackinggeek.canvas import Canvas
from trackinggeek.util import add_num_to_path
from trackinggeek.track import TrackLibrary

class Timelapse(GenericImageOutput):
    def __init__(self, latitude_range=None, longitude_range=None,
                 pixel_dimensions=None, config=None):
        GenericImageOutput.__init__(self, latitude_range=latitude_range,
                                    longitude_range=longitude_range,
                                    pixel_dimensions=pixel_dimensions,
                                    config=config)
        self._frames_prepared = False
        self.timelapse_unit = config.get_timelapse_unit()
        self.units_per_frame = config.get_units_per_frame()

    def draw(self):
        self.prepare_to_draw()
        self.resolution = (self.pixel_width, self.pixel_height)
        self.latitude_range = (self.min_latitude, self.max_latitude)
        self.longitude_range = (self.min_longitude, self.max_longitude)
        self.speed_range = (self.min_speed, self.max_speed)
        self.elevation_range = (self.min_elevation, self.max_elevation)
        self._prepare_frames()
        counter = 0
        for f in self.frames:
            counter += 1
            print("Drawing frame %s/%s" % (counter, len(self.frames)))
            f.draw()

    def save_png(self, path):
        """ Save the canvas as a png file
        """
        for f in self.frames:
            num_path = add_num_to_path(path, f.frame_number)
            f.canvas.surface.write_to_png(num_path)

    def save_svg(self, path):
        #self.surface.finish()
        raise NotImplementedError

    def _get_canvas(self, frame_number):
        return Canvas(resolution=self.resolution,
                      latitude_range=self.latitude_range,
                      longitude_range=self.longitude_range,
                      speed_range=self.speed_range,
                      elevation_range=self.elevation_range,
                      config=self.config)

    def _prepare_frames(self):
        if self._frames_prepared:
            return
        tl = TrackLibrary()
        # TODO: We might want to do some cleverer sorting
        tracks = tl.sort_tracks_by_time()
        self.frames = []
        if self.timelapse_unit == "track":
            batchsize = self.units_per_frame
            # This splits a list into batches, ie
            # [1,2,3,4,5] -> [[1,2],[3,4],[5]]
            cumulative_tracks = []
            counter = 0
            print("Creating frames")
            startnums = xrange(0, len(tracks), batchsize)
            # The end number should be 1 more than might be expected,
            # because of the way python list slicing works
            batches = [(s, s + batchsize) for s in startnums]
            total = len(batches)
            for tracklist in (tracks[s:e] for (s, e) in batches):
                counter += 1
                if counter % 10 == 0 and total > 20:
                    print("\tCreated %s/%s frames" % (counter, total))
                cumulative_tracks.extend(tracklist)
                canvas = self._get_canvas(counter - 1)
                self.frames.append(Frame(canvas=canvas,
                                         tracks=deepcopy(cumulative_tracks),
                                         frame_number=counter-1))
        else:
            raise NotImplementedError("Don't know how to handle %s" %
                    self.timelapse_unit)
        self._frames_prepared = True

class Frame(object):
    def __init__(self, canvas, tracks, frame_number):
        self.canvas = canvas
        # Let's keep this. We might want to postpone the track parsing
        # in future
        self.tracks = tracks
        self.frame_number = frame_number

    def draw(self):
        self.canvas.draw_tracks(self.tracks)
