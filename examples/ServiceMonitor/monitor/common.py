class BaseModule(object):
    def __init__(self, options):
        self.options = self.get_default_options()

        if options is not None:
            self.options.update(options)

    def get_default_options(self):
        return {}
