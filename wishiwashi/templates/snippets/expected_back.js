$(document).ready(function(){
    $(".expected_back_confirm").submit(function(event) {
        event.preventDefault();
        var values = $(this).serializeArray();
        var id = values[1].value;
        $.post("{% url 'vendors:expected_back_clean_only_confirm' %}", $(this).serialize(), function(data){
                $('#desktop_' + id).addClass("btn-success").html("Confirmed");
                $('#desktop_' + id).removeClass("btn-danger").html("Confirmed");
                $('#desktop_' + id).attr('disabled','disabled');
                $('#mobile_' + id).addClass("btn-success").html("Confirmed");
                $('#mobile_' + id).removeClass("btn-danger").html("Confirmed");
                $('#mobile_' + id).attr('disabled','disabled');
            }, "json")
            .fail(function(jqXHR, textStatus, errorThrown){
                var responseText = jQuery.parseJSON(jqXHR.responseText);
                $('.notify').addClass("alert-danger").html("Error: " + responseText.error);
            })
    });
});

