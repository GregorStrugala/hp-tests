import numpy as np

_checkargs = {}  # Store quantities used to check the data.

def humidity_check(field, exp, error):
    _checkargs['humidity_check'] = '(wr ws)'
    wr, ws = exp.get('wr ws')
    overhum = (wr < ws).sum() / len(wr)
    if overhum:
        msg = ('The supply humidity ratio exceeds '
               'the return humidity ratio {:.1%} of the time.')
        error(field, msg.format(overhum))

def cycling_check(field, exp, error):
    _checkargs['cycling_check'] = 'f'
    varf = np.var(exp.get('f'))
    if varf > exp.Q_('400 Hz**2'):
        error(field, 'There appears to be short cycling.')
    elif varf > exp.Q_('100 Hz**2'):
        error(field, 'There appears to be cycling with long steps.')
