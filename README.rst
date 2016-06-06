Openupgrade buildout
====================

This repository contains a buildout. Prepare it by running::

    python bootstrap.py

and then run it with::

    bin/buildout

After that, you can run the actual migration::

    ./migrate.sh your_database_name
