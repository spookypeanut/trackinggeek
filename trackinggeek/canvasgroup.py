from trackinggeek.canvas import Canvas

class CanvasGroup(object):
    def __init__(self, pixel_dimensions,
                 latitude_range, longitude_range, config):
        self.canvases = []
        if not config.do_timelapse():
            self.canvases.append(Canvas(pixel_dimensions=pixel_dimensions,
                                        latitude_range=latitude_range,
                                        longitude_range=longitude_range,
                                        config=config))

    def add_path(self, inputpath):
        for i in self.canvases:
            i.add_path(inputpath)

    def save_png(self, filepath):
        for i in self.canvases:
            i.save_png(filepath)

    def save_svg(self, filepath):
        for i in self.canvases:
            i.save_svg(filepath)
