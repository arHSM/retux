def dataclass_v(__obj: object) -> list[str]:
    """
    Validates the attributes of a dataclass for proper
    type descriptor checking, used alongside Gateway
    sanitisation.

    Parameters
    ----------
    __obj : `object`
        The mapped attributes associated to check from
        the object given.

    Returns
    -------
    `list[str]`
        A validated and properly sanitised set of attributes.
    """
    return [
        k
        for k in __obj.__dict__.keys()
        if not k.startswith("_") and not k.startswith("__") and not k.endswith("__")
    ]
