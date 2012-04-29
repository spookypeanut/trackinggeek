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

GPX_PATH = "./example/test.gpx"
OUTPUT_PATH = "/tmp/test.png"
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512

c = Canvas((51.51550, 51.53232), (-0.14138, -0.12016), (IMAGE_WIDTH, IMAGE_HEIGHT))
c.add_track(GPX_PATH)
c.draw()
c.save(OUTPUT_PATH)
