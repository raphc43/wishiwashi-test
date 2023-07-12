from django.core.urlresolvers import reverse


def generate_progress_svg(current_stage, request, for_mobile=False):
    """
    :param str stage: name of the current stage. Choices are: pick_up,
                      delivery, items, contact_details, address, payment
    :param session obj: Request's session object session, good for seeing if
                        the next stages have already been filled in once.

    :return: svg of progress bar
    :rtype: str
    """
    svg_width = 300 if for_mobile else 600

    svg = """
    <?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                         "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
    <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg"
         xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
         width="%dpx" height="120px" viewBox="0 0 %d 120"
         enable-background="new 0 0 %d 120" xml:space="preserve">
    """ % (svg_width, svg_width, svg_width)

    stages = (
        {
            'id': 'pick_up',
            'label': 'Pick up',
            'href': reverse('bookings:pick_up_time'),
        },
        {
            'id': 'delivery',
            'label': 'Delivery',
            'href': reverse('bookings:delivery_time'),
        },
        {
            'id': 'items',
            'label': 'Items',
            'href': reverse('bookings:items_to_clean'),
        },
        {
            'id': 'contact_details',
            'label': 'Account',
            'href': reverse('registration:create_account'),
        },
        {
            'id': 'address',
            'label': 'Address',
            'href': reverse('bookings:address'),
        },
        {
            'id': 'payment',
            'label': 'Payment',
            'href': reverse('payments:landing'),
        },
    )

    # Stages that have been completed (irrespective of current stage)
    # These checks are very basic as the @check_session_data decorator
    # will redirect users if the data isn't perfect or has been later
    # deactivated
    completed_stage = -1

    # Stage check 0: Pick up Time
    if 'pick_up_time' in request.session and \
       request.session['pick_up_time'] is not None and \
       len(request.session['pick_up_time'].strip()) >= 8:
        completed_stage = 0

        # Stage check 1: Delivery
        if 'delivery_time' in request.session and \
           request.session['delivery_time'] is not None and \
           len(request.session['delivery_time'].strip()) >= 8:
            completed_stage = 1

            # Stage check 2: Items and Prices
            if 'items' in request.session:
                completed_stage = 2

                # Stage check 3: Contact Details
                if request.user and request.user.is_authenticated() and 'items' in request.session:
                    completed_stage = 3

                    # Stage check 4: Address
                    if 'address' in request.session:
                        completed_stage = 4

    # Stage check 5: Payment
    # This will never be completed as the session is complete when this page is

    # Current stage index
    current_stage_index = None

    for index, stage in enumerate(stages):
        if current_stage == stage['id']:
            current_stage_index = index
            break

    assert current_stage_index is not None, current_stage

    # Most elements separation distance is doubled on desktop compared to mobile
    x_axis_mul = 40 if for_mobile else 100

    for index, stage in enumerate(stages):
        # Connecting lines
        line_width = 45 if for_mobile else 90
        initial_x_offset = -35 if for_mobile else 0

        if index < len(stages) - 1:
            line_color = '00ADE0'

            if index > completed_stage:
                line_color = '999999'

            tmpl = """
            <rect x="71.333" y="51" fill="#%s" width="%d" height="6.333"
                  transform="translate(%d,0)"/>
            """
            svg += tmpl % (line_color,
                           line_width,
                           (index * x_axis_mul) + initial_x_offset)

        # Circle(s)
        initial_x_offset = 35 if for_mobile else 53

        circle_color = '00ADE0'

        if index > completed_stage + 1:
            circle_color = '999999'

        circle_diamiter = 15 if for_mobile else 21

        # Decide if it should have a URL link or not
        if circle_color == '999999':
            tmpl = '<circle fill="#%s" cx="%d" cy="52" r="%d"/>'
            svg += tmpl % (circle_color,
                           (index * x_axis_mul) + initial_x_offset,
                           circle_diamiter)
        else:
            tmpl = """
            <a xlink:href="%s">
                <circle fill="#%s" cx="%d" cy="52" r="%d"/>
            </a>
            """
            svg += tmpl % (stage['href'],
                           circle_color,
                           (index * x_axis_mul) + initial_x_offset,
                           circle_diamiter)

        if current_stage == stage['id']:
            circle_diamiter = circle_diamiter - 4
            tmpl = '<circle fill="#ffffff" cx="%d" cy="52" r="%d"/>'
            x_axis_mul = 40 if for_mobile else 100
            svg += tmpl % ((index * x_axis_mul) + initial_x_offset,
                           circle_diamiter)

        # Tick mark
        scale = 0.5 if for_mobile else 1.0  # Tick mark and current arrow
        y_offset = 26 if for_mobile else 0
        initial_x_offset = 9 if for_mobile else 0

        if index <= completed_stage and index != current_stage_index:
            tmpl = """
            <a xlink:href="%s">
                <polygon fill="#%s" transform="translate(%d,%f) scale(%f,%f)"
                         points="50.803,58.555 42.401,51.84 38.084,57.242
                                 51.087,67.633 55.404,62.23 69.671,44.378
                                 65.071,40.701"/>
            </a>
            """
            tick_colour = '00ADE0' if current_stage == stage['id'] else 'ffffff'

            svg += tmpl % (stage['href'],
                           tick_colour,
                           (index * x_axis_mul) + initial_x_offset,
                           y_offset,
                           scale,
                           scale)

        # Current arrow
        if index == current_stage_index:
            tmpl = """
            <polygon fill="#00ADE0" transform="translate(%d,%f) scale(%f,%f)"
                     points="63.842,44.857 53,55.699 42.158,44.856
                             38.269,48.746 49.111,59.588 53,63.477
                             56.889,59.587 67.731,48.746 "/>
            """
            svg += tmpl % ((index * x_axis_mul) + initial_x_offset,
                           y_offset,
                           scale,
                           scale)

        # Label
        label = stage['label']

        if for_mobile:
            if index == current_stage_index:
                label = label.replace('\n', ' ')

                tmpl = """
                <text transform="matrix(1 0 0 1 150 105)"
                      font-family="Open Sans"
                      style="font-weight: 700;"
                      text-anchor="middle"
                      font-size="30"
                      fill="#00ADE0">%s</text>
                """
                svg += tmpl % label
        else:
            label_color = '999999'

            if index <= completed_stage + 1 or current_stage == stage['id']:
                label_color = '00ADE0'

            if '\n' in label:
                # Decide if it should have a URL link or not
                if label_color == '999999':
                    tmpl = """
                    <tspan x="1.162" y="%d" font-family="Open Sans"
                           style="font-weight: 700;" font-size="16">%s</tspan>
                    """
                    label = ''.join([tmpl % (line_index * 18, line)
                                     for line_index, line in enumerate(label.split('\n'))])
                else:
                    tmpl = """
                    <a xlink:href="%s">
                        <tspan x="1.162" y="%d"
                               font-family="Open Sans"
                               style="font-weight: 700;"
                               font-size="16">%s</tspan>
                    </a>
                    """
                    label = ''.join([tmpl % (stage['href'],
                                             line_index * 18,
                                             line)
                                     for line_index, line in enumerate(label.split('\n'))])

            # Decide if it should have a URL link or not
            if label_color == '999999':
                tmpl = """
                <text transform="matrix(1 0 0 1 %d 94)"
                      font-family="Open Sans"
                      style="font-weight: 700;"
                      font-size="16"
                      fill="#%s">%s</text>
                """
                svg += tmpl % ((index * x_axis_mul) + 26,
                               label_color,
                               label)
            else:
                tmpl = """
                <a xlink:href="%s">
                    <text transform="matrix(1 0 0 1 %d 94)"
                          font-family="Open Sans"
                          style="font-weight: 700;"
                          font-size="16"
                          fill="#%s">%s</text>
                </a>
                """
                svg += tmpl % (stage['href'],
                               (index * x_axis_mul) + 26,
                               label_color,
                               label)

    svg += "</svg>"

    return svg


def get_progress_svg(current_stage, request):
    """
    :param str stage: name of the current stage. Choices are: pick_up,
                      delivery, items, contact_details, address, payment
    :param session obj: Request's session object session, good for seeing if
                        the next stages have already been filled in once.

    :return: svg of progress bar in desktop and mobile formats
    :rtype: tuple
    """
    desktop, mobile = (generate_progress_svg(current_stage, request, False),
                       generate_progress_svg(current_stage, request, True))

    return (desktop, mobile)
