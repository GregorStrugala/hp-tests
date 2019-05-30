import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
from math import sqrt, floor
from os.path import split

from explore import Explorer

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

def plot_files(var, initialdir='./heating-data', paths=None, filetype=None):
    """
    Plot a single variable from several DataTaker files.

    Parameters
    ----------
    var : {'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'Ts',
           'Tr', 'Tin', 'Tout', 'Tamb', 'Tdtk', 'RHout', 'Tout_db', 'f',
           'pin', 'pout', 'flowrt_r', 'refDir', 'Pa', 'Pb',
           'Ptot', 'Pfan_out', 'Pfan_in',  'Qev', 'Qcond',
           'Pcomp', 'Pel'}
        The quantity that will be plotted.
    initialdir : str, default './Heating data'
        The path of the directory in which data files are located. When
        no `filename` is given, a dialog box opens at the location
        provided by `initialdir`.
    paths : iterable of str or 'all', optional
        An iterable with the paths used for plotting. When set to
        'all', every file in initialdir is selected. If None is given, a
        dialog box will ask to select the files.
    filetype : str, optional
        Extension of files to use for plotting (csv or excel). If not
        specified, files with both extension are used. Useful when
        `paths` is either 'all' or None.
    return_data : bool, default False
        If set to True, the function will return a DataFrame with the
        plotted data.

    Returns
    -------
    df : DataFrame or None
        A pandas DataFrame object with the values of the speicified
        variable (one colmun for each file). None is returned if
        `return_data` is False.

    """
    
    # If no paths are specified, ask with dialog box
    if paths is None:
        # Display default files based on the specified filetype
        if filetype is None:
            filetypes = (('All files', '.*'), ('CSV', '.csv'),
                         ('Excel', '.xlsx'))
        elif filetype.lower() in ('csv', '.csv'):
            filetypes = (('CSV', '.csv'), ('All files', '.*'))
        elif filetype.lower() in ('excel', 'xlsx', '.xlsx'):
            filetypes = (('Excel', '.xlsx'), ('All files', '.*'))

        title = 'Select input files'
        Tk().withdraw()  # remove tk window
        paths = askopenfilenames(initialdir=initialdir,
                                     title=title, filetypes=filetypes)
        if paths in ((), ''):  # Cancel button has been pressed
            return

    elif paths == 'all':  # take every file in initialdir
        paths = listdir(initialdir)
        # Use full path
        paths = [initialdir + '/' + filename for filename in paths]

    dfs=[]  # list to put the dataframes of each file
    for path in paths:
        exp = Explorer(filename=path)
        quantity = exp.get(var)
        _, filename = split(path)  # get filename without the path
        dfs.append(pd.DataFrame(quantity.magnitude,
                                columns=[var]).rename(columns={var:filename}))
    df = pd.concat(dfs, axis=1)  # merge all dataframes into one

    # Create the subplots layout
    nplots = len(df.columns)
    ncols = floor(sqrt(nplots))
    nrows = nplots // ncols + (nplots % ncols != 0)
    axs = df.plot(subplots=True, layout=(nrows, ncols), fontsize=8,
                  title=list(df.columns.values), sharex=False, legend=False)

    # Resize the subplot titles and adjust the x-axis limits
    for ax, df in zip(axs.reshape(-1), dfs):
        ax.title.set_size(8)
        ax.set_xlim([0, df.last_valid_index()])
    # Display a title in the figure
    plt.suptitle(var)
