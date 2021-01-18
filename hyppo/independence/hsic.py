import numpy as np
from numba import njit

from ..tools import chi2_approx, compute_kern
from ._utils import _CheckInputs
from .base import IndependenceTest
from .dcorr import Dcorr, _center_distmat


class Hsic(IndependenceTest):
    r"""
    Hilbert Schmidt Independence Criterion (Hsic) test statistic and p-value.

    Hsic is a kernel based independence test and is a way to measure
    multivariate nonlinear associations given a specified kernel [#1Hsic]_.
    The default choice is the Gaussian kernel, which uses the median distance
    as the bandwidth, which is a characteristic kernel that guarantees that
    Hsic is a consistent test `[1]`_ `[2]`_.

    The statistic can be derived as follows `[1]`_:

    Hsic is closely related distance correlation (Dcorr), implemented in
    :class:`hyppo.independence.Dcorr`, and exchanges distance matrices
    :math:`D^x` and :math:`D^y` for kernel similarity matrices :math:`K^x` and
    :math:`K^y`. That is, let :math:`x` and :math:`y` be :math:`(n, p)` samples
    of random variables
    :math:`X` and :math:`Y`. Let :math:`K^x` be the :math:`n \times n`
    kernel similarity matrix of :math:`x` and :math:`K^y` be the :math:`n \times n` be
    the kernel similarity matrix of :math:`y`. The Hsic statistic is,

    .. math::

        \mathrm{Hsic}^b_n (x, y) = \frac{1}{n^2} \mathrm{tr} (D^x H D^y H)

    They are exactly equivalent in the sense that every valid kernel has a corresponding
    valid semimetric to ensure their equivalence, and vice versa `[3]`_ `[4]`_. In
    other words, every Dcorr test is also an Hsic and vice versa. Nonetheless,
    implementations of Dcorr and Hsic use different metrics by default:
    Dcorr uses a euclidean distance while Hsic uses a Gaussian median kernel.

    The p-value returned is calculated using a permutation test using
    :meth:`hyppo.tools.perm_test`. The fast version of the test uses
    :meth:`hyppo.tools.chi2_approx`.

    .. _[1]: https://papers.nips.cc/paper/2007/file/d5cfead94f5350c12c322b5b664544c1-Paper.pdf
    .. _[2]: https://www.jmlr.org/papers/volume11/gretton10a/gretton10a.pdf
    .. _[3]: https://arxiv.org/abs/1806.05514
    .. _[4]: https://projecteuclid.org/euclid.aos/1383661264

    Parameters
    ----------
    compute_kernel : str, callable, or None, default: "gaussian"
        A function that computes the kernel similarity among the samples within each
        data matrix.
        Valid strings for ``compute_kernel`` are, as defined in
        ``sklearn.metrics.pairwise.pairwise_kernels``,

            ['additive_chi2', 'chi2', 'linear', 'poly', 'polynomial', 'gaussian',
            'laplacian', 'sigmoid', 'cosine']

        Set to ``None`` or ``'precomputed'`` if ``x`` and ``y`` are already kernel
        matrices. To call a custom function, either create the kernel matrix
        before-hand or create a function of the form ``metric(x, **kwargs)``
        where ``x`` is the data matrix for which pairwise similarities are
        calculated and ``**kwargs`` are extra arguements to send to your custom
        function.
    bias : bool, default: False
        Whether or not to use the biased or unbiased test statistics.
    **kwargs
        Arbitrary keyword arguments for ``compute_kernel``.
    """

    def __init__(self, compute_kernel="gaussian", bias=False, **kwargs):
        # set statistic and p-value
        self.compute_kernel = compute_kernel

        self.is_kernel = False
        if not compute_kernel:
            self.is_kernel = True
        self.bias = bias

        IndependenceTest.__init__(self, compute_distance=None, **kwargs)

    def statistic(self, x, y):
        r"""
        Helper function that calculates the Hsic test statistic.

        Parameters
        ----------
        x,y : ndarray
            Input data matrices. ``x`` and ``y`` must have the same number of
            samples. That is, the shapes must be ``(n, p)`` and ``(n, q)`` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, ``x`` and ``y`` can be kernel similarity
            matrices,
            where the shapes must both be ``(n, n)``.

        Returns
        -------
        stat : float
            The computed Hsic statistic.
        """
        distx = x
        disty = y

        if not self.is_kernel:
            kernx, kerny = compute_kern(x, y, metric=self.compute_kernel, **self.kwargs)
            distx = 1 - kernx / np.max(kernx)
            disty = 1 - kerny / np.max(kerny)

        stat = _dcov(distx, disty, self.bias)
        self.stat = stat

        return stat

    def test(self, x, y, reps=1000, workers=1, auto=True):
        r"""
        Calculates the Hsic test statistic and p-value.

        Parameters
        ----------
        x,y : ndarray
            Input data matrices. ``x`` and ``y`` must have the same number of
            samples. That is, the shapes must be ``(n, p)`` and ``(n, q)`` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, ``x`` and ``y`` can be kernel similarity
            matrices,
            where the shapes must both be ``(n, n)``.
        reps : int, default: 1000
            The number of replications used to estimate the null distribution
            when using the permutation test used to calculate the p-value.
        workers : int, default: 1
            The number of cores to parallelize the p-value computation over.
            Supply ``-1`` to use all cores available to the Process.
        auto : bool, default: True
            Automatically uses fast approximation when `n` and size of array
            is greater than 20. If ``True``, and sample size is greater than 20, then
            :class:`hyppo.tools.chi2_approx` will be run. Parameters ``reps`` and
            ``workers`` are
            irrelevant in this case. Otherwise, :class:`hyppo.tools.perm_test` will be
            run.

        Returns
        -------
        stat : float
            The computed Hsic statistic.
        pvalue : float
            The computed Hsic p-value.

        Examples
        --------
        >>> import numpy as np
        >>> from hyppo.independence import Hsic
        >>> x = np.arange(7)
        >>> y = x
        >>> stat, pvalue = Hsic().test(x, y)
        >>> '%.1f, %.2f' % (stat, pvalue)
        '0.2, 0.00'

        In addition, the inputs can be distance matrices. Using this is the,
        same as before, except the ``compute_kernel`` parameter must be set
        to ``None``.

        >>> import numpy as np
        >>> from hyppo.independence import Hsic
        >>> x = np.ones((10, 10)) - np.identity(10)
        >>> y = 2 * x
        >>> hsic = Hsic(compute_kernel=None)
        >>> stat, pvalue = hsic.test(x, y)
        >>> '%.1f, %.2f' % (stat, pvalue)
        '0.0, 1.00'
        """
        check_input = _CheckInputs(
            x,
            y,
            reps=reps,
        )
        x, y = check_input()

        if auto and x.shape[0] > 20:
            stat, pvalue = chi2_approx(self.statistic, x, y)
            self.stat = stat
            self.pvalue = pvalue
            self.null_dist = None
        else:
            x, y = compute_kern(x, y, metric=self.compute_kernel, **self.kwargs)
            self.is_kernel = True
            stat, pvalue = super(Hsic, self).test(x, y, reps, workers)

        return stat, pvalue


@njit
def _dcov(distx, disty, bias):  # pragma: no cover
    """Calculate the Dcov test statistic"""
    # center distance matrices
    cent_distx = _center_distmat(distx, bias)
    cent_disty = _center_distmat(disty, bias)

    N = distx.shape[0]
    covar = np.trace(cent_distx @ cent_disty)

    if bias:
        stat = 1 / (N ** 2) * covar
    else:
        stat = 1 / (N * (N - 3)) * covar

    return stat
