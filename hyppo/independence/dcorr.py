import numpy as np
from numba import njit

from ..tools import check_perm_blocks_dim, chi2_approx, compute_dist
from ._utils import _CheckInputs
from .base import IndependenceTest


class Dcorr(IndependenceTest):
    r"""
    Distance Correlation (Dcorr) test statistic and p-value.

    Dcorr is a measure of dependence between two paired random matrices of
    not necessarily equal dimensions. The coefficient is 0 if and only if the
    matrices are independent. It is an example of an energy distance.

    The statistic can be derived as follows:

    Let :math:`x` and :math:`y` be :math:`(n, p)` samples of random variables
    :math:`X` and :math:`Y`. Let :math:`D^x` be the :math:`n \times n`
    distance matrix of :math:`x` and :math:`D^y` be the :math:`n \times n` be
    the distance matrix of :math:`y`. The distance covariance is,

    .. math::

        \mathrm{Dcov}^b_n (x, y) = \frac{1}{n^2} \mathrm{tr} (D^x H D^y H)

    where :math:`\mathrm{tr} (\cdot)` is the trace operator and :math:`H` is
    defined as :math:`H = I - (1/n) J` where :math:`I` is the identity matrix
    and :math:`J` is a matrix of ones. The normalized version of this
    covariance is distance correlation `[1]`_ and is

    .. math::

        \mathrm{Dcorr}^b_n (x, y) = \frac{\mathrm{Dcov}^b_n (x, y)}
                                       {\sqrt{\mathrm{Dcov}^b_n (x, x)
                                              \mathrm{Dcov}^b_n (y, y)}}

    This is a biased test statistic. An unbiased alternative also exists, and is
    defined using the following: Consider the
    centering process where :math:`\mathbb{1}(\cdot)` is the indicator
    function:

    .. math::

        C^x_{ij} = \left[ D^x_{ij} - \frac{1}{n-2} \sum_{t=1}^n D^x_{it}
            - \frac{1}{n-2} \sum_{s=1}^n D^x_{sj}
            + \frac{1}{(n-1) (n-2)} \sum_{s,t=1}^n D^x_{st} \right]
            \mathbb{1}_{i \neq j}

    and similarly for :math:`C^y`. Then, this unbiased Dcorr is,

    .. math::

        \mathrm{Dcov}_n (x, y) = \frac{1}{n (n-3)} \mathrm{tr} (C^x C^y)

    The normalized version of this covariance `[2]`_ is

    .. math::

        \mathrm{Dcorr}_n (x, y) = \frac{\mathrm{Dcov}_n (x, y)}
                                        {\sqrt{\mathrm{Dcov}_n (x, x)
                                               \mathrm{Dcov}_n (y, y)}}

    The p-value returned is calculated using a permutation test using
    :meth:`hyppo.tools.perm_test`. The fast version of the test uses
    :meth:`hyppo.tools.chi2_approx`.

    When the data is 1 dimension and the distance metric is euclidean,
    and even faster version of the algorithm is run (computational
    complexity is :math:`\mathcal{O}(n \log n)`) `[3]`_.

    .. _[1]: https://projecteuclid.org/euclid.aos/1201012979
    .. _[2]: https://projecteuclid.org/euclid.aos/1413810731
    .. _[3]: https://www.sciencedirect.com/science/article/pii/S0167947319300313

    Parameters
    ----------
    compute_distance : str, callable, or None, default: "euclidean"
        A function that computes the distance among the samples within each
        data matrix.
        Valid strings for ``compute_distance`` are, as defined in
        :func:`sklearn.metrics.pairwise_distances`,

            - From scikit-learn: [``"euclidean"``, ``"cityblock"``, ``"cosine"``,
              ``"l1"``, ``"l2"``, ``"manhattan"``] See the documentation for
              :mod:`scipy.spatial.distance` for details
              on these metrics.
            - From scipy.spatial.distance: [``"braycurtis"``, ``"canberra"``,
              ``"chebyshev"``, ``"correlation"``, ``"dice"``, ``"hamming"``,
              ``"jaccard"``, ``"kulsinski"``, ``"mahalanobis"``, ``"minkowski"``,
              ``"rogerstanimoto"``, ``"russellrao"``, ``"seuclidean"``,
              ``"sokalmichener"``, ``"sokalsneath"``, ``"sqeuclidean"``,
              ``"yule"``] See the documentation for :mod:`scipy.spatial.distance` for
              details on these metrics.

        Set to ``None`` or ``"precomputed"`` if ``x`` and ``y`` are already distance
        matrices. To call a custom function, either create the distance matrix
        before-hand or create a function of the form ``metric(x, **kwargs)``
        where ``x`` is the data matrix for which pairwise distances are
        calculated and ``**kwargs`` are extra arguements to send to your custom
        function.
    bias : bool, default: False
        Whether or not to use the biased or unbiased test statistics.
    **kwargs
        Arbitrary keyword arguments for ``compute_distance``.
    """

    def __init__(self, compute_distance="euclidean", bias=False, **kwargs):
        # set is_distance to true if compute_distance is None
        self.is_distance = False
        if not compute_distance:
            self.is_distance = True
        self.bias = bias
        self.is_fast = False
        IndependenceTest.__init__(self, compute_distance=compute_distance, **kwargs)

    def statistic(self, x, y):
        r"""
        Helper function that calculates the Dcorr test statistic.

        Parameters
        ----------
        x,y : ndarray
            Input data matrices. ``x`` and ``y`` must have the same number of
            samples. That is, the shapes must be ``(n, p)`` and ``(n, q)`` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, ``x`` and ``y`` can be distance matrices,
            where the shapes must both be ``(n, n)``.

        Returns
        -------
        stat : float
            The computed Dcorr statistic.
        """
        distx = x
        disty = y

        if not self.is_distance and not self.is_fast:
            distx, disty = compute_dist(
                x, y, metric=self.compute_distance, **self.kwargs
            )

        stat = _dcorr(distx, disty, bias=self.bias, is_fast=self.is_fast)
        self.stat = stat

        return stat

    def test(self, x, y, reps=1000, workers=1, auto=True, perm_blocks=None):
        r"""
        Calculates the Dcorr test statistic and p-value.

        Parameters
        ----------
        x,y : ndarray
            Input data matrices. ``x`` and ``y`` must have the same number of
            samples. That is, the shapes must be ``(n, p)`` and ``(n, q)`` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, ``x`` and ``y`` can be distance matrices,
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
            If ``x`` and ``y`` have `p` equal to 1 and ``compute_distance`` set to
            ``'euclidean'``, then and :math:`\mathcal{O}(n \log n)` version is run.
        perm_blocks : None or ndarray, default: None
            Defines blocks of exchangeable samples during the permutation test.
            If None, all samples can be permuted with one another. Requires `n`
            rows. At each column, samples with matching column value are
            recursively partitioned into blocks of samples. Within each final
            block, samples are exchangeable. Blocks of samples from the same
            partition are also exchangeable between one another. If a column
            value is negative, that block is fixed and cannot be exchanged.

        Returns
        -------
        stat : float
            The computed Dcorr statistic.
        pvalue : float
            The computed Dcorr p-value.

        Examples
        --------
        >>> import numpy as np
        >>> from hyppo.independence import Dcorr
        >>> x = np.arange(25)
        >>> y = x
        >>> stat, pvalue = Dcorr().test(x, y)
        >>> '%.1f, %.2f' % (stat, pvalue)
        '1.0, 0.00'

        In addition, the inputs can be distance matrices. Using this is the,
        same as before, except the ``compute_distance`` parameter must be set
        to ``None``.

        >>> import numpy as np
        >>> from hyppo.independence import Dcorr
        >>> x = np.ones((10, 10)) - np.identity(10)
        >>> y = 2 * x
        >>> dcorr = Dcorr(compute_distance=None)
        >>> stat, pvalue = dcorr.test(x, y)
        >>> '%.1f, %.2f' % (stat, pvalue)
        '0.0, 1.00'
        """
        check_input = _CheckInputs(
            x,
            y,
            reps=reps,
        )
        x, y = check_input()
        if perm_blocks is not None:
            check_perm_blocks_dim(perm_blocks, y)

        if (
            auto
            and x.shape[1] == 1
            and y.shape[1] == 1
            and self.compute_distance == "euclidean"
        ):
            self.is_fast = True

        if auto and x.shape[0] > 20 and perm_blocks is None:
            stat, pvalue = chi2_approx(self.statistic, x, y)
            self.stat = stat
            self.pvalue = pvalue
            self.null_dist = None
        else:
            is_distsim = False
            if not self.is_fast:
                x, y = compute_dist(x, y, metric=self.compute_distance, **self.kwargs)
                self.is_distance = True
                is_distsim = True
            stat, pvalue = super(Dcorr, self).test(
                x, y, reps, workers, perm_blocks=perm_blocks, is_distsim=is_distsim
            )

        return stat, pvalue


