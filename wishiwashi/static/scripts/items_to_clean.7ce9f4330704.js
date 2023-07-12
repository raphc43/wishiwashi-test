$(document.body).ready(function() {
    var min_free_delivery = 15;
    var toggle_visible_items = function(_category) {
            $('.item-wrapper').not('[data-category=' + _category + ']').hide();
            $('.item-wrapper[data-category=' + _category + ']').each(function() {
                var url_bg = 'url("' + $(this).attr("data-src") + '")';
                if ($(this).css("background-image") == 'none') {
                    $(this).css("background-image", url_bg);
                }
            });
            $('.item-wrapper[data-category=' + _category + ']').fadeIn(500)
            $('input[name='+selected_category+']').attr('value', _category);
        },
        set_click_category_event = function() {
            $('.nav-item-wrapper').click(function(event) {
                var category = $(this).data('category');

                $('.nav-item-wrapper').removeClass('selected');
                $(this).addClass('selected');
                toggle_visible_items(category);
                $('select#category-picker').find('option[value=' + category + ']').attr("selected", true);
            });

            $('.nav-item-label, .nav-item-amount').click(function(event) {
                var category = $(this).parent().data('category');

                $('.nav-item-wrapper').removeClass('selected');
                $(this).parent().addClass('selected');
                toggle_visible_items(category);
                $('select#category-picker').find('option[value=' + category + ']').attr("selected", true);
            });


            $('select#category-picker').bind('change blur click tap', function() {
                var category = $('option:selected', $(this)).val();

                $('.nav-item-wrapper').removeClass('selected');
                $('.nav-item-wrapper[data-category=' + category + ']').addClass('selected');
                toggle_visible_items(category);
            });
        }(),
        calculate_grand_total = function() {
            var grand_total = 0.0;
            var for_free_delivery = 0.0;

            // Setting this to 0 again just in case the above declaration is
            // only called when the page is loaded and not when this is run
            // each time.
            grand_total = 0.0;

            $('.item-quantity-wrapper select option:selected').each(function(item) {
                grand_total += $(this).parent().parent().parent().data('price') * 
                               parseInt($(this).val());
            });

            grand_total = parseFloat(Math.round(grand_total * 100) / 100).toFixed(2);

            $('#basket-monetary-amount').html(grand_total);

            if(grand_total < min_free_delivery){
                for_free_delivery = parseFloat(Math.round((min_free_delivery - grand_total) * 100) / 100).toFixed(2);
                $('#transit .price').html("&pound;" + for_free_delivery);
                $('#transit').show();
                $('#free-transit').hide();
            }else{
                $('#transit .price').html("&pound;0.00");
                $('#transit').hide();
                $('#free-transit').show();
            }

        },
        calculate_initial_category_counts = function() {
            $('.nav-item-wrapper').each(function(count, category) {
                var category = $(category).data('category'),
                    total = 0;

                $('.item-wrapper[data-category=' + category + '] select').each(function(item) {
                    total += parseInt($('option:selected', $(this)).val());
                });

                $('.nav-item-wrapper[data-category=' + category + '] .nav-item-amount').html(total);
            });
        };

    toggle_visible_items(selected_category);
    $('.nav-item-wrapper[data-category='+selected_category+']').addClass('selected');
    $('select#category-picker').find('option[value='+selected_category+']').attr("selected", true);

    $('.item-quantity-wrapper select').on('click touchend change blur tap', function() {
        var category = $(this).parent().parent().data('category'),
            total = 0;

        if($(this).val() > 0){
            $(this).parent().addClass("has-success");
        }else{
            $(this).parent().removeClass("has-success");
        }

        $('.item-wrapper[data-category=' + category + '] select').each(function(item) {
            total += parseInt($('option:selected', $(this)).val());
        });

        $('.nav-item-wrapper[data-category=' + category + '] .nav-item-amount').html(total);

        $('select[name=' + $(this).attr('name') + ']').find('option[value=' + $(this).val() + ']').attr("selected", true);

        calculate_grand_total();
    });

    // Form persistence
    calculate_grand_total();
    calculate_initial_category_counts();
});

