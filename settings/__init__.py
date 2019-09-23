from importlib import import_module

from . import default_settings


class BaseSettings:
    """
    An object that holds settings values.
    This also defines the base interface for all classes that are to be used
    as settings.
    """

    def __init__(self, module=None, attributes=None):
        """
        :param object/string module: A :class:`Settings <settings.Settings>`
        object or a path string.
        :param dict attributes: A dict object containing the settings values.
        """
        self.attributes = {}
        if module:
            self.add_module(module)
        if attributes:
            self.set_from_dict(attributes)

    @classmethod
    def from_params(cls, **kwargs):
        return cls(attributes=kwargs)

    @classmethod
    def object_from(cls, settings):
        """
        Generates a new settings object based on a previous obj or settings
        file.
        `settings` can either be a string path pointing to settings file or a \
        :class:`BaseSettings <settings.BaseSettings>` object instance.
        """
        if isinstance(settings, BaseSettings):
            return settings
        else:
            return cls(settings)

    def __getattr__(self, name):
        val = self.get(name)
        if val is not None:
            return val
        else:
            return self.__dict__[name]

    def __setattr__(self, name, value):
        if name.isupper():
            self.attributes[name] = value
        else:
            self.__dict__[name] = value

    def add_module(self, module):
        if isinstance(module, str):
            module = import_module(module)
        for key in dir(module):
            if key.isupper():
                self.set(key, getattr(module, key))

    def get(self, key, default_value=None):
        if not key.isupper():
            return None
        return self.attributes.get(key, default_value)

    def set(self, key, value):
        if key.isupper():
            self.attributes[key] = value

    def set_from_dict(self, attributes):
        for name, value in attributes.items():
            self.set(name, value)


class Settings(BaseSettings):
    def __init__(self, module=None, attributes=None):
        super(Settings, self).__init__(default_settings, attributes)

        if module:
            self.add_module(module)


SETTINGS = Settings()