@njit
def _center_distmat(distx, bias):  # pragma: no cover
    """Centers the distance matrices"""
    n = distx.shape[0]
    if bias:
        # use sum instead of mean because of numba restrictions
        exp_distx = (
            np.repeat(distx.sum(axis=0) / n, n).reshape(-1, n).T
            + np.repeat(distx.sum(axis=1) / n, n).reshape(-1, n)
            - (distx.sum() / (n * n))
        )
    else:
        exp_distx = (
            np.repeat((distx.sum(axis=0) / (n - 2)), n).reshape(-1, n).T
            + np.repeat((distx.sum(axis=1) / (n - 2)), n).reshape(-1, n)
            - distx.sum() / ((n - 1) * (n - 2))
        )
    cent_distx = distx - exp_distx
    if not bias:
        np.fill_diagonal(cent_distx, 0)
    return cent_distx


@njit
def _cpu_cumsum(data):
    """Create cumulative sum since numba doesn't sum over axes."""
    cumsum = data
    if data.shape[0] != 1 and data.shape[1] != 1:
        for i in range(1, data.shape[0]):
            cumsum[i, :] = data[i, :] + cumsum[i - 1, :]
    return cumsum


@njit
def _fast_1d_dcov(x, y, bias=False):  # pragma: no cover
    """
    Calculate the Dcorr test statistic. Note that though Dcov is calculated
    and stored in covar, but not called due to a slower implementation.
    """
    n = x.shape[0]

    # sort inputs
    x = np.sort(x.ravel())
    y = y[np.argsort(x)]
    x = x.reshape(-1, 1)  # for numba

    # cumulative sum
    si = _cpu_cumsum(x)
    ax = np.arange(-(n - 2), n + 1, 2).reshape(-1, 1) * x + (
        si[-1] - 2 * si.copy().reshape(-1, 1)
    )

    v = np.hstack((x, y, x * y))
    nw = v.shape[1]

    idx = np.vstack((np.arange(n), np.zeros(n))).astype(np.int64).T
    ivs = [np.zeros(n)] * 4

    i = 0
    r = 0
    s = 1
    while i < n:
        gap = 2 * (i + 1)
        k = 0
        idx_r = idx[:, r]
        csumv = np.vstack((np.zeros(nw).reshape(1, -1), _cpu_cumsum(v[idx_r, :])))
        for j in range(0, n, gap):
            sts = [j, j + i]
            es = [min(sts[0] + i, n), min(sts[1] + i, n)]

            while (sts[0] < es[0]) and (sts[1] < es[1]):
                indexes = [idx_r[sts[0]], idx_r[sts[1]]]

                if y[indexes[0]] >= y[indexes[1]]:
                    idx[k, s] = indexes[0]
                    sts[0] += 1
                else:
                    idx[k, s] = indexes[1]
                    sts[1] += 1
                    ivs[0][indexes[1]] += es[0] - sts[0] + 1
                    ivs[1][indexes[1]] += csumv[es[0], 0] - csumv[sts[0], 0]
                    ivs[2][indexes[1]] += csumv[es[0], 1] - csumv[sts[0], 1]
                    ivs[3][indexes[1]] += csumv[es[0], 2] - csumv[sts[0], 2]
                k += 1

            if sts[0] < es[0]:
                kf = k + es[0] - sts[0]
                idx[k:kf, s] = idx_r[sts[0] : es[0]]
                k = kf
            elif sts[1] < es[1]:
                kf = k + es[1] - sts[1]
                idx[k:kf, s] = idx_r[sts[1] : es[1]]
                k = kf

        i = gap
        r = 1 - r
        s = 1 - s

    covterm = n * (x - np.mean(x)).T @ (y - np.mean(y))
    cs = [ivs[0].T @ v[:, 2].copy(), np.sum(ivs[3]), ivs[1].T @ y, ivs[2].T @ x]
    d = 4 * ((cs[0] + cs[1]) - (cs[2] + cs[3])) - 2 * covterm

    y = y[np.flip(idx[:, r])]
    si = _cpu_cumsum(y)
    by = np.zeros((n, 1))
    by[np.flip(idx[:, r])] = np.arange(-(n - 2), n + 1, 2).reshape(-1, 1) * y + (
        si[-1] - 2 * si.copy().reshape(-1, 1)
    )

    if bias:
        denom = [n ** 2, n ** 3, n ** 4]
    else:
        denom = [n * (n - 3), n * (n - 3) * (n - 2), n * (n - 3) * (n - 2) * (n - 1)]

    stat = np.sum(
        (d / denom[0])
        + (np.sum(ax) * np.sum(by) / denom[2])
        - (2 * (ax.T @ by) / denom[1])
    )

    return stat


