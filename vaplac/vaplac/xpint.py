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
