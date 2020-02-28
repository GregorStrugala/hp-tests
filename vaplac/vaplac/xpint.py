"""
xpint (extended pint) provides an extension of pint's UnitRegistry class
that is used to define a new Quantity class, in order to provide a few
more attributes (see the Quantity class documentation).
"""
import pint, pint.quantity
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings


class UnitRegistry(pint.registry.UnitRegistry):
    """
    Defines the Registry, a class to contains units and their relations.

    This is a subclass of pint.registry.UnitRegistry, whose only purpose
    is to build a custom Quantity class. A UnitRegistry is necessary to
    create Quantity objects.
    """

    def __init__(self, filename='', force_ndarray=False,
                 default_as_delta=True,
                 autoconvert_offset_to_baseunit=False,
                 on_redefinition='warn', system=None,
                 auto_reduce_dimensions=False):

        # Inherit as in the parent UnitRegistry class
        super(UnitRegistry, self).__init__(
            filename=filename,
            force_ndarray=force_ndarray,
            on_redefinition=on_redefinition,
            default_as_delta=default_as_delta,
            autoconvert_offset_to_baseunit=autoconvert_offset_to_baseunit,
            system=system,
            auto_reduce_dimensions=auto_reduce_dimensions
        )

        # Build Quantity from the _Quantity class
        self.Quantity = build_quantity_class(self, force_ndarray)


class _Quantity(pint.quantity._Quantity):
    """
    Implementation of the Quantity class.
    """

    def __new__(cls, value, units=None, prop=None, label=None):
        self = super().__new__(cls, value, units)
        self._prop = prop
        self._label = label
        self._name = {'prop': prop, 'label': label}

        return self


    @property
    def prop(self):
        return self._prop

    @property
    def label(self):
        return self._label

    @property
    def name(self):
        return self._name

    def set_prop(self, prop):
        self._prop = prop
        self._name['prop'] = prop

    def set_label(self, label):
        self._label = label
        self._name['label'] = label

    def set_name(self, prop=None, label=None):
        self.set_prop(prop or self._prop)
        self.set_label(label or self._label)

    def to(self, other=None, *contexts, **ctx_kwargs):
        """Keep the values of `prop` and `label` after a conversion."""
        if other is None:
            return self.__class__(self._magnitude, units=self._units,
                                  prop=self._prop, label=self._label)
        else:
            quantity = super().to(other, *contexts, **ctx_kwargs)
            return self.__class__(quantity._magnitude, units=quantity._units,
                                  prop=self._prop, label=self._label)

    def __getitem__(self, key):
        """Keep the values of `prop` and `label` when indexing."""
        try:
            return type(self)(self._magnitude[key], self._units, **self._name)
        except pint.errors.PintTypeError:
            raise
        except TypeError:
            raise TypeError(
                "Neither Quantity object nor its magnitude ({})"
                "supports indexing".format(self._magnitude)
            )

    def __iter__(self):
        """Keep the values of `prop` and `label` when iterating."""

        # Make sure that, if self.magnitude is not iterable,
        # we raise TypeError as soon as one calls iter(self)
        # without waiting for the first element to be drawn from the iterator.
        it_magnitude = iter(self.magnitude)

        def it_outer():
            for element in it_magnitude:
                yield self.__class__(element, self._units, **self._name)

        return it_outer()

    def clean(self):
        """Replace UnderRange values by zero and divide by two."""
        if self.magnitude.dtype != 'O':
            raise Exception(('This function only applies to a Quantity'
                             ' whose magnitude dtype is \'O\''))
        self[self.magnitude == 'UnderRange'] = self.__class__(0, 'Hz')
        return self.__class__(self.astype(float)/2, units=self._units,
                              **self._name)

    def info(self, index=slice(0, None)):
        """Display the min, max and mean values of the quantity."""
        # Specify the property
        if self.dimensionless:
            if self._prop is None:
                print('dimensionless quantity', '\n')
            else:
                print(self._prop, '(dimensionless quantity)', '\n')

        else:
            if self._prop is None:
                print('Unspecified property',
                      f'(with units {self._units})', '\n')
            else:
                print(self._prop, '\n')

        def fmt(q):
            """Return the number to display with its char number."""
            q_rd = round(q, 2)
            if q.magnitude == 0 or q_rd.magnitude != 0:
                return len(str(q_rd)), q_rd
            else:
                return len(f'{q:.2e} '), f'{q:.2e} '

        # Get the length and values
        l_min, v_min = fmt(self.min())
        l_max, v_max = fmt(self.max())
        l_avg, v_avg = fmt(self.mean())
        l = max(l_min, l_max, l_avg)

        # and print 'em
        print('min: ' + ' '*(l-l_min), v_min)
        print('max: ' + ' '*(l-l_max), v_max)
        print('mean:' + ' '*(l-l_avg), v_avg)

    def plot(self, time='min', step=60, interval=slice(0, None)):
        """
        Plot the quantity versus time.

        Parameters
        ----------
        time : {'s', 'min', 'h', 'day'} or ndarray, default 'min'
            Controls what is displayed on the x-axis. If 's', 'min', 'h'
            or 'day' is given, a minute timestep is assumed by default
            and the x-axis is created to fit the length of variables in
            `*args` (see `step` parameter to set another timestep).
            Alternatively, an explicit array can be given
            (including datetime arrays).
        step : int or float
            The timestep between each measurement in seconds.
        interval : slice, default slice(0, None)
            A slice object containing the range over which the
            quantities are plotted.
        """

        # Disable pint's annoying UnitStrippedWarning warnings
        warnings.simplefilter('ignore')

        res = {'s':1/step, 'min':60/step, 'h':3600/step, 'days':86400/step}
        t_str = isinstance(time, str)
        t = np.arange(0, len(self)) / res[time] if t_str else time[interval]

        _, ax = plt.subplots()
        ax.plot(t, self[interval])

        # Set x-label
        x_label = 'time (' + (time if t_str else 'timestamp') + ')'
        ax.set(xlabel=x_label)

        # Set y-label
        if self.label is not None:
            if self.dimensionless:
                ax.set(ylabel=self.label)
            else:
                ax.set(ylabel=self.label + f' ({self.units:~P})')

        # label (or property) and units used in status bar
        sbdim, sbunit = self.prop, f'{self.units:~P}'

        # Create (unformatted) statusbar
        statusbar = {True:'time: {:.2f} {}     {}: {:.2f} {}',
                     False:'time: {}     {}: {:.2f} {}'}[t_str]

        def fmtr(x, y, sbdim=sbdim, sbunit=sbunit):
            """Make a formatter for the axis statusbar"""
            if t_str:
                return statusbar.format(x, time, sbdim, y, sbunit)

            else:

                def datefmt(ax):
                    t_min, t_max = (int(t) for t in ax.get_xlim())
                    fmt = '%d %H:%M:%S' if t_max-t_min > 0 else '%H:%M:%S'
                    return mdates.DateFormatter(fmt)

                return statusbar.format(datefmt(ax)(x), time, sbdim, y, sbunit)

        ax.format_coord = fmtr

    def movmean(self, n):
        """
        Compute the moving mean of the Quantity.

        Parameters
        ----------
        n : int
            Size of the window used to compute the moving average.
            This value must be odd, otherwise it will be incremented.

        Returns
        -------
        array_like
            Moving mean of array a with window of size n.

        Examples
        --------
        >>> ureg = UnitRegistry()
        >>> t = np.random.rand(50) * ureg.second
        >>> window_size = 9
        >>> t.movmean(window_size)

        """

        try:
            if len(self.magnitude) < 3:
                raise ValueError('The length must be at least 3 '
                                 'to compute a moving mean.')
        except TypeError:
            raise ValueError('The length must be at least 3 '
                             'to compute a moving mean.')
        # Increment n if it is even
        n += 1 if n % 2 == 0 else 0
        l = (n-1) // 2  # edge length
        # Compute cumulative sum
        cumsum = np.cumsum(self.magnitude, dtype=float)
        # Get a moving sum everywhere but on the edges
        movsum = (np.append(cumsum[l:], np.zeros(l))
                  - np.append(np.zeros(l+1), cumsum[:-l-1]))
        # Fill the edges by mirroring them and computing their moving sum
        cumsum_refl = np.cumsum(np.pad(self.magnitude, (l+1, l+1), 'reflect'))
        movsum_refl = cumsum_refl[n:] - cumsum_refl[:-n]
        # print(movsum)
        # print(movsum_refl)
        movsum[:l] = movsum_refl[:l]
        movsum[-l:] = movsum_refl[-l-1:-1]
        return self.__class__(movsum / n, self.units, **self._name)

