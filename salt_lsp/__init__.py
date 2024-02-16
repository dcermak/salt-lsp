from importlib import metadata

try:
    __version__ = metadata.version(__package__)
except:
    __version__ = "dev"

del metadata  # avoid polluting the main namespace
