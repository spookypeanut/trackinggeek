import os
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

class ConfigError(ValueError):
    pass

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
            return None

    def _generic_multi_getter(self, section, entry, override):
        try:
            if override:
                return get_multivalue(override)
            return get_multivalue(self.get(section, entry))
        except (NoSectionError, NoOptionError):
            # If it's not in the config file or command line, our code
            # should have sensible defaults
            return (None, None)

    def get_latitude(self, override=None):
        return self._generic_multi_getter("map", "latitude", override)

    def get_longitude(self, override=None):
        return self._generic_multi_getter("map", "longitude", override)

    def get_basecolour(self, override=None):
        return tuple([float(value) for value in 
                self._generic_multi_getter("drawing", "basecolour", override)])

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

    def get_min_resolution(self, override=None):
        value = self._generic_single_getter("output", "minresolution",
                                            override)
        if value:
            return int(value)
        return value

    def get_max_resolution(self, override=None):
        value = self._generic_single_getter("output", "maxresolution",
                                            override)
        if value:
            return int(value)
        return value

    def get_resolution(self, override=None):
        return self._generic_multi_getter("output", "resolution", override)
