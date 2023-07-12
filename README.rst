Backend, Web Frontend and Tasks
===============================

Local installation
==================

This code base is meant to be run on Ubuntu 14 and Heroku's Cedar-14 platform.

After creating and sourcing a virtual environment please run:

.. code-block:: bash

    $ sudo apt-get install python-virtualenv python-dev postgresql-9.3 postgresql-server-dev-9.3
    $ pip install --upgrade -r requirements-dev.txt

This will install everything within `requirements.txt` as well.

If there are settings you don't wish to keep as environment variables on your local setup then please place them in `wishiwashi/base/local_settings.py`. This file is excluded from git.

Create Local DB
===============

.. code-block:: bash

    $ createdb -O <OWNER> -E utf8 <DB_NAME>


Updating Python Packages
========================
If you add in a new package, please place it in either `requirements.txt` or `requirements-dev.txt`.

When dumping out packages to update version pinnings please use `pip-dump`.

Environment Variables
=====================

Exported in hook $VIRTUAL_ENV/bin/postactivate

.. code-block:: bash

    export PYTHONPATH=/path/to/wishiwashi/
    export DJANGO_SETTINGS_MODULE=base.settings
    export DATABASE_URL='postgres://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>'  # Local install
    export STRIPE_API_KEY="sk_test_5OD9yinDX5BZqwVAyz4GKXZq"  # Test settings
    export STRIPE_PUBLISHABLE_KEY="pk_test_ncQmoeph4MSrDS9gZgDSM2zO"  # Test settings
    export RENDER_SERVICE_USERNAME="username"
    export RENDER_SERVICE_PASSWORD="testing"
    export COMMUNICATE_SERVICE_USERNAME="username"
    export COMMUNICATE_SERVICE_PASSWORD="testing"


Loading Fixtures
================

.. code-block:: bash

    $ python manage.py loaddata outcodes categories_and_items vendor_issues faq


Wishi Washi Vendor
==================

Wishi Washi the vendor is the initial and primary Vendor, on initial set up
import this vendor so the primary key matches VENDOR_WISHI_WASHI_PK

.. code-block:: bash

    $ python manage.py loaddata vendor


Syncing assets to Amazon Cloudfront
===================================

After Jenkins has successfully built the staging branch, login to Jenkins and run ``s3cmd``:

.. code-block:: bash

    $ ssh jenkins
    $ sudo su - jenkins
    $ cd /tmp/staging
    $ s3cmd sync wishiwashi/external/ s3://wishiwashi-backend-staging \
        --acl-public \
        --guess-mime-type \
        --config=/var/lib/jenkins/.s3cfg.staging

Heroku
======

Database
--------

Postgres daily scheduled backups at midnight Europe/London time.

.. code-block:: bash

    $ heroku pg:backups schedule --at '00:00 Europe/London' DATABASE_URL --app polar-escarpment-4510
    $ heroku pg:backups schedules --app polar-escarpment-4510
    === Backup Schedules
    DATABASE_URL: daily at 0:00 (Europe/London)


Download database and restore to new local database:

.. code-block:: bash

    $ heroku pg:backups capture --app polar-escarpment-4510
    $ curl -o latest.dump `heroku pg:backups public-url --app polar-escarpment-4510`
    $ createdb wishiwashi_db_2015_07_15 -O simon -E utf-8
    $ pg_restore --verbose --clean --no-acl --no-owner -p 5433 -h 127.0.0.1 -U simon -d wishiwashi_db_2015_07_15 latest.dump


Local Testing
=============

For testing individual units which do not require DB Set up, the TEST_RUNNER base.test_runner.NoDbTestRunner can be used.

Example:

.. code-block:: bash

    $ python manage.py test --testrunner base.test_runner.NoDbTestRunner vendors.tests.views.Views.test_update_order_wishi_washi_only

