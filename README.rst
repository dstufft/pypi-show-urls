pypi-show-urls
==============

Shows information about where packages come from


Installation
------------

.. code:: bash

    $ pip install pypi-show-urls


Usage
-----

.. code:: bash

    # Show all the counts for a bunch of packages
    $ pypi-show-urls -p package1 package2 package3

    # Show all the counts for a set of packages owned by users
    $ pypi-show-urls -u user1 user2 user3

    # Show all the urls found and all the versions only available externally
    $ pypi-show-urls -v -p package1 package2 package3
    $ pypi-show-urls -v -u user1 user2 user3
