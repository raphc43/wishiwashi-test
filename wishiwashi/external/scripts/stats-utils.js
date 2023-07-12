function drop_down_monthly(url, select_id){
    var start_date = new Date("June 2015");
    var end_date = new Date();
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    var drop_down = '<select id = "' + select_id + '" class="form-control">';

    while (start_date <= end_date)
    {
        var selected = (start_date.getMonth() == end_date.getMonth() && 
                        start_date.getYear() == end_date.getYear()) ? 'selected="selected"' : '';
        var string_date = months[start_date.getMonth()] + " " + start_date.getFullYear();
        drop_down += "<option " + 
                     selected + 
                     " value='" + 
                     url + 
                     "?month=" + 
                     (start_date.getMonth() + 1) + 
                     "&year=" + 
                     start_date.getFullYear()+"'>" + 
                     string_date + 
                     "</option>";
        start_date.setMonth(start_date.getMonth() + 1);
    }

    drop_down += "</select>";
    return drop_down;
}

function drop_down_yearly(url, select_id){
    var start_date = new Date("2015");
    var end_date = new Date();

    var drop_down = '<select id = "' + select_id + '" class="form-control">';

    while (start_date <= end_date)
    {
        var selected = start_date.getYear() == end_date.getYear() ? 'selected="selected"' : '';
        var string_date = start_date.getFullYear();
        drop_down += "<option " + 
                     selected + 
                     " value='" + 
                     url + 
                     "?year=" + 
                     start_date.getFullYear()+"'>" + 
                     string_date + 
                     "</option>";
        start_date.setFullYear(start_date.getFullYear() + 1);
    }

    drop_down += "</select>";
    return drop_down;
}
