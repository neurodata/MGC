..  -*- coding: utf-8 -*-

.. _contents:

Overview of hyppo_
===================

.. _hyppo: https://hyppo.neurodata.io/

.. image:: https://img.shields.io/badge/arXiv-1907.02088-red.svg?style=flat
   :target: https://arxiv.org/abs/1907.02088
.. image:: https://img.shields.io/pypi/v/hyppo.svg
   :target: https://pypi.org/project/hyppo/
.. image:: https://img.shields.io/pypi/dm/hyppo
.. image:: https://img.shields.io/github/license/neurodata/hyppo
   :target: https://hyppo.neurodata.io/license.html

``hyppo`` (**HYP**\ othesis Testing in **P**\ yth\ **O**\ n, pronounced
"Hippo") is an open-source software package for multivariate hypothesis testing.

Motivation
----------

With the increase in the amount of data in many fields, a method to
consistently and efficiently decipher relationships within high dimensional
data sets is important. Because many modern datasets are multivariate,
univariate tests are not applicable. Many multivariate
hypothesis tests also have R packages available, but the interfaces are inconsistent
and most are not available in Python. ``hyppo`` is an extensive Python library
that includes many state of the art multivariate hypothesis testing
procedures using a common interface. The package is easy-to-use and is
flexible enough to enable future extensions.

Python
------

Python is a powerful programming language that allows concise expressions of
network algorithms.  Python has a vibrant and growing ecosystem of packages
that hyppo uses to provide more features such as numerical linear algebra and
plotting.  In order to make the most out of ``hyppo`` you will want to know how
to write basic programs in Python.  Among the many guides to Python, we
recommend the `Python documentation <https://docs.python.org/3/>`_.

Free software
-------------

``hyppo`` is free software; you can redistribute it and/or modify it under the
terms of the :doc:`Apache 2.0 </license>`.  We welcome contributions. Join us on
`GitHub <https://github.com/neurodata/hyppo>`_.

History
-------

``hyppo`` is a rebranding of ``mgcpy``, which was founded in September 2018.
The original version was designed and written by Satish Palaniappan, Sambit
Panda, Junhao Xiong, Sandhya Ramachandran, and Ronak Mehtra. This new version
was written by Sambit Panda.

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting Started

   tutorials/overview.rst
   install
   gallery/index.rst

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: User Guide

   tutorials

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference Docs

   api/index
   news
   license
