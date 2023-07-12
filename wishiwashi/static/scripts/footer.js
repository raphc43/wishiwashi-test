/* This JS file is only used for the landing page */
$(document.body).ready(function() {
    var positionFooter = function() {
        /* jQuery won't need this helper class, it's only for non-JS driven pages*/
        $("footer.desktop").removeClass("non-fixed");

        if(parseInt($(document).height(), 10) < 606) {
            $("footer.desktop").css("position", "relative");
        } else {
            $("footer.desktop").css("position", "absolute");
        }
    }

    positionFooter();

    $(window).resize(function() {
        positionFooter();
    });
});
