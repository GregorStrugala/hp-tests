This repository contains modules to read and process data file(s).  
It provides the [``vaplac``](#the-vaplac-package) package for data analysis,
which heavily relies on the [``xpint``](#The-xpint-module) module,
implementing a subclass of `UnitRegistry` from the
[`pint`](https://pint.readthedocs.io) package, to manage units
and plot labelling.

## The `vaplac` package
This packages provides three main functionalities:
1. **Va**lidate data from a file, based on several checks contained in the
  [vaplac.sauroneye](vaplac/sauroneye.py) module.
2. **Pl**ot and visualize the data.
3. **Ac**quire the data in the form of xpint Quantity objects.


The front-end classes, methods and functions are organized as follow:
```
vaplac/
├── DataTaker class (base.py)
|   ├── validate method
|   ├── plot method
|   └── get method
├── plot function (_plot.py)
└── plot_files function (_plot_files.py)
```

### The ``DataTaker`` class
``DataTaker`` objects are instantiated by providing a data file. They
can be used as shown by the following example:
1. Create a DataTaker, and validate the data
  ```python
  import vaplac as vpa
  dtk = vpa.DataTaker()  # No file name provided: a dialog box should ask for it.
  dtk.validate()  # If warnings are given, use show_data=True to display the relevant quantitites.
  ```
2. Plot the return and supply temperatures, the frequency in rpm and the inlet
and outlet pressures in MPa.
  ```python
  dtk.plot('(Tr Ts) f/rpm (pin pout)/MPa')
  ```
3. Extract the condenser heat output, the indoor fan power and the total
consumed power to compute the COP, then display some statistical
characteristics.
  ```python
  Qcond, Pfan_in, Ptot = dtk.get('Qcond Pfan_in Ptot')
  COP = (Qcond + Pfan_in) / Ptot
  COP.info()
  ```
Note that the variables have the same name than the arguments of the
`DataTaker.get` method because it improves clarity, but they do not
*have* to.
Moreover, the variables `Qcond` and `Pfan_in` can be added because they
have the same dimensionality, but the operation `COP + Ptot` will raise
a `DimensionalityError`.  
In order to be able to display quantities such as the condenser capacity,
the DataTaker class has methods to perform thermodynamic calculations,
but they are not part of the user interface since the relevant quantities
can be directly accessed through the `DataTaker.get` method.

More detailed information about each method is available with the `help`
function.

### The ``plot`` function
The top-level `plot` function works in the same way as the DataTaker.plot
method, but is dedicated to plotting Quantity objects.
Following the previous example, the condenser capacity and the total
power can be plotted along with the COP using
```python
vpa.plot([Qcond, Ptot], COP)
```

### The ``plot_files`` function
Sometimes plotting a quantity for several files may come in handy, this
can be performed using the `plot_files` function. Providing no parameters
will open a dialog box where several files can be opened. To plot a
quantity from all files in the default directory, simply use the option
`paths='all'`.

## The `xpint` module
`xpint` (extended pint) provides an extension of `pint`'s `UnitRegistry`
class that is used to define a new `Quantity` class,
in order to provide a few more attributes.
More details and examples can be found in the documentation,
available using
```python
import xpint
help(xpint.UnitRegistry().Quantity)
