import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot(*args, time='min', step=60, interval=slice(0, None),
         sharex='col', legend=True, lf=True, loc='best'):
    """
    Plot variables specified as arguments against time.

    Parameters
    ----------
    *args : xpint Quantity, or list of xpint Quantity
        The quantities to be plotted. Quantities grouped in a list are
        plotted in the same axis.
    time : {'s', 'min', 'h', 'day'} or ndarray, default 'min'
        Controls what is displayed on the x-axis. If 's', 'min', 'h' or
        'day' is given, a minute timestep is assumed by default and the
        x-axis is created to fit the length of variables in `*args` (see
        `step` parameter to set another timestep).
        Alternatively, an explicit array can be given
        (including datetime arrays).
    step : int or float
        The timestep between each measurement in seconds.
    interval : slice, default slice(0, None)
        A slice object containing the range over which the quantities
        are plotted.
    sharex : bool or {'none', 'all', 'row', 'col'}, default 'col'
        Controls sharing of properties among x axis (see parameter
        `sharex` in `matplotlib.pyplot.subplots` function)
    legend : bool, default True
        When set to False, no legend is displayed.
    lf : bool, default True
        When set to False, a legend frame is displayed.
    loc : int or string or pair of floats, default 'best'
        See `loc` parameter in `matplotlib.pyplot.legend`.

    Examples
    --------
    Plot only one variable (say Tr):

    >>> plot(Tr)

    Plot several variables (say Tr, Ts, f) without legend frame:

    >>> plot(Tr, Ts, f, lf=False)

    Group some variables (say Tr, Ts) in the same axis:

    >>> plot([Tr, Ts], f)

    """

    res = {'s':1/step, 'min':60/step, 'h':3600/step, 'days':86400/step}
    properties = {
        'temperature':'$T$', 'electrical power':'$P$',
        'mechanical power':'$\dot{W}$','heat transfer rate':'$\dot{Q}$',
        'difference of internal energy rate of change':'$\Delta\dot U$',
        'flow rate':'$\dot{m}$', 'frequency':'$f$', 'pressure':'$p$',
        'specific enthalpy':'$h$', 'relative humidity':'$\phi$',
        'absolute humidity':'$\omega$', 'state':'$\gamma$',
        'relative error':'$\delta$'
    }

    # Store this boolean as it is used numerous times.
    t_str = isinstance(time, str)

    a0_list = isinstance(args[0], list)
    length = len(args[0][0][interval] if a0_list else args[0][interval])
    t = np.arange(0, length) / res[time] if t_str else time[interval]

    warn_msg_dim = ('Quantities with different dimensionalities '
                    'are displayed on the same plot')
    warn_msg_unit = ('Quantities with different units '
                     'are displayed on the same plot')

    # Create the statusbar string to be formatted.
    statusbar = {True:'time: {:.2f} {}     {}: {:.2f} {}',
                 False:'time: {}     {}: {:.2f} {}'}[t_str]

    # Create the figure and axis.
    fig, ax = plt.subplots(len(args), sharex=sharex, facecolor=(.93,.93,.93))

    def y_label(q, attr):
        """Create a y label for the quantity q."""
        # Ensure that there is a non-empty label
        # or a property listed in the properties dictionary
        if (attr == 'label' and q.label is None or
            attr == 'prop' and q.prop not in properties):
            return None

        pre = {'label':q.label, 'prop':properties[q.prop]}.get(attr, '')

        # Cannot use Quantity().dimensionless in case of percentages
        if str(q.units) != 'dimensionless':
            post = ' ({:~P})'.format(q.units)
        else:
            post = ''

        return pre + post if pre + post != '' else None


    def fmtr(x, y, sbdim, sbunit, ax):
        """Make a formatter for the axis statusbar"""
        if t_str:
            return statusbar.format(x, time, sbdim, y, sbunit)
        else:
            def datefmt(ax):
                t_min, t_max = (int(t) for t in ax.get_xlim())
                fmt = '%d %H:%M:%S' if t_max-t_min > 0 else '%H:%M:%S'
                return mdates.DateFormatter(fmt)
            return statusbar.format(datefmt(ax)(x), sbdim, y, sbunit)

    if len(args) == 1:  # There is only one axis (that may have several plots).

        if not isinstance(args[0], list):  # There is only one plot.
            ax.plot(t, args[0][interval])
            ax.set(ylabel=y_label(args[0], 'label'))
            # Label (or property) and units used in status bar
            sbdim, sbunit = args[0].prop, '{:~P}'.format(args[0].units)

        else:  # There are several plots.
            for var in args[0]:
                ax.plot(t, var[interval], label=var.label)
                
                if var.dimensionality != args[0][0].dimensionality:
                    warnings.warn(warn_msg_dim)
                if var.units != args[0][0].units:
                    warnings.warn(warn_msg_unit)

            # The y-label is by default that of the last element.
            ax.set(ylabel=y_label(args[0][-1], 'prop'))

            sbdim, sbunit = args[0][-1].prop, '{:~P}'.format(args[0][-1].units)
            if legend:
                ax.legend(loc=loc, frameon=lf)

        ax.format_coord = lambda x, y: fmtr(x, y, sbdim, sbunit, ax)

    else:  # There are several subplots.
        for i, var in enumerate(args):
            # If var is not a list, there is only one variable
            # to be plotted in the current subplot.
            if not isinstance(var, list):
                ax[i].plot(t, var[interval].magnitude)
                ax[i].set(ylabel=y_label(var, 'label'))
                sbdim, sbunit = var.prop, '{:~P}'.format(var.units)
            else:
                for var2 in var:
                    ax[i].plot(t, var2[interval].magnitude, label=var2.label)

                if var2.dimensionality != var[0].dimensionality:
                    warnings.warn(warn_msg_dim)
                if var2.units != var[0].units:
                    warnings.warn(warn_msg_unit)

                ax[i].set(ylabel=y_label(var[-1], 'prop'))
                sbdim, sbunit = var[-1].prop, '{:~P}'.format(var[-1].units)
                if legend:
                    ax[i].legend(loc=loc, frameon=lf)

            # kwargs necessary so that each subplot
            # gets its own statusbar formatter
            def fmtri(x, y, sbdim=sbdim, sbunit=sbunit):
                return fmtr(x, y, sbdim, sbunit, ax[i])
            ax[i].format_coord = fmtri

    plt.xlabel('$t$ (' + (time if t_str else 'timestamp') + ')');
