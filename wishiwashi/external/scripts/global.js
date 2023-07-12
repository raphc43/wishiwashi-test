$(document.body).ready(function() {
    setTimeout(function() {
        $("#top-desktop-login-bar").slideDown();
    }, 1500);

    $("input.form-element-error, textarea.form-element-error").bind('touchstart mousedown change focus', function(event){
        $(this).removeClass("form-element-error");
    });

    if($.browser.msie && parseInt($.browser.version, 10) === 8) {
        $("input[type=text]").attr("placeholder", "");
    }

    $('div.menu-trigger').click(function(event){
        if($('body').hasClass('menu-active')) {
            $('body').removeClass('menu-active');
        } else {
            $('body').addClass('menu-active');
        }
    });
});
