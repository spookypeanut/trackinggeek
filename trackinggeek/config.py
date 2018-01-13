import os
from ConfigParser import ConfigParser, NoSectionError, NoOptionError
from ast import literal_eval
from datetime import date
from calendar import monthrange

from trackinggeek.colour import Palette

class ConfigError(ValueError):
    pass

TRUESTRINGS = ["yes", "y", "1", "true", "t"]
FALSESTRINGS = ["no", "n", "0", "false", "f"]

def stringtobool(value):
    if value.lower() in TRUESTRINGS:
        return True
    if value.lower() in FALSESTRINGS:
        return False
    raise ValueError("%s is neither true or false" % value)

def get_multivalue(stringpair):
    try:
        # Get a pair in either 10x20 or 10,20 formats
        value_tuple = tuple(stringpair.replace("x", ",").split(","))
        return value_tuple
    except ValueError:
        msg = "Invalid format: %s" % stringpair
        raise ConfigError(msg)

class Config(ConfigParser):
    def __init__(self, filepath):
        ConfigParser.__init__(self)

        if filepath is not None:
            if not os.path.exists(filepath):
                raise IOError("Config file doesn't exist (%s)" % filepath)
            self.read(filepath)

    def _generic_single_getter(self, section, entry, override):
        try:
            if override:
                return override
            return self.get(section, entry)
        except (NoSectionError, NoOptionError):
            # If it's not in the config file or command line, our code
            # should have sensible defaults
            raise ConfigError("Entry [%s, %s] not found" % (section, entry))

    def _generic_multi_getter(self, section, entry, override):
        try:
            if override:
                return get_multivalue(override)
            return get_multivalue(self.get(section, entry))
        except (NoSectionError, NoOptionError):
            # If it's not in the config file or command line, our code
            # should have sensible defaults
            raise ConfigError("Entry [%s, %s] not found" % (section, entry))

    def get_units_per_frame(self, override=None):
        try:
            value = self._generic_single_getter("timelapse", "unitsperframe",
                                                override)
        except ConfigError:
            return 1
        return int(value)

    def get_timelapse_unit(self, override=None):
        try:
            value = self._generic_single_getter("timelapse", "unit",
                                                override)
        except ConfigError:
            return "track"
        return value

    def do_timelapse(self, override=None):
        try:
            value = self._generic_single_getter("timelapse", "timelapse",
                                                override)
        except ConfigError:
            return False
        return stringtobool(value)

    def get_palette(self):
        return Palette(self.get_palette_by_name(self.get_palette_name()))

    def get_palette_name(self):
        try:
            return self.get("drawing", "palette")
        except (NoSectionError, NoOptionError):
            msg = "No palette specified in config file"
            raise ConfigError(msg)

    def get_palette_by_name(self, name):
        try:
            pal_string = self.get("palettes", name)
            return literal_eval(pal_string)
        except (NoSectionError, NoOptionError):
            msg = "Palette %s doesn't exist" % name
            raise ConfigError(msg)

    def get_latitude(self, override=None):
        try:
            return self._generic_multi_getter("map", "latitude", override)
        except ConfigError:
            return None

    def get_longitude(self, override=None):
        try:
            return self._generic_multi_getter("map", "longitude", override)
        except ConfigError:
            return None

    def get_elevation_range(self, override=None):
        try:
            return self._generic_multi_getter("drawing", "elevation_range", override)
        except ConfigError:
            return None

    def get_speed_range(self, override=None):
        try:
            return self._generic_multi_getter("drawing", "speed_range", override)
        except ConfigError:
            return None

    def get_basecolour(self, override=None):
        try:
            result = self._generic_multi_getter("drawing", "basecolour", override)
        except ConfigError:
            return None
        if not result:
            return None
        return tuple([float(value) for value in result])

    def get_colour_type(self, override=None):
        """ Get the type of variation in the linewidth
        """
        value = self._generic_single_getter("drawing", "colour", override)
        if value in ("elevation", "speed"):
            return value
        try:
            value = self._generic_multi_getter("drawing", "colour", override)
        except ValueError:
            msg = "Invalid entry for colour in config: %s" % value
            raise ConfigError(msg)
        else:
            return "constant"

    def get_background(self, override=None):
        try:
            return tuple([float(value) for value in
                self._generic_multi_getter("drawing", "background", override)])
        except ConfigError:
            return None

    def get_colour(self, override=None):
        return tuple([float(value) for value in
                self._generic_multi_getter("drawing", "colour", override)])

    def get_linewidth_type(self, override=None):
        """ Get the type of variation in the linewidth
        """
        value = self._generic_single_getter("drawing", "linewidth", override)
        if value in ("elevation", "speed"):
            return value
        try:
            float(value)
        except ValueError:
            msg = "Invalid entry for linewidth in config: %s" % value
            raise ConfigError(msg)
        else:
            return "constant"

    def get_linewidth(self, override=None):
        if self.get_linewidth_type() != "constant":
            msg = "Linewidth is not constant: "
            msg += "use get_linewidth_type/min/max"
            raise ConfigError(msg)
        value = self._generic_single_getter("drawing", "linewidth", override)
        return float(value)

    def get_linewidth_min(self, override=None):
        value = self._generic_single_getter("drawing", "linewidth_min", override)
        return float(value)

    def get_linewidth_max(self, override=None):
        value = self._generic_single_getter("drawing", "linewidth_max", override)
        return float(value)

    def get_inputpath(self, override=None):
        return(self._generic_single_getter("input", "path",
            override))

    def get_outpng(self, override=None):
        try:
            return(self._generic_single_getter("output", "pngpath", override))
        except ConfigError:
            return None

    def get_outsvg(self, override=None):
        try:
            return(self._generic_single_getter("output", "svgpath", override))
        except ConfigError:
            return None

    def get_outma(self, override=None):
        try:
            return(self._generic_single_getter("output", "mapath", override))
        except ConfigError:
            return None

    def savememory(self, override=None):
        try:
            value = self._generic_single_getter("input", "savememory",
                                                override)
        except ConfigError:
            return True
        return stringtobool(value)

    def get_min_resolution(self, override=None):
        try:
            value = self._generic_single_getter("output", "minresolution",
                                                override)
        except ConfigError:
            return None
        if not value:
            return None
        return int(value)

    def get_max_resolution(self, override=None):
        try:
            value = self._generic_single_getter("output", "maxresolution",
                                                override)
        except ConfigError:
            return None
        if not value:
            return None
        return int(value)

    def get_resolution(self, override=None):
        try:
            return self._generic_multi_getter("output", "resolution", override)
        except ConfigError:
            return (None, None)

    def get_min_date(self):
        """ Get the earliest date to use for tracks. If not present in
        the config, return None
        """
        try:
            minyear = int(self._generic_single_getter("input", "minyear",
                            None))
        except ConfigError:
            return None
        try:
            minmonth = int(self._generic_single_getter("input", "minmonth",
                            None))
        except ConfigError:
            minmonth = 1
            minday = 1
        else:
            try:
                minday = int(self._generic_single_getter("input", "minday",
                            None))
            except ConfigError:
                minday = 1
        return date(minyear, minmonth, minday)

    def get_max_date(self):
        """ Get the latest date to use for tracks. If not present in
        the config, return None
        """
        try:
            maxyear = int(self._generic_single_getter("input", "maxyear",
                None))
        except ConfigError:
            return None
        try:
            maxmonth = int(self._generic_single_getter("input", "maxmonth",
                None))
        except ConfigError:
            maxmonth = 12
            maxday = 31
        else:
            try:
                maxday = int(self._generic_single_getter("input", "maxday",
                    None))
            except ConfigError:
                maxday = monthrange(maxyear, maxmonth)[1]
        return date(maxyear, maxmonth, maxday)

    def colour_is_constant(self):
        return self.get_colour_type() == "constant"

    def linewidth_is_constant(self):
        return self.get_linewidth_type() == "constant"
