===============
 sopel-quotes
===============

|version| |build| |issues| |alerts| |coverage-status| |license|

Introduction
============
sopel-quotes is a module for handling user added quotes

Usage
=====

Adding Quote
~~~~~~~~~~~~
.. code-block::

    .quote a = b
    .quoteadd a = b

Retrieving Quote
~~~~~~~~~~~~~~~~
.. code-block::

    # Retrieve a random quote
    .quote
    # Retrieve a quote about a specific key
    .quote a

Deleting Quote
~~~~~~~~~~~~~~
.. code-block::

    .quotedelete a

Requirements
============

Python Requirements
~~~~~~~~~~~~~~~~~~~
.. code-block::

    sopel

System Requirements
~~~~~~~~~~~~~~~~~~~
.. code-block::

    libmysqlclient-dev

.. |version| image:: https://img.shields.io/pypi/v/sopel-modules.quotes.svg
   :target: https://pypi.python.org/pypi/sopel-modules.quotes
.. |build| image:: https://travis-ci.com/RustyBower/sopel-quotes.svg?branch=master
   :target: https://travis-ci.com/RustyBower/sopel-quotes
.. |issues| image:: https://img.shields.io/github/issues/RustyBower/sopel-quotes.svg
   :target: https://travis-ci.com/RustyBower/sopel-quotes/issues
.. |alerts| image:: https://img.shields.io/lgtm/alerts/g/RustyBower/sopel-quotes.svg
   :target: https://lgtm.com/projects/g/RustyBower/sopel-quotes/alerts/
.. |coverage-status| image:: https://coveralls.io/repos/github/RustyBower/sopel-quotes/badge.svg?branch=master
   :target: https://coveralls.io/github/RustyBower/sopel-quotes?branch=master
.. |license| image:: https://img.shields.io/pypi/l/sopel-modules.quotes.svg
   :target: https://github.com/RustyBower/sopel-quotes/blob/master/LICENSE
