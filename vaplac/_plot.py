"""
This module implements the plot function,
to easily produce formatted subplots from Quantity objects.

"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings

def plot(*args, commons=None, pos='abscissa', sharex='col', sharey='row',
         legend=True, legend_args={'frameon':False}, plots_types=None,
         plots_args=None, scatter_args={'s':10}, line_args={}, **kwargs):
    """
    Plot given quantities, and easily create subplots.

    Parameters
    ----------
    *args : xpint Quantity, or list of xpint Quantity
        The quantities to be plotted. Quantities grouped in a list are
        plotted in the same axis.
    commons : list of xpint Quantity default None
        Variable(s) against which the first arguments are plotted.
        If a list of lists of quantities is given, a 'groupby' plot
        is assumed (see `groupby` argument in DataTaker.plot).
        If None, the first argument in *args is taken by default.
        Plotting only one quantity will raise an error.
    pos : 'abscissa' or 'ordinate', default 'abscissa'
        Axis on which the common variable should be displayed.
    sharex : bool or {'none', 'all', 'row', 'col'}, default 'col'
        Controls sharing of properties among x axis (see parameter
        `sharex` in `matplotlib.pyplot.subplots` function).
    sharey : bool or {'none', 'all', 'row', 'col'}, default False
        Controls sharing of properties among y axis (see parameter
        `sharey` in `matplotlib.pyplot.subplots` function).
    legend : bool, default True
        When set to False, no legend is displayed.
    legend_args : dict, default {'frameon':False}
        The keyword arguments used to customize the legend.
    plots_types : list, default None
        A nested list that allow to specify each plot subplot type
        ('line' or 'scatter') individually. Each sublist element must be
        either 'line', 'scatter' or None. The list must have a shape
        corresponding to the subplots layout.
    plots_args : list, default None
        A nested list that allow to specify keyword arguments for each
        subplot individually. All elements should be a dict, or None.
        The list must have a shape corresponding to the subplots layout.
    scatter_args : dict, default {'s':10}
        Keyword arguments that are passed to all scatter plots, if any.
    line_args : dict, default {}
        Keyword arguments that are passed to all line plots, if any.
    **kwargs
        Any remaining keyword arguments will be passed to each subplot,
        regardless of its type.

    Examples
    --------
    Plot only two quantities against each other (say Tr and t):

    >>> plot(Tr, t)

    Group some quantities (say Tr, Ts) in the same axis, and plot them
    against another (say f):

    >>> plot(f, [Tr, Ts])

    Specify several independent quantities (say t and f):

    >>> plot(Tr, Ts, commons=[t, f])

    Plot Tr and Ts against Tout, with Tout as ordinate

    >>> plot([Tr, Ts], commons=[Tout], pos='ordinate')

    """

    if commons is None and len(args) < 2:
        raise ValueError('At least two dependent variables must be provided.')
    elif commons is None:
        if isinstance(args[0], list):
            commons = [args[0][0]]
            args_start = args[0][1:] if len(args[0]) > 1 else []
            args = args_start + args[1:]
        else:
            commons = [args[0]]
            args = args[1:]

    abscissa = (pos == 'abscissa')
    ordinate = (pos == 'ordinate')
    if not (abscissa or ordinate):
        err = "Parameter pos should be either 'abscissa' or 'ordinate'."
        raise ValueError(err)

    if 's' in kwargs:
        scatter_args['s'] = kwargs.pop('s')

    warn_msg_dim = ('Quantities with different dimensionalities '
                    'are displayed on the same plot')
    warn_msg_unit = ('Quantities with different units '
                     'are displayed on the same plot')
    warnings.simplefilter('always')

    properties = {  # Label used for Axes with several plots
        'temperature':'$T$', 'electrical power':'$P$',
        'mechanical power':'$\dot{W}$','heat transfer rate':'$\dot{Q}$',
        'difference of internal energy rate of change':'$\Delta\dot U$',
        'flow rate':'$\dot{m}$', 'frequency':'$f$', 'pressure':'$p$',
        'specific enthalpy':'$h$', 'relative humidity':'$\phi$',
        'absolute humidity':'$\omega$', 'flow direction':'$\gamma$',
        'relative error':'$\delta$', 'enthalpy':'$h$', 'time':'$t$'}

    def ordered(i, j):
        return (i,j) if abscissa else (j,i)

    # Create the figure and axis.
    fig, ax = plt.subplots(*ordered(len(args), len(commons)),
                           sharex=sharex, sharey=sharey,
                           squeeze=False, facecolor=(.93,.93,.93))

    def label(quantity, attribute, common=False):
        """Create an axis label for the quantity q."""

        # Ensure that there is a non-empty label
        # or a property listed in the properties dictionary
        if (attribute == 'label' and quantity.label is None or
            attribute == 'prop' and quantity.prop not in properties):
            return None

        pre = {'label': quantity.label,
               'prop': properties[quantity.prop]}.get(attribute, '')
        # Cannot use Quantity().dimensionless in case of percentages
        if str(quantity.units) != 'dimensionless':
            post = f' ({quantity.units:~P})'
        else:
            post = ''
        axis = 'x' if common and abscissa or not (common or abscissa) else 'y'
        return {f'{axis}label': pre + post if pre + post != '' else None}

    def set_legend(ax, j):
        """Create a well-positionned legend for the speicifed axis."""

        sep = 1.05 if legend_args['frameon'] else 1
        if abscissa and j == len(commons) - 1:
            new_entries = {'loc': 'center left',
                           'bbox_to_anchor': (sep, 0.5)}
            legend_args.update(new_entries)
            ax.legend(**legend_args)
        elif ordinate and j == 0:
            new_entries = {'loc': 'lower center',
                           'bbox_to_anchor': (0.5, sep)}
            legend_args.update(new_entries)
            ax.legend(**legend_args)
        plt.tight_layout()
        plt.gcf().subplots_adjust(bottom=0.11, left=0.11)

    coordinates = '{}: {:.2f} {:~P}     {}: {:.2f} {:~P}'

    def formatter(x, y, props, units):
        xprop, yprop, xunits, yunits = *props, *units
        return coordinates.format(xprop, x, xunits, yprop, y, yunits)

    # wrap formatter using kwargs so that
    # each subplot gets its own statusbar
    def fmtr_wrap(xprop, yprop, xunits, yunits):

        def fmt_coord(x, y, props=ordered(xprop, yprop),
                      units=ordered(xunits, yunits)):
            return formatter(x, y, props, units)

        return fmt_coord

    def set_defaults(x, y, row, col):

        if plots_types is None:
            has_time = x.check('[time]') or y.check('[time]')
            plot_type = 'line' if has_time else 'scatter'
        else:
            plot_type = plots_types[row][col]
        plot_args = (plots_args[row][col] if plots_args else {}) or {}
        type_args = {'scatter': scatter_args, 'line': line_args}[plot_type]
        return plot_type, {**kwargs, **type_args, **plot_args}

    def iterator(x, y):
        """Iterator used to avoid a nested for loop."""

        return (((i, xi), (j, yj)) for i, xi in enumerate(x)
                                   for j, yj in enumerate(y))

    for (j, common), (i, arg) in iterator(commons, args):
        row, col = ordered(i, j)
        if isinstance(arg, list) and isinstance(common, list):
            for grouped_arg, grouped_common in zip(arg, common):
                plot_type, plot_args = set_defaults(grouped_common, grouped_arg,
                                                    row, col)
                call = {'line': 'plot', 'scatter': 'scatter'}[plot_type]
                plot_call = getattr(ax[row, col], call)
                plot_call(*ordered(grouped_common.magnitude,
                                   grouped_arg.magnitude),
                          label=grouped_arg.group, **plot_args)
            fmt_coord = fmtr_wrap(common[0].prop, arg[0].prop,
                                  common[0].units, arg[0].units)
        elif isinstance(arg, list):
            for quantity in arg:
                plot_type, plot_args = set_defaults(common, quantity, row, col)
                call = {'line': 'plot', 'scatter': 'scatter'}[plot_type]
                plot_call = getattr(ax[row, col], call)
                plot_call(*ordered(common.magnitude, quantity.magnitude),
                          label=quantity.label, **plot_args)
                if quantity.dimensionality != arg[0].dimensionality:
                    warnings.warn(warn_msg_dim)
                if quantity.units != arg[0].units:
                    warnings.warn(warn_msg_unit)
            fmt_coord = fmtr_wrap(common.prop, arg[0].prop,
                                  common.units, arg[0].units)
            if legend and (j == 0 or j == len(commons) - 1):
                set_legend(ax[row, col], j)
        else:
            plot_type, plot_args = set_defaults(common, arg, row, col)
            call = {'line': 'plot', 'scatter': 'scatter'}[plot_type]
            plot_call = getattr(ax[row, col], call)
            plot_call(*ordered(common.magnitude, arg.magnitude), **plot_args)
            fmt_coord = fmtr_wrap(common.prop, arg.prop,
                                  common.units, arg.units)
        ax[row, col].format_coord = fmt_coord

        if j == 0 and abscissa or j == len(commons) - 1 and ordinate:
            if isinstance(arg, list) and isinstance(common, list):
                ax[row, col].set(**label(arg[-1], 'label'))
            elif isinstance(arg, list):
                ax[row, col].set(**label(arg[-1], 'prop'))
            else:
                ax[row, col].set(**label(arg, 'label'))
        row, col = ordered(0 if ordinate else len(args) - 1, j)
        if isinstance(common, list):
            ax[row, col].set(**label(common[-1], 'label', common=True))
        else:
            ax[row, col].set(**label(common, 'label', common=True))
    if legend and isinstance(commons[0], list):
        new_entries = {'loc': 'lower left', 'bbox_to_anchor': (0, 1)}
        legend_args.update(new_entries)
        ax[ordered(0, len(commons)-1)].legend(**legend_args)
        plt.tight_layout()
