import numpy as np

def movmean(a, n):
    """
    Compute the moving mean of an array.

    Parameters
    ----------
    a : array_like
        Input array.
    n : int
        Size of the window used to compute the moving average.
        This value must be odd, otherwise it will be incremented.

    Returns
    -------
    array_like
        Moving mean of array a with window of size n.

    Examples
    --------
    >>> a = np.random.rand(50)
    >>> mean = vpa.movmean(a, 9)

    """

    # Increment n if it is even
    n += 1 if n % 2 == 0 else 0
    l = (n-1) // 2  # edge length
    # Compute cumulative sum
    cumsum = np.cumsum(a, dtype=float)
    # Get a moving sum everywhere but on the edges
    movsum = (np.append(cumsum[l:], np.zeros(l))
              - np.append(np.zeros(l+1), cumsum[:-l-1]))
    # Fill the edges by mirroring them and computing their moving sum
    cumsum_refl = np.cumsum(np.pad(a, (l+1, l+1), 'reflect'))
    movsum_refl = cumsum_refl[n:] - cumsum_refl[:-n]
    movsum[:l] = movsum_refl[:l]
    movsum[-l:] = movsum_refl[-l-1:-1]
    return movsum / n
