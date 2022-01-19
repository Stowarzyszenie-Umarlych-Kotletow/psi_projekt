from simple_p2p.file_transfer.exceptions import InvalidRangeError


def calc_range_len(actual_size: int, offset: int, num_bytes: int = None) -> int:
    """
    Helper method to calculate the byte length of a given range.
    If num_bytes is null, the file is read until EOF.
    This function raises `InvalidRangeError`.
    """
    if offset > actual_size:
        raise InvalidRangeError("Offset past file length")
    offset_len = actual_size - offset  # the number of bytes left
    if num_bytes is None:
        return offset_len
    if num_bytes > offset_len:
        raise InvalidRangeError("Number of bytes past file length")
    return num_bytes
