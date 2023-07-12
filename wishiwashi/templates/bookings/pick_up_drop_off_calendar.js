{% load staticfiles %}

var calendar_grid = {{calendar_grid|safe}};

$(document.body).ready(function() {
    var pad = function(num, size) {
        var s = num + "";
        while (s.length < size) s = "0" + s;
        return s;
    },
    bind_form_submit_events = function(_prefix) {
        // Prefix is either #mobile or #desktop
        $(_prefix + " .time-slot").click(function(event){
            if(!$(this).hasClass('unavailable-slot')) {
                $(_prefix + ' img.selected-slot-checkmark').remove();
                $(_prefix + ' div.time-slot').removeClass('selected-slot');
                $(this).addClass("selected-slot");
                $(this).after('<img src="{% static "images/check.png" %}" width="39" height="39" alt="" class="selected-slot-checkmark">')
                $('input[name=time_slot]').attr('value', $(this).data('time'));
            }
        });
    },
    first_day_offset = function() {
        for(var i = 0; i < calendar_grid.length; i ++) {
            for(var j = 0; j < calendar_grid[i].time_slots.length; j ++) {
                if(calendar_grid[i].time_slots[j].available) {
                    return i;
                }
            }
        }
        return 0;
    }(),
    first_selected_day_offset = function() {
        // Find the first day with selectable times.
        // The grid is week-centric so the first few days might not have
        // selectable times
        if(parseInt({{selected_day|default:0}}) > 0) {
            return parseInt({{selected_day|default:0}});
        }

        for(var i = 0; i < calendar_grid.length; i ++) {
            for(var j = 0; j < calendar_grid[i].time_slots.length; j ++) {
                if(calendar_grid[i].time_slots[j].available) {
                    return i;
                }
            }
        }
        return 0;
    }(),

    // This is only used by the mobile version
    day_offset = first_selected_day_offset,

    // This is only used by the mobile version
    draw_day = function(_day_offset) {
        $('#mobile .calendar-month-label').html(calendar_grid[_day_offset].month_name);
        $('#mobile .calendar-date-wrapper').html('<div class="day-of-week">' + calendar_grid[_day_offset].day_name + '</div>' + calendar_grid[_day_offset].day_of_month);
    
        $('#mobile .time-slots-wrapper').remove();

        for(var i = Math.ceil(calendar_grid[_day_offset].time_slots.length / 2) - 1; i >= 0; i --) {
            var left_label = '',
                right_label = '',
                _html = '';

            if(calendar_grid[_day_offset].time_slots[i * 2]) {
                left_label = calendar_grid[_day_offset].time_slots[i * 2].label;
            }

            if(calendar_grid[_day_offset].time_slots[(i * 2) + 1]) {
                right_label = calendar_grid[_day_offset].time_slots[(i * 2) + 1].label;
            }
            
            _html = '<div class="row time-slots-wrapper"><div class="col-xs-6"><div class="time-slot">' + left_label + '</div></div>';
            
            if(right_label != '') {
                _html += '<div class="col-xs-6"><div class="time-slot">' + right_label + '</div></div>';
            }
                        
            _html += '</div>';
            $('#mobile .arrow-and-day-name-wrapper').after(_html);
        }

        for(var i = 0; i < calendar_grid[_day_offset].time_slots.length; i ++) {
            var selector = '#mobile .time-slot:eq(' + i + ')';

            if(!calendar_grid[_day_offset].time_slots[i].available) {
                $(selector).addClass('unavailable-slot').unbind('click');
            }

            $(selector).data('time', calendar_grid[_day_offset].date + ' ' + pad(calendar_grid[_day_offset].time_slots[i].hour, 2));
        }

        bind_form_submit_events('#mobile');
    },

    // This is only used by the mobile version
    build_day_selectors = function() {
        $('#mobile_previous').click(function(event) {
            event.preventDefault();
            if(day_offset > first_day_offset) {
                day_offset --;
                draw_day(day_offset);
                $('#mobile_next').attr('disabled', false);

                if(day_offset == first_day_offset) {
                    $(this).attr('disabled', true);
                }
            }

            persist_form($('input[name=time_slot]').attr('value'));
        });

        $('#mobile_next').click(function(event) {
            event.preventDefault();
            if(day_offset < calendar_grid.length - 2) {
                day_offset ++;
                draw_day(day_offset);
                $('#mobile_previous').attr('disabled', false);

                if(day_offset >= calendar_grid.length - 2) {
                    $(this).attr('disabled', true);
                }
            }

            persist_form($('input[name=time_slot]').attr('value'));
        });

        if(day_offset == first_day_offset) {
            $('#mobile_previous').attr('disabled', true);
        }

        if(day_offset >= calendar_grid.length - 2) {
            $('#mobile_next').attr('disabled', true);
        }
    },
    
    // This is only used by the desktop version
    week_offset = parseInt({{selected_week|default:0}}),

    // This is only used by the desktop version
    draw_week = function(_week_offset) {
        var month = new Array(6);
        for(var day=0; day < 6; day++){
           month[day] = calendar_grid[day + (_week_offset * 6)].month_name;
        }

        // Set header for day columns (3 columns cross day borders)
        if(month[2] == month[3]){
            $('#desktop div.calendar-month-label:eq(2)').html('<h2>' + month[2] + '</h2>');
        }else{
            $('#desktop div.calendar-month-label:eq(2)').html('&nbsp;');
        }

        if(month[0] == month[1] && month[0] != month[2]){
            $('#desktop div.calendar-month-label:eq(0)').html('<h2>' + month[0] + '</h2>');
        }else{
            if($('#desktop div.calendar-month-label:eq(2)').html() == '&nbsp;'){
                $('#desktop div.calendar-month-label:eq(0)').html('<h2>' + month[0] + '</h2>');
            }else{
                $('#desktop div.calendar-month-label:eq(0)').html('&nbsp;');
            }
        }

        if(month[4] != month[2]){
            $('#desktop div.calendar-month-label:eq(4)').html('<h2>' + month[4] + '</h2>');
        }else{
            $('#desktop div.calendar-month-label:eq(4)').html('&nbsp;');
        }

        // Day of month labels
        $('#desktop #date-labels-wrapper div.col-xs-2').remove();

        for(var day = 5; day >= 0; day --) {
            $('#desktop #date-labels-wrapper p:eq(0)').after('<div class="col-xs-2"><div class="calendar-date-wrapper"><div class="day-of-week">' + calendar_grid[day + (_week_offset * 6)].day_name + '</div>' + calendar_grid[day + (_week_offset * 6)].day_of_month + '</div></div>');
        }

        // Time slots
        $('#desktop .time-slot-row-wrapper').remove();

        for(var time_slot = 0; time_slot < calendar_grid[_week_offset * 6].time_slots.length; time_slot ++) {
            $('#desktop #date-labels-wrapper').after('<div class="row time-slot-row-wrapper">' + Array(7).join('<div class="col-xs-2"><div class="time-slot" data-time=""></div></div>') + '</div>');
        }

        for(var day = 0; day < 6; day ++) {
            for(var time_slot = 0; time_slot < calendar_grid[_week_offset * 6].time_slots.length; time_slot ++) {
                var selector = '#desktop div.time-slot-row-wrapper:eq(' + time_slot + ') div.col-xs-2:eq(' + day + ') div.time-slot'
                $(selector).html(calendar_grid[day + (_week_offset * 6)].time_slots[time_slot].label);
                $(selector).data('time', calendar_grid[day + (_week_offset * 6)].date + ' ' + pad(calendar_grid[day + (_week_offset * 6)].time_slots[time_slot].hour), 2);

                if(!calendar_grid[day + (_week_offset * 6)].time_slots[time_slot].available) {
                    $(selector).addClass('unavailable-slot').unbind('click');
                }
            }
        }

        bind_form_submit_events('#desktop');
    },

    // This is only used by the desktop version
    build_week_selectors = function() {
        $('#desktop_previous').click(function(event) {
            event.preventDefault();
            if(week_offset > 0) {
                week_offset --;
                draw_week(week_offset);
                $('#desktop_next').attr('disabled', false);

                if(week_offset == 0) {
                    $(this).attr('disabled', true);
                }
            }

            persist_form($('input[name=time_slot]').attr('value'));
        });

        $('#desktop_next').click(function(event) {
            event.preventDefault();
            if(week_offset < (calendar_grid.length / 6) - 1) {
                week_offset ++;
                draw_week(week_offset);
                $('#desktop_previous').attr('disabled', false);

                if(week_offset >= (calendar_grid.length / 6) - 1) {
                    $(this).attr('disabled', true);
                }
            }

            persist_form($('input[name=time_slot]').attr('value'));
        });

        if(week_offset == 0) {
            $('#desktop_previous').attr('disabled', true);
        }

        if(week_offset >= (calendar_grid.length / 6) - 1) {
            $('#desktop_next').attr('disabled', true);
        }
    },
    persist_form = function(selected_time) {
        $('.time-slot').each(function(index, item) {
            if($(item).data('time') == selected_time) {
                $(item).addClass("selected-slot");
                $(item).after('<img src="{% static "images/check.png" %}" width="39" height="39" alt="" class="selected-slot-checkmark">')
                $('input[name=time_slot]').attr('value', $(item).data('time'));
            }
        });
    };

    draw_week(week_offset);
    build_week_selectors();
    draw_day(day_offset);
    build_day_selectors();

    // If there is only a single week available then make sure the state of the right week selector is changed to inactive.
    if(calendar_grid.length <= 6) {
        $('#desktop .calendar-range-btn:eq(1)').attr('src', "{% static "images/arrow-right-inactive.png" %}");
    }

    {% if selected_date and selected_hour %}
        persist_form('{{selected_date}} {{selected_hour}}');
    {% endif %}
});
