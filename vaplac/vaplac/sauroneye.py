"""
This modules regroups all the check functions used to validate the data
read by a DataTaker. Each function corresponds to a particular test.

"""

import numpy as np

# Store quantities used to check the data,
# for plotting in DataTaker.validate method.
_checkargs = {}

def humidity_check(field, dtk, error):
    """Check whether the humidity ratio is increasing."""
    _checkargs['humidity_check'] = '(wr ws)'
    wr, ws = dtk.get('wr ws')
    overhum = (wr < ws).sum() / len(wr)
    if overhum > 0.02:
        msg = ('The supply humidity ratio exceeds '
               f'the return humidity ratio {overhum:.1%} of the time.')
        error(field, msg)

def cycling_check(field, dtk, error):
    """Check if there is cycling."""
    _checkargs['cycling_check'] = 'f'
    window_size = 15
    f = dtk.get('f')
    fmean = f.movmean(window_size)
    interval = slice(window_size//2, -window_size//2)
    variance = np.var(f[interval] - fmean[interval])
    if variance > dtk.Q_('100 Hz**2'):
        error(field, 'There appears to be cycling.')
