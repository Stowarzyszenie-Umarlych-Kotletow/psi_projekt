from file_transfer.exceptions import InvalidRangeError


def calc_range_len(actual_size: int, offset: int, num_bytes: int = None) -> int:
    if offset > actual_size:
        raise InvalidRangeError("Offset past file length")
    offset_len = actual_size - offset  # the number of bytes left
    if num_bytes is None:
        return offset_len
    if num_bytes > offset_len:
        raise InvalidRangeError("Number of bytes past file length")
    return num_bytes
