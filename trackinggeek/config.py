import os
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

class ConfigError(ValueError):
    pass

def get_value_pair(stringpair):
    try:
        # Get a pair in either 10x20 or 10,20 formats
        min_value, max_value = stringpair.replace("x", ",").split(",")
        return (min_value, max_value)
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

    def _generic_dual_getter(self, section, entry, override):
        try:
            if override:
                return get_value_pair(override)
            return get_value_pair(self.get(section, entry))
        except (NoSectionError, NoOptionError):
            # If it's not in the config file or command line, our code
            # should have sensible defaults
            return (None, None)

    def get_latitude(self, override=None):
        return self._generic_dual_getter("map", "latitude", override)

    def get_longitude(self, override=None):
        return self._generic_dual_getter("map", "longitude", override)

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
        return self._generic_dual_getter("output", "resolution", override)
