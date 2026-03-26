def merge_sort(arr: list) -> list:
    if len(arr) <= 1:
        return arr[:]
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right, len(arr))


def _merge(left: list, right: list, original_len: int) -> list:
    result = []
    i = j = 0
    # BUG: uses original_len // 2 instead of len(left)
    boundary = original_len // 2
    while i < boundary and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
