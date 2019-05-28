from tkinter import Tk
from tkinter.filedialog import askopenfilename, askopenfilenames
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt, floor
from os.path import split

from explore import Explorer

def plot_files(var, initialdir='./heating-data', paths=None,
               filetype=None, return_data=False):
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

    def read_file(file, **kwargs):

        # Append if filetype is None or excel,
        # and the current file is an excel file
        if (str(filetype).lower() in ('none', 'excel', 'xlsx', '.xlsx') and
            file.lower().endswith('.xlsx')):
            
            if any(word in list(pd.read_excel(file))[0] for word in
                   ['load', 'aux', 'setpoint', '|', 'PdT']):
                # Skip the first row containing the conditions
                return pd.read_excel(file, skiprows=1, **kwargs)
            else:
                return pd.read_excel(file, **kwargs)

        # Append if filetype is None or csv,
        # and the current file is a csv file
        elif (str(filetype).lower() in ('none', 'csv', '.csv') and
              file.lower().endswith('.csv')):
            if any(word in list(pd.read_csv(file))[0] for word in
                   'load aux setpoint | PdT'.split()):
                return pd.read_csv(file, skiprows=1, **kwargs)
            else:
                return pd.read_csv(file, **kwargs)


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

    if return_data:
        return df

