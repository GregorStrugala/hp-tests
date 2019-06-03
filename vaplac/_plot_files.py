"""
This module implements the plot_files function,
to plot a single quantity from several data files.

"""


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
from math import sqrt, floor
from os.path import split

from .base import DataTaker

def plot_files(var, initialdir='./heating-data', paths=None, filetype=None):
    """
    Plot a single variable from several data files.

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
        quantity = DataTaker(filename=path).get(var)
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
