#!/usr/bin/env python

import sys
import re

def main():
    inputpath = sys.argv[1]
    outputpath = inputpath.replace(".gpx", "_cleaned.gpx")
    print "Cleaning from %s to %s" % (inputpath, outputpath)
    getlatlon = re.compile('[^"]*"([-.\d]*)"[^"]*"([-.\d]*)"[^"]*')
    try:
        inputfile = open(inputpath)
        outputfile = open(outputpath, "w")
    except IOError:
        print "%s doesn't exist?" % sys.argv
        return

    outputfile.write("<gpx><trk>\n")
    for i in inputfile.readlines():
        if "<trkpt" in i:
            lat, lon = getlatlon.match(i).groups()
            #print ("latitude: %s, longitude: %s" % (lat, lon))
            outputfile.write('<trkpt lat="%s" lon="%s" />\n' % (lat, lon))
        elif "trkseg" in i:
            outputfile.write(i)
    outputfile.write("</trk></gpx>")
if __name__ == "__main__":
    main()
