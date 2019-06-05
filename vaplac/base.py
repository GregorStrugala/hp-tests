"""
This module provides the DataTaker class,
to process, validate and visualize data.

"""

import platform
from os.path import splitext, basename
from itertools import groupby
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
import re
import warnings
import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
from math import floor, sqrt

from CoolProp.CoolProp import PropsSI, PhaseSI
from CoolProp.HumidAirProp import HAPropsSI as psychro
from cerberus import Validator

from ._plot import plot
from xpint import UnitRegistry
from vaplac import sauroneye

class DataTaker():
    """
    Process and visualize data from files generated by a data logger.

    A DataTaker object holds information about data contained in a file
    from a data logger (CSV or excel). The filename must be passed to
    the constructor. Moreover, a DataTaker has methods to validate
    or return the data. The latter can be useful to perform
    calculations that are not implemented in the DataTaker class.

    Because column names in data files may be quite long, it becomes
    tedious if the user has to type them numerous times.
    A DataTaker object thus links those names to alternate, shorter ones
    based on an external file that can be specified (default is
    `name_conversions_UTF8.txt` on unix-based systems, and
    `name_conversions_ANSI.txt` on windows sysems). This file also
    gives the units and property for each measured quantity.

    Parameters
    ----------
    filename : str
        The name of the DataTaker file (.csv or .xlsx) to read.

    Attributes
    ----------
    read_file : str
        The name of the data file that was read by the DataTaker.
    """

    ureg = UnitRegistry()
    Q_ = ureg.Quantity
    ureg.define('fraction = [] = frac = ratio')
    ureg.define('percent = 1e-2 frac = pct')
    ureg.define('ppm = 1e-6 fraction')

    def __init__(self, filename=None, initialdir='heating-data',
                 convert_file='name_conversions_UTF8.txt'):
        # assign read_file and raw_data attribute
        self.read_file = self.read(filename, initialdir=initialdir)
        # assign _name_converter attribute
        if platform.system() == 'Windows':
            convert_file = 'name_conversions_ANSI.txt'
        self._build_name_converter(convert_file)
        self.quantities = {}

    def _build_name_converter(self, filename):
        """
        Create a DataFrame to get the actual columns names
        in the DataTaker file.

        Parameters
        ----------
        filename : str, default 'name_conversions_UTF8.txt'
            The name of the DataTaker file.

        """

        # Read the label conversion table differently according to the OS
        nconv = pd.read_fwf(filename, comment='#',
                            widths=[12, 36, 20, 20, 5], index_col=0)
        nconv[nconv=='-'] = None
        self._name_converter = nconv

    def read(self, filename=None, initialdir='heating-data'):
        """
        Read a data file and assign it to the raw_data attribute.

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
                       ('Excel', '.xlsx'))
            filename = askopenfilename(initialdir=initialdir,
                                       title='Select input file',
                                       filetypes=filetypes)
        # Return if the Cancel button is pressed
        if filename in ((), ''):
            return None

        # Get the file type from the extension
        _, ext = splitext(filename)
        if ext.lower() == '.csv':
            filetype = 'csv'
        elif ext.lower() == '.xlsx':
            filetype = 'excel'
        else:
            raise ValueError('invalid file extension')

        # Check the file encoding:
        with open(filename) as f:
            try:
                next(f)
            except UnicodeDecodeError:
                encoding = 'ISO-8859-1'
            else:
                encoding = 'UTF8'

        # Define the reader function according to the file type
        call = 'read_' + filetype
        # Read the first line
        raw_data = getattr(pd, call)(filename, nrows=0, encoding=encoding)

        # Fetch the data
        if any( word in list(raw_data)[0] for word in
               ['load', 'aux', 'setpoint', '|', 'PdT'] ):

            # Print the test conditions
            print('Test conditions :', list(raw_data)[0])

            # Skip the first row containing the conditions
            self.raw_data = getattr(pd, call)(filename, skiprows=1,
                                              encoding=encoding)
        else:
            self.raw_data = getattr(pd, call)(filename, encoding=encoding)

        return basename(filename)

    def _build_quantities(self, *quantities, update=True):
        """
        Add quantities to the DataTaker's quantities attribute,
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
        >>> dtk = vpa.DataTaker()
        >>> quantities = ('T1', 'T2', 'T3')
        >>> T1, T2, T3 = dtk._build_quantities(*quantities, update=False)

        """

        nconv = self._name_converter
        stored_quantities = self.quantities.keys() if not update else {}
        quantities = set(quantities) - set(stored_quantities)
        # quantities are divided into 4 categories:
        #   humidity ratios,
        #   those whose magnitude require a bit of cleaning,
        #   those depending upon other quantities to be computed,
        #   and those that can be taken 'as is'.
        hum_ratios = quantities.intersection({'ws', 'wr'})
        to_clean = quantities.intersection({'f', 'flowrt_r'})
        dependant = quantities.intersection(
            {'Qcond', 'Qev', 'Pcomp', 'Pel', 'Qloss_ev'})
        as_is = quantities - hum_ratios - to_clean - dependant

        for w in hum_ratios:
            T = self.get('T' + w.strip('w')).to('K').magnitude
            RH = self.get('RH' + w.strip('w')).to('ratio').magnitude
            self.quantities[w] = self.Q_(
                psychro('W', 'P', 101325, 'T', T, 'RH', RH),
                label='$\omega_{' + w.strip('w') + '}$',
                prop='absolute humidity',
                units='ratio'
            ).to('g/kg')

        if not update and 'flowrt_r' in to_clean:
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
            # First get the adequate refrigerant states according to
            # the quantity to build and the refrigerant flow direction.
            ref_dir = self.get('refdir')
            if len(np.nonzero(ref_dir)[0]) < len(ref_dir) / 2:
                ref_states = {
                    'Qcond': 'pout T4 pout T6',
                    'Qev': 'pout T6 pin T9',
                    'Pcomp': 'pin T1 pout T2'
                }[quantity]
            else:
                ref_states = {
                    'Qcond': 'pout T9 pout T7',
                    'Qev': 'pout T7 pin T4',
                    'Pcomp': 'pin T1 pout T2',
                    'Qloss_ev': 'pin T4 pin T1'
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
        Return specific quantities from a DataTaker as Quantity objects.

        All the specified quantities that are not yet in the DataTaker's
        quantities are added, then all the specified quantities are
        returned in the form of Quantity objects.

        Parameters
        ----------
        quantities : str with a combination of the following items,
                     separated by spaces
                     {T1 T2 T3 T4 T5 T6 T7 T8 T9 Ts RHs ws Tr RHr wr Tin
                     Tout Tamb Tdtk f RHout Tout_db refdir flowrt_r pin
                      pout Pa Pb Pfan_out Pfan_in Ptot Qcond Qev Pcomp}

        Returns
        -------
        xpint Quantity or iterable of xpint Quantity objects

        Examples
        --------
        >>> dtk = vpa.DataTaker()
        >>> T4, pout = dtk.get('T4 pout')

        >>> properties = 'T1 T2 T3 T4 T5 T6 T7'
        >>> T1, T2, T3, T4, T5, T6, T7 = dtk.get(properties)

        """

        quantities = quantities.split()
        # Only build quantities not already in the DataTaker's quantities
        self._build_quantities(*(set(quantities) - set(self.quantities)))
        # Return a Quantity if there is only one element in quantities
        if len(quantities) > 1:
            return (self.quantities[quantity] for quantity in quantities)
        else:
            return self.quantities[quantities[0]]

    def plot(self, quantities='all', timestamp=False, **kwargs):
        """
        Plot DataTaker's quantities against time.

        If no quantities are given, all the Quantity objects in the
        DataTaker's attribute `quantities` are plotted. Each quantity
        having an identical dimensionality is plotted in the same axis.

        Parameters
        ----------
        quantities : {'all', 'allsplit', 'allmerge'} or str
            All the quantities to be plotted, separated by a space.
            Quantites to be plotted together must be grouped inside (),
            [] or {}.
        **kwargs : see function vaplac.plot.

        Example
        -------
        >>> dtk = vpa.DataTaker()
        >>> dtk.plot('(T1 T2) f')

        """

        # Store in a list the arguments to pass
        # to the datataker.plot method
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
            iterator = (arg.strip('()')
                        for arg in re.findall('\([^\)]*\)|\S+', quantities))
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
        exp_phase_in, exp_phase_out = {'Qcond': ('gas', 'liq'),
                                       'Qev': ('liq', 'gas'),
                                       'Pcomp': ('gas', 'gas'),
                                       'Qloss_ev': ('gas', 'gas')
                                      }[power]
        # Get quality based on expected phase
        quality = {'liq':0, 'gas':1, None:None}

        # Replace by saturated state enthalpy if not in the right phase
        if not exp_phase_in in phase_in:
            hin[phase_in != exp_phase_in] = PropsSI(
                'H', 'P', pin[phase_in != exp_phase_in],
                'Q', quality[exp_phase_in], 'R410a'
            )
        if not exp_phase_out in phase_out:
            hout[phase_out != exp_phase_out] = PropsSI(
                'H', 'P', pout[phase_out != exp_phase_out],
                'Q', quality[exp_phase_out], 'R410a'
            )

        # Get the right attributes depending on the input property
        label={'Qcond': '$\dot{Q}_{cond}$',
               'Qev': '$\dot{Q}_{ev}$',
               'Pcomp': '$P_{comp}$',
               'Qloss_ev': '$\dot{Q}_{loss,ev}$'
               }[power]
        prop = 'mechanical power' if power == 'Pcomp' else 'heat transfer rate'

        # Return result in watts
        return self.Q_(flow * (hout - hin) * (-1 if power == 'Qcond' else 1),
                       label=label, units='W', prop=prop
                 )

    def validate(self, show_data=False):
        """
        Perform data checks implemented in vaplac.sauroneye.

        If no abnormalities are detected, the message 'No warnings' is
        displayed. Otherwise, the corresponding warnings will be given.

        Parameters
        ----------
        show_data : boolean, default False
            If set to True, the quantities involved in the checks resulting
            in a warning are plotted.

        Example
        -------
        >>> dtk = vpa.DataTaker()
        >>> dtk.validate(show_data=True)

        """
        schema = {check: {'check_with': getattr(sauroneye, check)}
                  for check in dir(sauroneye) if check.endswith('check')}
        v = Validator(schema)
        if v.validate({check: self for check in schema}):
            print('No warnings')
        else:
            n_warn = len(v.errors)
            if n_warn > 1:
                print('There are {} warnings:'.format(n_warn))
                for i, warning in enumerate(v.errors.values()):
                    print(' ', i+1, warning[0])
            else:
                warn = list(v.errors.values())[0][0]
                print('Warning:', warn[0].lower() + warn[1:] if warn else warn)

        if show_data:
            checkargs = sauroneye._checkargs
            args = ' '.join(checkargs[check] for check in v.errors)
            self.plot(args)
