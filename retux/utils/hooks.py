from cattrs import Converter, register_structure_hook
from ..client.resources.abc import Snowflake, Timestamp


def cattrs_structure_hooks(converter: Converter = None):
    """
    Hooks retux objects into the cattrs converter.
    Can be used to hook objects into a user made 
    converter as well.

    Parameters
    ----------
    converter : `Converter`, optional
        The converter to hook into, defaults to the
        global cattrs converter.
    """
    if converter:
        reg = converter.register_structure_hook
    else:
        reg = register_structure_hook
    reg(Snowflake, lambda d, t: t(d))
    reg(Timestamp, lambda d, t: t(d))
