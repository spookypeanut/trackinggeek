import math
import os

def add_num_to_path(path, number):
    """ Convert an unnumbered path into a numbered one.
    E.g. blah.txt -> blah.0001.txt
    """
    if number is None:
        return path
    return (".%04d." % number).join(path.rsplit(".", 1))

def tracks_from_path(path):
    """ Given a path, which could be a directory, return an iterable (set
    probably) of full paths to gpx track files
    """
    tracks = set()
    if os.path.isfile(path):
        tracks.add(path)
        return tracks
    if not os.path.isdir(path):
        raise IOError("Path %s doesn't exist" % path)
    print("Getting tracks from %s" % path)
    for dir_path, _, filenames in os.walk(path):
        gpxfiles = [filename for filename in filenames if
                os.path.splitext(filename)[-1] == ".gpx"]
        for i in gpxfiles:
            tracks.add(os.path.join(dir_path, i))
    print("Found %s gpx in %s" % (len(tracks), path))
    return tracks

def mercator_adjust(lat):
    """ Create a mercator projection-adjusted latitude
    """
    return 180 / math.pi * math.log(math.tan(math.pi / 4 + lat *
                                                (math.pi / 180) / 2))

