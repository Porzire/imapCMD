import sys

def _check_color():
    """ Check the availbility of using color in the terminal.
    """
    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
    # isatty is not always implemented.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if supported_platform and is_a_tty:
        return True
    else:
        return False

# True if terminal support color.
SUPPORT_COLOR = _check_color()

def printd(info, highlight=False):
    """ Print given information if debug flag is set to True.

    The default pirinting color is dim.

    Args:
        info:      The debugging information to be printed.
        highlight: Use highlight instead of dim if ture.
    """
    if __debug__:
        if SUPPORT_COLOR:
            prefix = '\033[1m' if highlight else '\033[2m'
            info = prefix + str(info) + '\033[0m'
        sys.stdout.write(info)

def printe(exception):
    """ Print the error information of the given Exception.

    Args:
        exception: The exception to be printed.
    """
    print(str(exception).strip('\''))
