from ._plot import _plot

def plot(*args, commons=None, pos='abscissa', sharex='col', sharey='row',
         legend=True, legend_args={'frameon':False}, plots_types=None,
         plots_args=None, scatter_args={'s':10}, line_args={}, colorbar=None,
         **kwargs):

    _plot(None, *args, commons=commons, pos=pos, sharex=sharex, sharey=sharey,
          legend=legend, legend_args=legend_args, plots_types=plots_types,
          plots_args=plots_args, scatter_args=scatter_args,
          line_args=line_args, colorbar=colorbar, **kwargs)