@njit
def _dcov(distx, disty, bias=False, only_dcov=True):  # pragma: no cover
    """Calculate the Dcov test statistic"""
    if only_dcov:
        # center distance matrices
        distx = _center_distmat(distx, bias)
        disty = _center_distmat(disty, bias)

    stat = np.sum(distx * disty)

    if only_dcov:
        N = distx.shape[0]
        if bias:
            stat = 1 / (N ** 2) * stat
        else:
            stat = 1 / (N * (N - 3)) * stat

    return stat


@njit
def _dcorr(distx, disty, bias=False, is_fast=False):  # pragma: no cover
    """
    Calculate the Dcorr test statistic. Note that though Dcov is calculated
    and stored in covar, but not called due to a slower implementation.
    """
    if is_fast:
        # calculate covariances and variances
        covar = _fast_1d_dcov(distx, disty, bias=bias)
        varx = _fast_1d_dcov(distx, distx, bias=bias)
        vary = _fast_1d_dcov(disty, disty, bias=bias)
    else:
        # center distance matrices
        distx = _center_distmat(distx, bias)
        disty = _center_distmat(disty, bias)

        # calculate covariances and variances
        covar = _dcov(distx, disty, bias=bias, only_dcov=False)
        varx = _dcov(distx, distx, bias=bias, only_dcov=False)
        vary = _dcov(disty, disty, bias=bias, only_dcov=False)

    # stat is 0 with negative variances (would make denominator undefined)
    if varx <= 0 or vary <= 0:
        stat = 0

    # calculate generalized test statistic
    else:
        stat = covar / np.real(np.sqrt(varx * vary))

    return stat
