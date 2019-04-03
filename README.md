This repository contains scripts and files to read, plot and process data from *DataTaker* file(s). Two modules are provided: `explore.py`, with useful functions for data processing and visualization, and `xpint.py`, that implements a subclass of `UnitRegistry` from the [`pint`](https://pint.readthedocs.io) package, to manage units and plot labelling.

## The `explore` module
The functions `read`, `get` and `plot` can be used respectively to read, extract and plot the data from a *DataTaker* file. All actions are also combined in one unique function called `explore`, which is more concise but has a little less flexibility. All the functions from the `explore` module are briefly described at the end, but more information can be found in their respective documentation—available through the `help` function.

## The `xpint` module
`xpint` (extended `pint`) provides an extension of `pint`'s `UnitRegistry` class that is used to define a new `Quantity` class, in order to provide a few more attributes. More details and examples can be found in the documentation, available using
```python
import xpint
help(xpint.UnitRegistry().Quantity)
```

### Functions of the `explore` module
| Function names  | Description |
| --------------- | ----------- |
| `explore`       | Plot and/or read the data from a file. This is basically a combination of the functions `read`, `get` and `plot`. |
| `read`          | Read the data from the file into a DataFrame. |
| `get`           | Extract specific variables from a DataFrame into `Quantity` objects. |
| `plot`          | (Sub)plot one or several `Quantity` objects. |
| `thermo_cal` 		| Compute heat transfer from flowrate, pressures and temperatures. |
| `plot_files`    | Plot a quantity for several files to allow comparison. |

# Section