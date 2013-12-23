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

DEFAULT_COLOUR = (0.3, 0.2, 0.5)

class Palette(dict):
    """ A colour palette, defined as a dictionary with the keys as numbers
    (0-1) with a colour as their values.
    """
    def interpolate(self, fraction):
        if fraction in self.keys():
            return self[fraction]
        value_list = sorted(self.keys())
        previous_value = value_list[0]
        for value in value_list:
            if fraction > value:
                previous_value = value
                continue
            colour_fraction = (fraction - previous_value) / \
                              (value - previous_value)
            return _interpolate_colours(colour_fraction, self[previous_value],
                                        self[value])

DEFAULT_PALETTE = Palette({0.0:(0,0,0), 1.0:(1,1,1)})

def _interpolate_colours(fraction, start, end):
    output = []
    for i in range(3):
        diff = end[i] - start[i]
        output.append(start[i] + diff * fraction)
    return tuple(output)
