"""
This module provides a handful of functions for processing and plotting
data from the DataTaker files.
It contains the following functions, each with their own documentation:

    explore     Plot and/or read the data from a file. This is basically
                a combination of the functions `read`, `get` and `plot`.
    read        Read the data from the file into a DataFrame.
    get         Extract specific variables from a DataFrame
                into Quantity objects.
    plot        (Sub)plot one or several Quantity objects.
    thermo_cal  Compute heat transfer from flowrate, pressure and
                temperatures.
    plot_files  Plot a quantity for several files to allow comparison.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as dtm, timedelta as tdl
from CoolProp.CoolProp import PropsSI, PhaseSI
import platform  # detect OS
import warnings
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
from os import listdir
from math import floor, sqrt
from os.path import split, splitext

from xpint import UnitRegistry
ureg = UnitRegistry()
ureg.define('fraction = [] = frac = ratio')
ureg.define('percent = 1e-2 frac = pct')
ureg.define('ppm = 1e-6 fraction')

Q_ = ureg.Quantity

def read(filename=None, get_time=False, initialdir='./heating-data'):
    """
    Read a DataTaker file.

    Paramters
    ---------
    filename : str, optional
        The name of the file to read. If None is given, a dialog box
        will open to select the file. Valid extensions are csv (.csv)
        and excel (.xslx).
    get_time : bool, default False
        a vector with datetime objects is also returned if set to True.
    initialdir : str, default './Heating data'
        a string with the path of the directory in which the dialog box
        will open if no filename is specified.

    Returns
    -------
    raw_data : DataFrame
        A pandas DataFrame containing the data in the specified file.
    t : pandas.Series
        A pandas Series with Timestamps objects corresponding to the
        Timestamp column of the DataTaker file, rounded to the minute.

    """

    if filename is None:
        Tk().withdraw()  # remove tk window

        # Open dialog window in initialdir
        filetypes=(('All files', '.*'), ('CSV', '.csv'), ('Excel', '.xlsx'))
        filename = askopenfilename(initialdir=initialdir,
                                   title='Select input file',
                                   filetypes=filetypes)
    
    if filename in ((), ''):  # Cancel button pressed
        return None if not get_time else None, None

    _, ext = splitext(filename)  # get the file extension

    if ext.lower() == '.csv':
        fileType = 'csv'
    elif ext.lower() == '.xlsx':
        fileType = 'excel'
    else:
        raise ValueError('invalid file extension')

    # Name of the function that will read the file
    call = 'read_' + fileType

    # Read the first line of the .csv (or .xlsx) file
    raw_data = getattr(pd, call)(filename,nrows=0)

    # Display all columns in jupyter
    pd.set_option('display.max_columns', 100)

    if any( word in list(raw_data)[0] for word in
           ['load', 'aux', 'setpoint', '|', 'PdT'] ):
        # Print the test conditions
        print(list(raw_data)[0])

        # Skip the first row containing the conditions
        raw_data = getattr(pd, call)(filename, skiprows=1)

    else:
        raw_data = getattr(pd, call)(filename)

    if get_time:
        # Take a minute resolution
        t = raw_data['Timestamp'].apply(lambda t: pd.Timestamp(t).round('min'))
        return raw_data, t
    else:
        return raw_data

def get(raw_data, *args):
    """
    Create a list of xpint arrays to be used in plot function.

    All the variables given in the arguments as strings are extracted
    from raw_data. For conciseness sake, the variable names are kept
    short and thus an external file (name_conversions) associates them
    with those used in the dataker file. The file also provides the
    adequate Quantity parameters for each variable (units, label...).

    Parameters
    ----------
    raw_data : DataFrame
        A pandas DataFrame containing the raw data.
    *args : {'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'Ts',
             'Tr', 'Tin', 'Tout', 'Tamb', 'Tdt','RHout','TwbOut', 'pIn',
             'pOut', 'mDotRef', 'refDir', 'PowerA', 'PowerB',
             'PowerFanOut', 'f', 'PowerFanIn', 'PowerTot'}

    Returns
    -------
    xpint Quantity or iterable of xpint Quantitiy objects

    Examples
    --------
    >>> raw_data = read()
    >>> T4, pOut = get(raw_data, 'T4', 'pOut')

    >>> properties = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8')
    >>> T1, T2, T3, T4, T5, T6, T7, T8 = get(raw_data, *properties)

    """

    # Read the name converter differently according to the OS
    if platform.system() == 'Linux':
        nconv = pd.read_fwf('name_conversions', comment='#',
                            widths=[12, 36, 20, 20, 5], index_col=0)
    else:
        nconv = pd.read_csv('name_conversions.txt', delimiter='\t+',
                        index_col=0, engine='python', comment='#')
        nconv.loc[:,'col_names'] = nconv.loc[:,'col_names'].str.replace('Â','');
        nconv.loc[:,'units'] = nconv.loc[:,'units'].str.replace('Â','');

    nconv[nconv=='-'] = None
    out = ( Q_(np.array(raw_data[nconv.loc[var, 'col_names']]),
               label=nconv.loc[var, 'labels'],
               prop=nconv.loc[var, 'properties'],
               units=nconv.loc[var, 'units']) for var in args
          )

    return out if len(args) > 1 else next(out)

def plot(*args, time='min', step=60, interval=slice(0, None), sharex='col',
         legend=True, lf=True, loc='best'):
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
    Plot only one varaible (say Tr):

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

    # Store this boolean as it is used numerous times
    t_str = isinstance(time, str)

    a0_list = isinstance(args[0], list)
    length = len(args[0][0][interval] if a0_list else args[0][interval])
    t = np.arange(0, length) / res[time] if t_str else time[interval]

    # warning messages
    warn_msg_dim = ('Quantities with different dimensionalities'
                    'are displayed on the same plot')
    warn_msg_unit = ('Quantities with different units'
                     'are displayed on the same plot')

    # Create statusbar
    statusbar = {True:'time: {:.2f} {}     {}: {:.2f} {}',
                 False:'time: {}     {}: {:.2f} {}'}[t_str]

    # Create the figure and axis
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

            return statusbar.format(datefmt(ax)(x), time, sbdim, y, sbunit)


    if len(args) == 1:  # only one axis (that may have several plots)

        if not isinstance(args[0], list):  # only one plot
            ax.plot(t, args[0][interval])
            ax.set(ylabel=y_label(args[0], 'label'))

            # label (or property) and units used in status bar
            sbdim, sbunit = args[0].prop, '{:~P}'.format(args[0].units)

        else:  # several plots
            for var in args[0]:
                ax.plot(t, var[interval], label=var.label)

                if var.dimensionality != args[0][0].dimensionality:
                    warnings.warn(warn_msg_dim)

                if var.units != args[0][0].units:
                    warnings.warn(warn_msg_unit)

            # Set y-label from the last element
            ax.set(ylabel=y_label(args[0][-1], 'prop'))

            sbdim, sbunit = args[0][-1].prop, '{:~P}'.format(args[0][-1].units)

            if legend:
                ax.legend(loc=loc, frameon=lf)

        ax.format_coord = lambda x, y: fmtr(x, y, sbdim, sbunit, ax)

    else:  # several subplots
        for i, var in enumerate(args):

            # Only one variable to be plotted in current subplot
            if not isinstance(var, list):
                ax[i].plot(t, var[interval])
                ax[i].set(ylabel=y_label(var, 'label'))
                sbdim, sbunit = var.prop, '{:~P}'.format(var.units)
            else:  # several variables to be plotted in current subplot
                for var2 in var:
                    ax[i].plot(t, var2[interval], label=var2.label)

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

def thermo_cal(prop, flowrate=None, pin=None, Tin=None, pout=None,
               Tout=None):
    """
    Compute power (or heat transfer rate) from thermodynamic quantities.

    All provided quantities must be (x)pint Quantity objects,
    `array_like` quantities must be the same length.

    Parameters
    ----------
    prop : {'Qcond', 'Qev', 'Pcomp'}
        Property to be evaluated.
    flowrate : Quantity
        The mass flow rate of the fluid exchanging heat or work.
    pin : Quantity
        Inlet fluid pressure.
    Tin : Quantity
        Inlet fluid temperature.
    pout : Quantity
        Outlet fluid pressure.
    Tout : Quantity
        Outlet fluid temperature.

    Returns
    -------
    out : Quantity
        Mass flow rate multiplied by the enthalpy difference.

    """

    pin = pin.to('Pa').magnitude
    Tin = Tin.to('K').magnitude
    pout = pout.to('Pa').magnitude
    Tout = Tout.to('K').magnitude

    # Get the enthalpies using CoolProp, in J/kg
    hin = PropsSI('H', 'P', pin, 'T', Tin, 'R410a')
    hout = PropsSI('H', 'P', pout, 'T', Tout, 'R410a')

    # Check the phase, because points in and out may be
    # on the wrong side of the saturation curve
    phase_in = np.array([PhaseSI('P', p, 'T', T, 'R410a')
                         for p, T in zip(pin, Tin)])
    phase_out = np.array([PhaseSI('P', p, 'T', T, 'R410a')
                          for p, T in zip(pout, Tout)])

    # Assign the expected phases based on the specified property
    exp_phase_in, exp_phase_out = {'Qcond':('gas', 'liquid'),
                                   'Qev':('liquid', 'gas'),
                                   'Pcomp':('gas', 'gas'),
                                   'Pel':(None, None)}[prop]
    # Get quality based on expected phase
    quality = {'liquid':0, 'gas':1, None:None}

     # Replace by saturated state enthalpy if not in the right phase
    hin[phase_in != exp_phase_in] = PropsSI(
        'H', 'P', pin[phase_in != exp_phase_in],
        'Q', quality[exp_phase_in], 'R410a')
    hout[phase_out != exp_phase_out] = PropsSI(
        'H', 'P', pout[phase_out != exp_phase_out],
        'Q', quality[exp_phase_out], 'R410a')

    # Get the right attributes depending on the input property
    label={'Qcond':'$\dot{Q}_{cond}$',
            'Qev':'$\dot{Q}_{ev}$',
            'Pcomp':'$\dot{P}_{comp}$'
           }[prop]
    p_type = 'mechanical power' if prop == 'Pcomp' else 'heat transfer rate'
    flowdir = -1 if prop == 'Qcond' else 1
    # Return result in watts
    return Q_(flowrate.to('kg/s').magnitude * (hout - hin) * flowdir,
              label=label, units='W', prop=p_type
             )


def explore(*args, plot_data=True, return_data=False,
            filename=None, **kwargs):
    """
    Plot quantities and extract data from DataTaker files.

    The specified quantities are read from a csv or excel file, plotted
    and/or returned as xpint quantities. Quantities with the same
    dimensionality are plotted in the same axis.

    Parameters
    ----------
    *args : {'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'Ts',
             'Tr', 'Tin', 'Tout', 'Tamb', 'Tdt', 'pIn', 'pOut','RHout',
             'TwbOut', 'mDotRef', 'refDir', 'PowerA', 'PowerB',
             'PowerFanOut', 'f', 'PowerFanIn', 'PowerTot', 'Qev',
             'Qcond', 'Pcomp', 'Pel'}
        Quantities to be plotted and/or returned as xpint arrays.
    plot_data : bool, default True
        The quantities are not plotted if set to False.
    return_data : bool, default False
        The raw data and the specified quantities given as arguments are
        returned if set to True.
    filename : str, optional
        The name of the file to read. A dialog box asks for file if None
        is specified.
    **kwargs
        Additional arguments passed to the plot function.
        See plot for more details.

    Returns
    -------
    xpint quantity or list of xpint quantities

    Examples
    --------
    >>> explore('Tr', 'Ts', 'f', 'Qcond')

    >>> Tr, Ts = explore('Tr', 'Ts', return_data=True, lf=False)

    """

    # Disable Unit_strippedWarning warnings
    warnings.simplefilter('ignore')

    raw_data = read(filename)

    # Return if Cancel button was pressed in dialog window
    if raw_data is None:
        return

    # Remove those arguments that are not in the DataTaker file
    measurements = list(np.setdiff1d(args, ['Qcond', 'Qev', 'Pcomp', 'Pel'],
                                     assume_unique=True))
    data = get(raw_data, *measurements) if measurements else ()

    # plotvar must be a list of pint Quantities
    plotvar = [data] if len(measurements) == 1 else list(data)

    # Function to avoid code duplication
    def get_var(qt):
        """Do not read a quantity if it is already in measurements."""
        if qt in measurements:
            return plotvar[measurements.index(qt)]
        else:
            return get(raw_data, qt)

    if 'f' in args:
        plotvar[measurements.index('f')] = get_var('f').clean()

    if any([qt in args for qt in ('mDotRef', 'Qcond', 'Qev', 'Pcomp')]):
        f = get_var('f').clean()
        flowrt_r = get_var('mDotRef')

        # Impose a zero flow rate whenever f is zero
        flowrt_r[f == 0] = Q_(0, flowrt_r.units)

        if 'mDotRef' in args:
            plotvar[measurements.index('mDotRef')] = flowrt_r

        if any([qt in args for qt in ('Qcond', 'Qev', 'Pcomp')]):
            pOut = get_var('pOut')
            if any([qt in args for qt in ('Qev', 'Pcomp')]):
                pIn = get_var('pIn')


    if 'Qcond' in args:
        # Get necessary quantities in SI units
        T4 = get_var('T4')
        T6 = get_var('T6')
        p4 = pOut.to('Pa')
        p6 = pOut.to('Pa')

        Qcond = thermo_cal('Qcond', flowrt_r, p4, T4, p6, T6).to('kW')

        # Add to the plotted variables list
        # while keeping the previous position
        plotvar.insert(args.index('Qcond'), Qcond)


    if 'Qev' in args:
        # Get necessary quantities in SI units
        T1 = get_var('T1')
        T6 = get_var('T6')
        p1 = pIn.to('Pa')
        p6 = pOut.to('Pa')

        Qev = thermo_cal('Qev', flowrt_r, p6, T6, p1, T1).to('kW')

        # Add to the plotted variables list
        # while keeping the previous position
        plotvar.insert(args.index('Qev'), Qev)


    if 'Pcomp' in args:
        # Get necessary quantities in SI units
        T1 = get_var('T1')
        T2 = get_var('T6')
        p1 = pIn.to('Pa')
        p2 = pOut.to('Pa')

        Pcomp = thermo_cal('Pcomp', flowrt_r, p1, T1, p2, T2).to('kW')

        # Add to the plotted variables list
        # while keeping the previous position
        plotvar.insert(args.index('Pcomp'), Pcomp)


    if 'Pel' in args:
        # Get necessary quantities in kW
        Pa = get_var('PowerA').to('kW')
        Pb = get_var('PowerB').to('kW')

        # Compute the compressor's electrical consumption
        Pel = Pa + Pb
        Pel.name('electrical power', '$P_{el}$')

        # Add to the plotted variables list
        # while keeping the previous position
        plotvar.insert(args.index('Pel'), Pel)

    if plot_data:
        if len(args) > 1:
            # Group plotted variables based on their dimensionality
            groups = {}
            for var in plotvar:
                groups.setdefault(var.dimensionality, []).append(var)

            groups = list(groups.values())

            # Un-nest 1-element lists (that are too nested)
            for i, group in enumerate(groups):
                if len(group) == 1:
                    groups[i] = group[0]
            plot(*groups, **kwargs)
        else:
            plot(*plotvar, **kwargs)

    if return_data:
        return plotvar if len(args) > 1 else plotvar[0]


def plot_files(var, initialdir='./Heating data', filenames=None,
               filetype=None, return_data=False):
    """
    Plot a single variable from several DataTaker files.

    Parameters
    ----------
    var : {'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'Ts',
           'Tr', 'Tin', 'Tout', 'Tamb', 'Tdt', 'RHout', 'TwbOut', 'f',
           'pIn', 'pOut', 'mDotRef', 'refDir', 'PowerA', 'PowerB',
           'PowerTot', 'PowerFanOut', 'PowerFanIn',  'Qev', 'Qcond',
           'Pcomp', 'Pel'}
        The quantity that will be plotted.
    initialdir : str, default './Heating data'
        The path of the directory in which data files are located. When
        no `filename` is given, a dialog box opens at the location
        provided by `initialdir`.
    filenames : iterable of str or 'all', optional
        An iterable with the filenames used for plotting. When set to
        'all', every file in initialdir is selected. If None is given, a
        dialog box will ask to select the files.
    filetype : str, optional
        Extension of files to use for plotting (csv or excel). If not
        specified, files with both extension are used. Useful when
        `filenames` is either 'all' or None.
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

    # Read the label conversion table differently according to the OS
    if platform.system() == 'Linux':
        nconv = pd.read_fwf('name_conversions', comment='#',
                            widths=[12, 36, 20, 20, 5], index_col=0)
    else:
        nconv = pd.read_csv('name_conversions.txt', delimiter='\t+',
                        index_col=0, engine='python', comment='#')
        nconv.loc[:,'col_names'] = nconv.loc[:,'col_names'].str.replace('Â','');
        nconv.loc[:,'units'] = nconv.loc[:,'units'].str.replace('Â','');

    nconv[nconv=='-'] = None

    # If no filenames are specified, ask with dialog box
    if filenames is None:

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
        filenames = askopenfilenames(initialdir=initialdir,
                                     title=title, filetypes=filetypes)

        if filenames in ((), ''):  # Cancel button has been pressed
            return

    elif filenames == 'all':  # take every file in initialdir
        filenames = listdir(initialdir)

        # Use full path
        filenames = [initialdir + '/' + filename for filename in filenames]

    dfs=[]  # list to put the dataframes of each file

    def read_file(file, **kwargs):

        # Append if filetype is None or excel,
        # and the current file is an excel file
        if (str(filetype).lower() in ('none', 'excel', 'xlsx', '.xlsx') and
            file.lower().endswith('.xlsx')):
            return pd.read_excel(file, **kwargs)

        # Append if filetype is None or csv,
        # and the current file is a csv file
        elif (str(filetype).lower() in ('none', 'csv', '.csv') and
              file.lower().endswith('.csv')):
            return pd.read_csv(file, **kwargs)


    for file in filenames:

        _, filename = split(file)  # get filename without the path

        if var in ('f', 'mDotRef'):

            col_names = list(nconv.loc[('f', 'mDotRef'), 'col_names'])
            df = read_file(file, usecols=col_names)
            f, flowrt_r = get(df, 'f', 'mDotRef')

            if var == 'f':
                dfs.append(
                    pd.DataFrame(f.clean().magnitude, columns=[var]
                                ).rename(columns={var:filename})
                )

            else:
                flowrt_r[f.clean() == 0] = Q_(0, flowrt_r.units)
                dfs.append(
                    pd.DataFrame(flowrt_r.magnitude, columns=[var]
                                ).rename(columns={var:filename})
                )

        elif var in ('Qcond', 'Qev', 'Pcomp'):

            # Fetch quantities needed to compute the given variable
            tci = {
                'Qcond':('pOut', 'T4', 'pOut', 'T6'),
                'Qev':('pOut', 'T6', 'pIn', 'T1'),
                'Pcomp':('pIn', 'T1', 'pOut', 'T2'),
            }[var]

            rd = lambda t: tuple(set(t))  # remove duplicates from tuple

            # Get a list of column names as written by the DataTaker
            col_names = list(nconv.loc[('f', 'mDotRef') + rd(tci), 'col_names'])

            # Use it to read the appropriate columns
            prop_req = read_file(file, usecols=col_names)

            f, flowrt_r = get(prop_req, 'f', 'mDotRef')
            f = f.magnitude
            flowrt_r[(f == 0) | (f == 'UnderRange')] = Q_(0, flowrt_r.units)

            # Give the right inputs to thermo_cal based on var
            get_inputs = {
                'Qcond':{'Tin':'T4', 'Tout':'T6',
                         'p_in':'pOut', 'p_out':'pOut'},
                'Qev':{'Tin':'T6', 'Tout':'T1',
                       'p_in':'pOut', 'p_out':'pIn'},
                'Pcomp':{'Tin':'T1', 'Tout':'T2',
                         'p_in':'pIn', 'p_out':'pOut'}
            }[var]

            # thermo_cal input names
            tc_inputs = ('p_in', 'Tin', 'p_out', 'Tout')

            # Get all the required properties as Quantity objects
            pr = get(prop_req, 'mDotRef', *[get_inputs[i] for i in tc_inputs])

            dfs.append(
                pd.DataFrame(
                    thermo_cal(var, *pr).to('kW').magnitude, columns=[var]
                ).rename(columns={var:filename})
            )

        elif var == 'Pel':
            col_names = list(nconv.loc[('PowerA', 'PowerB'), 'col_names'])
            phase_power = read_file(file, usecols=col_names)
            Pa, Pb = get(phase_power, 'PowerA', 'PowerB')
            dfs.append(
                pd.DataFrame(
                    (Pa + Pb).to('kW').magnitude
                            ).rename(columns={0:filename})
            )

        else:
            col = nconv.loc[var, 'col_names']
            dfs.append(
                read_file(file, usecols=[col]).rename(columns={col:filename})
            )

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

    if return_data:
        return df
