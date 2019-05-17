import numpy as np

def humidity(field, exp, error):
    wr, ws = exp.get('wr ws')
    overhum = (wr < ws).sum() / len(wr)
    if overhum:
        msg = ('The supply humidity ratio exceeds '
               'the return humidity ratio {:.1%} of the time.')
        error(field, msg.format(overhum))

def cycling(field, exp, error):
    varf = np.var(exp.get('f'))
    if varf > exp.Q_('400 Hz**2'):
        error(field, 'There appears to be short cycling.')
    elif varf > exp.Q_('100 Hz**2'):
        error(field, 'There appears to be cycling with long steps.')
