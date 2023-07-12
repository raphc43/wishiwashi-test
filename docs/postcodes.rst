To collect a white list of postcode out codes for the UK the following steps were taken:

.. code-block:: bash

    $ wget http://www.doogal.co.uk/files/postcodes.zip
    $ unzip postcodes.zip
    $ grep -o '^\S*' postcodes.csv | awk '{print tolower($0)}' | \
      sort | uniq | tr '\n' ' ' > outcodes.txt

This list of codes was then added into a python string:

.. code-block:: python

    codes = """
    ab1 ab10 ab11 ab12 ab13 ab14 ab15 ... yo90 yo91 yo95 ze1 ze2 ze3
    """

The header row from postcodes.csv was also incidentally included and manually removed.

Then on the Django shell the string was parsed and each out code was added to the ``OutCodes`` model:

.. code-block:: python

    from bookings.models import OutCodes

    for code in codes.split(" "):
        if len(code.strip()) > 1:
            oc = OutCodes(out_code=code)
            oc.save()

Then the data was dumped into the initial data fixture for bookings:

.. code-block:: bash

    $ python manage.py dumpdata bookings.outcodes \
      --indent=4 >> bookings/fixtures/initial_data.json
