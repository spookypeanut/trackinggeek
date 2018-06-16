#!/usr/bin/env python
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

import sys
import argparse
from trackinggeek.config import Config
from trackinggeek.singleimage import SingleImage
from trackinggeek.timelapse import Timelapse


def OutputImage(pixel_dimensions, latitude_range, longitude_range,
                elevation_range, speed_range, config):
    if config.do_timelapse():
        return Timelapse(pixel_dimensions=pixel_dimensions,
                         latitude_range=latitude_range,
                         longitude_range=longitude_range,
                         elevation_range=elevation_range,
                         speed_range=speed_range,
                         config=config)
    return SingleImage(pixel_dimensions=pixel_dimensions,
                       latitude_range=latitude_range,
                       longitude_range=longitude_range,
                       elevation_range=elevation_range,
                       speed_range=speed_range,
                       config=config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', action='store',
                        help='path to the config file to use for defaults')
    parser.add_argument('--inputpath', action='store',
                        help='path to the gpx file / directory of gpx files')
    parser.add_argument('--databasepath', action='store',
                        help='path to the gpx file database root directory')
    parser.add_argument('--outsvg', action='store',
                        help='path to the output svg')
    parser.add_argument('--outpng', action='store',
                        help='path to the output png')
    parser.add_argument('--outma', action='store',
                        help='path to the output Maya ascii file')
    parser.add_argument('--resolution', action='store',
                        help='absolute resolution of the output image')
    parser.add_argument('--max', action='store',
                        help='the maximum of either dimension of the'
                        'output image')
    parser.add_argument('--min', action='store',
                        help='the minimum of either dimension of the'
                        'output image')
    parser.add_argument('--latitude', action='store',
                        help='the latitude range to use, e.g. 43.1,45.6')
    parser.add_argument('--longitude', action='store',
                        help='the longitude range to use, e.g. -2.3,1.2')
    args = parser.parse_args()

    pixel_dimensions = {}
    config = Config(args.config)

    latitude_range = config.get_latitude(args.latitude)
    longitude_range = config.get_longitude(args.longitude)

    tmp = config.get_elevation_range()
    if tmp:
        elevation_range = (float(tmp[0]), float(tmp[1]))
    else:
        elevation_range = None
    tmp = config.get_speed_range()
    if tmp:
        speed_range = (float(tmp[0]), float(tmp[1]))
    else:
        speed_range = None

    # TODO: Even if resolution is specified in the config, a
    # command-line min / max should override it
    pixel_dimensions["min"] = config.get_min_resolution(args.min)
    pixel_dimensions["max"] = config.get_max_resolution(args.max)

    x, y = config.get_resolution(args.resolution)

    if x and y:
        pixel_dimensions["width"] = int(x)
        pixel_dimensions["height"] = int(y)

    inputpath = config.get_inputpath(args.inputpath)
    databasepath = config.get_databasepath(args.databasepath)

    outpng = config.get_outpng(args.outpng)
    outsvg = config.get_outsvg(args.outsvg)
    outma = config.get_outma(args.outma)

    c = OutputImage(pixel_dimensions=pixel_dimensions,
                    latitude_range=latitude_range,
                    longitude_range=longitude_range,
                    elevation_range=elevation_range,
                    speed_range=speed_range,
                    config=config)
    if inputpath:
        c.add_path(inputpath)
    if databasepath:
        c.add_path(databasepath)
    if outma:
        c.save_ma(outma)
    if outpng:
        c.save_png(outpng)
    if outsvg:
        c.save_svg(outsvg)

if __name__ == "__main__":
    sys.exit(main())