def build_quantity_class(registry, force_ndarray=False):
    """Build a Quantity class from a registry, subclassing _Quantity"""

    class Quantity(_Quantity):
        """
        Phyiscal quantity (the product of a numerical value and a unit
        of measurement) with additional info that is not available in pint.

        This class creates Quantity objects similar to pint's quantities,
        but also provides the `prop` (property) and `label` attributes,
        along with some more methods. The method `to` (conversion between
        units) is modified to keep the attributes `prop` and `label`
        identical after the new object is returned.

        Attributes
        ----------
        Besides the attributes already present in pint's Quantity class,
        the followings are provided:
        prop: str
            The property wich is described by the quantity (e.g. voltage).
        label: str
            The label that with by displayed on the y label (or legend)
            of plots created with the `plot` function.
        Examples
        --------
        Create a registry and give a short name to the constructor:
        >>> from xpint import UnitRegistry
        >>> ureg = UnitRegistry()
        >>> Q_ = ureg.Quantity

        Create a Quantity object with a label and a property:
        >>> I = Q_('3 A', prop='electrical current', label='$I$')
        >>> I
        3 ampere
        >>> I.prop
        'electrical current'

        `prop` and `label` attributes are identical after a conversion:
        >>> I.to('mA').prop
        'electrical current'
        """
        pass

    Quantity._REGISTRY = registry
    Quantity.force_ndarray = force_ndarray

    return Quantity
