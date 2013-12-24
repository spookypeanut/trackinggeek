from trackinggeek.genericimageoutput import GenericImageOutput
from trackinggeek.canvas import Canvas

class SingleImage(GenericImageOutput):
    def __init__(self, latitude_range=None, longitude_range=None,
                 pixel_dimensions=None, config=None):
        GenericImageOutput.__init__(self, latitude_range=latitude_range,
                                    longitude_range=longitude_range,
                                    pixel_dimensions=pixel_dimensions,
                                    config=config)

    def draw(self):
        self.prepare_to_draw()
        resolution = (self.pixel_width, self.pixel_height)
        latitude_range = (self.min_latitude, self.max_latitude)
        longitude_range = (self.min_longitude, self.max_longitude)
        speed_range = (self.min_speed, self.max_speed)
        elevation_range = (self.min_elevation, self.max_elevation)
        self.canvas = Canvas(resolution=resolution,
                             latitude_range=latitude_range,
                             longitude_range=longitude_range,
                             speed_range=speed_range,
                             elevation_range=elevation_range,
                             config=self.config)

        self.canvas.draw_tracks(self.tracks)

    def save_png(self, path):
        """ Save the canvas as a png file
        """
        self.canvas.surface.write_to_png(path)

    def save_svg(self, path):
        #self.surface.finish()
        raise NotImplementedError
