class NoDeviceException(Exception):
    """Raised when an operation requiring an attached purpledrop is attempted
    but not device is currently connected
    """
    pass