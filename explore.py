"""
This module provides the Explorer class, to process and visualize data.

In addition, it provides a handful of functions to manipulate the data
that can be returned by an Explorer object.

"""

import platform
from os.path import split, splitext, basename
from itertools import groupby
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
import re
import warnings
import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from xpint import UnitRegistry
from CoolProp.CoolProp import PropsSI, PhaseSI


class Explorer():
    """
    Process and visualize data from files generated by the DataTaker.

    An Explorer object holds information about data contained in a file
    from the DataTaker (csv or excel). The filename must be passed to
    the constructor. Moreover, an Explorer has several methods to plot
    and/or return the data. The latter can be useful to perform
    calculations that are not implemented in the Explorer class.

    Parameters
    ----------
    filename : str
        The name of the DataTaker file (.csv or .xlsx) to read.

    Attributes
    ----------
    read_file : str
        The name of the DataTaker file that was read by the Explorer.
    """
    
    ureg = UnitRegistry()
    Q_ = ureg.Quantity
    ureg.define('fraction = [] = frac = ratio')
    ureg.define('percent = 1e-2 frac = pct')
    ureg.define('ppm = 1e-6 fraction')

    def __init__(self, filename=None, convert_file=None):
        self.read_file = self.read(filename) # assigns raw_data attribute
        self._build_name_converter(convert_file) # assigns _name_converter attribute
        self.quantities = {}
        # Define 'adimensional units' for humidity

    def _build_name_converter(self, filename='name_conversions.txt'):
        """
        Create a DataFrame to get the actual columns names
        in the DataTaker file.

        Parameters
        ----------
        filename : str, default 'name_conversions.txt'
            The name of the DataTaker file.

        """

        # Read the label conversion table differently according to the OS
        if platform.system() == 'Linux':
            nconv = pd.read_fwf(filename, comment='#',
                                widths=[12, 36, 20, 20, 5], index_col=0)
        else:
            nconv = pd.read_csv(filename, delimiter='\t+',
                                index_col=0, engine='python', comment='#')
            nconv_cols = nconv.loc[:, 'col_names'].str.replace('Â', '');
            nconv_units = nconv.loc[:, 'units'].str.replace('Â', '');
            nconv.loc[:, 'col_names'] = nconv_cols
            nconv.loc[:, 'units'] = nconv_units

        nconv[nconv=='-'] = None
        self._name_converter = nconv

    def read(self, filename=None, initialdir='./heating-data'):
        """
        Read a DataTaker file and assign it to the raw_data attribute.

        Paramters
        ---------
        filename : str, optional
            The name of the file to read. If None is given, a dialog box
            will open to select the file. Valid extensions are csv
            (.csv) and excel (.xslx).
        initialdir : str, default './Heating data'
            a string with the path of the directory in which the dialog
            box will open if no filename is specified.

        """

        if filename is None:
            Tk().withdraw()  # remove tk window
            # Open dialog window in initialdir
            filetypes=(('All files', '.*'),
                       ('CSV', '.csv'),
                       ('Excel', '.xlsx')
                      )
            filename = askopenfilename(initialdir=initialdir,
                                       title='Select input file',
                                       filetypes=filetypes)
        # Return if the Cancel button is pressed
        if filename in ((), ''):
            return None if not get_time else None, None

        # Get the file type from the extension
        _, ext = splitext(filename)
        if ext.lower() == '.csv':
            filetype = 'csv'
        elif ext.lower() == '.xlsx':
            filetype = 'excel'
        else:
            raise ValueError('invalid file extension')

        # Define the reader function according to the file type
        call = 'read_' + filetype
        # Read the first line of the file
        raw_data = getattr(pd, call)(filename, nrows=0)
        # Fetch the data
        if any( word in list(raw_data)[0] for word in
               ['load', 'aux', 'setpoint', '|', 'PdT'] ):

            # Print the test conditions
            print('Test conditions :', list(raw_data)[0])

            # Skip the first row containing the conditions
            self.raw_data = getattr(pd, call)(filename, skiprows=1)

        else:
            self.raw_data = getattr(pd, call)(filename)

        return basename(filename)

    def _build_quantities(self, *quantities, update=True):
        """
        Add quantities to the Explorator's quantities attribute,
        optionally returning them as Quantity objects.

        Parameters
        ----------
        *quantities : {'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8',
                       'T9','Ts', 'Tr', 'Tin', 'Tout', 'Tamb', 'Tdtk',
                       'RHout','Tout_db', 'pin', 'pout', 'flowrt_r',
                       'refdir', 'Pa', 'Pb', 'Pfan_out', 'f', 'Pfan_in',
                       'Ptot', Qcond, Qev, Pcomp}
        update : boolean, default True
            If set to False, quantities already present will not be
            replaced.

        Example
        -------
        >>> e = exp.Explorer()
        >>> quantities = ('T1', 'T2', 'T3')
        >>> T1, T2, T3 = e._build_quantities(*quantities, update=False)

        """

        nconv = self._name_converter
        stored_quantities = self.quantities.keys() if not update else {}
        quantities = set(quantities) - set(stored_quantities)
        # quantities are divided into 3 categories:
        #   those whose magnitude require a bit of cleaning,
        #   those depending upon other quantities to be computed,
        #   and those that can be taken 'as is'.
        to_clean = quantities.intersection({'f', 'flowrt_r'})
        dependant = quantities.intersection({'Qcond', 'Qev', 'Pcomp', 'Pel'})
        as_is = quantities - to_clean - dependant
        
        if not update and 'flowrt_r' in to_clean and to_clean:
            # Since update is False, flowrt_r is not in self.quantities
            self._build_quantities('flowrt_r', update=True)
        elif to_clean:
            f = self.raw_data[nconv.loc['f', 'col_names']].values
            f[f == 'UnderRange'] = 0
            f = f.astype(float) / 2 # actual compressor frequency
            if 'f' in to_clean:
                self.quantities['f'] = self.Q_(
                    f,
                    label=nconv.loc['f', 'labels'],
                    prop=nconv.loc['f', 'properties'],
                    units=nconv.loc['f', 'units']
                )
            if 'flowrt_r' in to_clean:
                flowrt_r = self.raw_data[
                    nconv.loc['flowrt_r', 'col_names']
                ].values
                flowrt_r[f == 0] = 0
                self.quantities['flowrt_r'] = self.Q_(
                    flowrt_r,
                    label=nconv.loc['flowrt_r', 'labels'],
                    prop=nconv.loc['flowrt_r', 'properties'],
                    units=nconv.loc['flowrt_r', 'units']
                )

        for quantity in dependant - {'Pel'}:
            # First get the adequate refrigerant states
            # according to the quantity to build
            ref_states = {
                'Qcond':'pout T4 pout T6',
                'Qev':'pout T6 pin T1',
                'Pcomp':'pin T1 pout T2',
            }[quantity]
            heat_params = self.get('flowrt_r ' + ref_states)
            pow_kW = self._heat(quantity, *heat_params).to('kW')
            self.quantities[quantity] = pow_kW

        if 'Pel' in dependant:
            Pel = np.add(*self.get('Pa Pb'))
            self.quantities['Pel'] = self.Q_(Pel.magnitude,
                                             label='$P_{el}$',
                                             prop='electrical power',
                                             units=Pel.units).to('kW')

        for quantity in as_is:
            magnitude = self.raw_data[nconv.loc[quantity, 'col_names']].values
            self.quantities[quantity] = self.Q_(magnitude,
                label=nconv.loc[quantity, 'labels'],
                prop=nconv.loc[quantity, 'properties'],
                units=nconv.loc[quantity, 'units']
            )

    def get(self, quantities):
        """
        Return specific quantities from an Explorer as Quantity objects.

        All the specified quantities that are not yet in the Explorer's
        quantites are added, then all the specified quantities are
        returned in the form of Quantity objects.

        Parameters
        ----------
        quantities : str with a combination of the following items,
                     separated by spaces
                     {T1 T2 T3 T4 T5 T6 T7 T8 T9 Ts Tr Tin Tout Tamb Tdtk
                      f RHout Tout_db pin pout flowrt_r refdir Pa Pb
                      Pfan_out Pfan_in Ptot Qcond Qev Pcomp}

        Returns
        -------
        xpint Quantity or iterable of xpint Quantity objects

        Examples
        --------
        >>> e = exp.Eplorer()
        >>> T4, pout = e.get('T4', 'pout')

        >>> properties = ('T1 T2 T3 T4 T5 T6 T7')
        >>> T1, T2, T3, T4, T5, T6, T7 = e.get(properties)

        """
        
        quantities = quantities.split()
        # Only build quantities not already in the Explorer's quantities
        self._build_quantities(*(set(quantities) - set(self.quantities)))
        # Return a Quantity if there is only one element in quantities
        if len(quantities) > 1:
            return (self.quantities[quantity] for quantity in quantities)
        else:
            return self.quantities[quantities[0]]

    def plot(self, quantities='all', timestamp=False, **kwargs):
        """
        Plot Explorer's quantities against time.

        If no quantities are given, all the Quantity objects in the
        Explorer's attribute `quantities` are plotted. Each quantity
        having an identical dimensionality is plotted in the same axis.

        Parameters
        ----------
        quantities : {'all', 'allsplit', 'allmerge'} or str
            All the quantities to be plotted, separated by a space.
            Quantites to be plotted together must be grouped inside (),
            [] or {}.
        **kwargs : see function explore.plot.

        Example
        -------
        >>> e = exp.Explorer()
        >>> e.plot('(T1 T2) f')

        """

        args = [] # parameters to pass to plot function
        quantities = 'allmerge' if quantities == 'all' else quantities
        
        # Define an iterator and an appender to add the right quantities
        # to the args list
        if quantities == 'allsplit':
            iterator = self.quantities.keys()
            appender = lambda arg: self.get(arg)
        elif quantities == 'allmerge':
            def gen():
                # Group quantities by property
                key = lambda q: self.quantities[q].prop
                for _, prop in groupby(sorted(self.quantities, key=key), key):
                    # Yield a list in any case, the appender will take
                    # care of the cases with only one element
                    yield [self.quantities[q] for q in prop]
            iterator = gen()
            appender = lambda arg: arg[0] if len(arg) == 1 else arg
        elif any(delim in quantities for delim in ('(', '[', '{')):
            # Split but keep grouped quantities together
            regex_pattern = re.split(r'[()|\[\]|\{\}]', quantities)
            iterator = (arg.strip() for arg in regex_pattern if arg.strip())
            def appender(arg):
                if ' ' in arg:
                    return list(self.get(arg))
                else:
                    return self.get(arg)
        else:
            iterator = quantities.split()
            appender = lambda arg: self.get(arg)

        for arg in iterator:
            args.append(appender(arg))
        
        if timestamp:
            # Take a minute resolution
            as_rounded_timestamp = lambda t: pd.Timestamp(t).round('min')
            t = self.raw_data['Timestamp'].apply(as_rounded_timestamp)
            kwargs['time'] = t
        
        plot(*args, **kwargs)
    
    @ureg.wraps(None, (None, None, ureg.kilogram/ureg.second,
                       ureg.pascal, ureg.kelvin, ureg.pascal, ureg.kelvin)) 
    def _heat(self, power, flow=None,
              pin=None, Tin=None, pout=None, Tout=None):
        """
        Compute heat transfer rate from thermodynamic quantities.

        All provided quantities must be (x)pint Quantity objects, with a
        magnitude of the same length.

        Parameters
        ----------
        power : {'Qcond', 'Qev', 'Pcomp'}
            Property to be evaluated.
        flow : Quantity
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
        Quantity
            Mass flow rate multiplied by the enthalpy difference,
            i.e. the heat transfer rate in watts.

        """
        
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
                                       'Pel':(None, None)}[power]
        # Get quality based on expected phase
        quality = {'liquid':0, 'gas':1, None:None}

        # Replace by saturated state enthalpy if not in the right phase
        hin[phase_in != exp_phase_in] = PropsSI(
            'H', 'P', pin[phase_in != exp_phase_in],
            'Q', quality[exp_phase_in], 'R410a'
        )
        hout[phase_out != exp_phase_out] = PropsSI(
            'H', 'P', pout[phase_out != exp_phase_out],
            'Q', quality[exp_phase_out], 'R410a'
        )
        
        # Get the right attributes depending on the input property
        label={'Qcond':'$\dot{Q}_{cond}$',
               'Qev':'$\dot{Q}_{ev}$',
               'Pcomp':'$P_{comp}$',
               }[power]
        prop = 'mechanical power' if power == 'Pcomp' else 'heat transfer rate'
        
        # Return result in watts
        return self.Q_(flow * (hout - hin) * (-1 if power == 'Qcond' else 1),
                       label=label, units='W', prop=prop
                 )
    

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
                ax[i].plot(t, var[interval])
                ax[i].set(ylabel=y_label(var, 'label'))
                sbdim, sbunit = var.prop, '{:~P}'.format(var.units)
            else:
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
