#!/usr/bin/env python
import urllib
import re
from ast import literal_eval
import sys

# TODO: argparse
do_background = True
url = sys.argv[1]
w = urllib.urlopen(url)
for line in w.readlines():
    if "var _paletteColorsUI" in line:
        colourline = line
    if "/lover/" in line:
        loverline = line

extract_name = re.compile("([\w]+)/?$")
name = extract_name.search(url).groups()[0]
name = name.lower()
extract_lover_url = re.compile("(/lover/[^/\"]*)")
m = extract_lover_url.search(loverline)
lover_partial_url = m.groups()[0]
lover_url = "http://www.colourlovers.com" + lover_partial_url
lover = lover_partial_url.split("/")[-1]
extract_colours = re.compile(".*\"_colors\":(\[[\"0-9A-F,]*\])")
m = extract_colours.match(colourline)
hexlist = literal_eval(m.groups()[0])
floatlist = []
for h in hexlist:
    intnums = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    stringnums = []
    for i in intnums:
        stringnums.append("%0.5f" % (float(i) / 255))
    floatlist.append(tuple(stringnums))

step = 1.0 / (len(floatlist) - 1)
print "palette = %s" % name
if do_background:
    background = floatlist.pop(0)
    print("background = %s" % ",".join(background))
currentpos = 0.0
outstring = "%s = {" % name
strings = []
for i in floatlist:
    outstring += "%0.1f" % currentpos 
    outstring += ": ("
    outstring += ",".join(i)

    outstring += "),"
    strings.append(outstring)

    currentpos += step
    outstring = ""

# Replace the last , with a }
strings[-1] = strings[-1][:-1] + "}"
print "# Thanks to %s (%s) for the palette" % (lover, lover_url)
print "# %s" % url
for i in strings:
    print i
