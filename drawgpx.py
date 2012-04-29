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
from trackinggeek.point import Point

OUTPUT_PATH = "/tmp/test.png"
IMAGE_WIDTH = 128
IMAGE_HEIGHT = 128

c = Canvas((-1, 10), (-10, 100), (IMAGE_WIDTH, IMAGE_HEIGHT))

for x in [float(x) / 10 for x in xrange(0, 100)]:
    p = Point(x, x*x)
    print ("Doing pixel %s, %s" % (p.long, p.lat))
    c._draw_point(p)

c.save(OUTPUT_PATH)
