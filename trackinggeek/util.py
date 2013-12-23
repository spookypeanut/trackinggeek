import math
import os

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
        print("Found %s gpx files from %s files in %s" % (len(gpxfiles),
            len(filenames), dir_path))
        for i in gpxfiles:
            tracks.add(os.path.join(dir_path, i))
    return tracks

def mercator_adjust(self, lat):
    """ Create a mercator projection-adjusted latitude
    """
    return 180 / math.pi * math.log(math.tan(math.pi / 4 + lat *
                                                (math.pi / 180) / 2))

