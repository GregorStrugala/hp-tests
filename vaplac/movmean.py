import numpy as np

from .base import DataTaker

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
    Plot only one variable (say Tr):

    >>> a = np.random.rand(50)
    >>> mean = movmean(a, 20)

    """

    # Increment n if it is even
    n += 1 if n % 2 == 0 else 0
    l = (n-1) // 2  # edge length
    # Compute cumulative sum
    a_is_dimensional = isinstance(a, DataTaker.Q_)
    cumsum = (np.cumsum(a.magnitude, dtype=float) if a_is_dimensional
              else np.cumsum(a, dtype=float))
    # Get a moving sum everywhere but on the edges
    movsum = (np.append(cumsum[l:], np.zeros(l))
              - np.append(np.zeros(l+1), cumsum[:-l-1]))
    # Fill the edges by mirroring them and computing their moving sum
    cumsum_refl = np.cumsum(np.pad(a, (l+1, l+1), 'reflect'))
    movsum_refl = cumsum_refl[n:] - cumsum_refl[:-n]
    # print(movsum)
    # print(movsum_refl)
    movsum[:l] = movsum_refl[:l]
    movsum[-l:] = movsum_refl[-l-1:-1]
    if a_is_dimensional:
        return DataTaker.Q_(movsum / n, a.units, label=a.label, prop=a.prop)
    else:
        return movsum / n
