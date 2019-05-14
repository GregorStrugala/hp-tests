This repository contains scripts and files to read,
plot and process data from *DataTaker* file(s).
Two modules are provided:
`explore.py`, that implements the `Explorer` class for processing and
visualizing data,
and `xpint.py`, that implements a subclass of `UnitRegistry`
from the [`pint`](https://pint.readthedocs.io) package,
to manage units and plot labelling.

## The `explore` module
This module provides the `Explorer` class, to read and plot data.
`Explorer` objects can also perform some thermodynamic calculations
to obtain new properties.
However, the functions implementing those calculations shouldn't have to
be directly called by the user, quantities that are not in the
*DataTaker* file will automatically be computed.

An `Explorer` object is initialized with the name of a data file.
Its [methods](#methods-of-the-explorer-class) allow to plot various
quantities or retrieve them as `Quantity` objects.
This last feature can be useful if some non-implemented calculations
need to be done.
Note that extracted (or newly computed) quantities can still
be plotted, using the top-level function `explore.plot`.

Each function from the `Explorer` class is briefly described at the end,
but more information can be found in their respective
documentation—available through the `help` function.

## The `xpint` module
`xpint` (extended pint) provides an extension of `pint`'s `UnitRegistry`
class that is used to define a new `Quantity` class,
in order to provide a few more attributes.
More details and examples can be found in the documentation,
available using
```python
import xpint
help(xpint.UnitRegistry().Quantity)
```

### Methods of the `Explorer` class
| Method names  | Description |
| ------------- | ----------- |
| `read`	| Read the data from the file into a DataFrame. |
| `get`         | Extract specific variables from a DataFrame into `Quantity` objects. |
| `plot`        | (Sub)plot one or several quantities. |
