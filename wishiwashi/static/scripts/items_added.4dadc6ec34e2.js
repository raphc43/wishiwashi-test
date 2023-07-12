$(document.body).ready(function() {
    $('.item-wrapper').each(function() {
        var url_bg = 'url("' + $(this).attr("data-src") + '")';
            if ($(this).css("background-image") == 'none') {
               $(this).css("background-image", url_bg);
            }
        });

    var min_free_delivery = 15;
    var calculate_grand_total = function() {
            var grand_total = 0.0;
            var for_free_delivery = 0.0;


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
        };

    $('.item-quantity-wrapper select').on('click touchend change blur tap', function() {
        if($(this).val() > 0){
            $(this).parent().addClass("has-success");
        }else{
            $(this).parent().removeClass("has-success");
        }
        calculate_grand_total();
    });

    if(total < min_free_delivery){
        calculate_grand_total();
    }else{
        $('#free-transit').show();
    }
});
