var WeekDayBox = React.createClass({displayName: "WeekDayBox",
  loadDataFromServer: function() {
    $.ajax({
      url: this.props.url,
      dataType: 'json',
      cache: false,
      success: function(data) {
        this.setState({data: data});
      }.bind(this),
      error: function(xhr, status, err) {
        console.error(this.props.url, status, err.toString());
      }.bind(this)
    });
  },
  getInitialState: function() {
    return {data: []};
  },
  componentDidMount: function() {
    this.loadDataFromServer();
    setInterval(this.loadDataFromServer, this.props.pollInterval);
  },
  render: function() {
    var rows = [];
    for(i = 0, row=0; i < this.props.hours.length; i++, row++){
        rows.push(React.createElement(SlotRow, {data: this.state.data, key: 'row' + i, days: this.props.days, row: row}))
    }
    return (
      React.createElement("div", {className: "container"}, 
      React.createElement(WeekDays, {days: this.props.days}), 
      rows
      )
    );
  }
});

var SlotEntry = React.createClass({displayName: "SlotEntry",
  render: function() {
      var day = this.props.day;
      var row = this.props.row;
      return (
            React.createElement("div", null, 
            this.props.entries.map(function(entry, index){
                var style = {color: 'white', fontWeight: '800', padding: '1px', margin: '1px'};
                var link = {color: 'white'};
                var url = "/vendors/order/"+ entry.pk;
                if(entry.collect){
                    var pre_text = "Collect: ";
                    style.backgroundColor = '#FF8300';
                    // RECEIVED_BY_VENDOR = 2 OR DELIVERED_BACK_TO_CUSTOMER = 6
                    if(entry.status === 2 || entry.status === 6 ){
                        style.opacity = 0.5;
                    }
                }else{
                    var pre_text = "Deliver: ";
                    style.backgroundColor = '#06799F';
                    // DELIVERED_BACK_TO_CUSTOMER = 6
                    if(entry.status === 6){
                        style.opacity = 0.5;
                    }
                }
                return (React.createElement("div", {key: 'e5' + row + day + index, style: style, className: "row"}, 
                            React.createElement("div", {className: "col-xs-12"}, React.createElement("a", {target: "_blank", style: link, href: url}, entry.order)), 
                            React.createElement("div", {className: "col-xs-12"}, pre_text, " ", entry.postcode), 
                            React.createElement("div", {className: "col-xs-12"}, React.createElement("small", null, entry.status_display))
                        ));
            })
            )
      );
  }
});

var SlotEmpty = React.createClass({displayName: "SlotEmpty",
  render: function() {
    var start = this.props.row + 8;
    var end = start + 1;
    var slot = start + '-' + end;
    var style = {padding: '5px'};

    if(this.props.day == 5 && this.props.row > 8){
        // unavailable hours on saturday
        style.backgroundColor = '#CCCCCC';
        style.color = 'silver';
    }else{
        style.backgroundColor = '#00BB3F';
        style.color = '#ffffff';
        style.fontWeight = '800';
    }

    return React.createElement("p", {style: style}, slot);
  }
});


var Slot = React.createClass({displayName: "Slot",
  render: function() {
    var empty = true;
    var populateSlot = function(row, day, data){
        if(typeof data[row] !== 'undefined' && typeof data[row][day] !== 'undefined' && data[row][day].length > 0) {
            empty = false;
            return React.createElement(SlotEntry, {row: row, day: day, key: 'entry' + row + ',' + day, entries: data[row][day]});
        } else {
            return React.createElement(SlotEmpty, {row: row, day: day})
        }
    };
    return (
        React.createElement("div", {key: this.props.row + ',' + this.props.id, className: "col-xs-2 text-center"}, 
        populateSlot(this.props.row, this.props.id, this.props.data)
        )
    );
  }
});

var SlotRow = React.createClass({displayName: "SlotRow",
  render: function() {
    var row = this.props.row;
    var data = this.props.data;
    return (
        React.createElement("div", {className: "row"}, 
        React.createElement("hr", null), 
        this.props.days.map(function(day) { 
            return React.createElement(Slot, {key: 'slot-' + day.key + ',' + row, id: day.key, row: row, data: data})
        })
        )
    );
  }
});


var WeekDays = React.createClass({displayName: "WeekDays",
  render: function() {
   return (
        React.createElement("div", {className: "row"}, 
        this.props.days.map(function(day) { 
            return React.createElement("div", {key: day.key, className: "col-xs-2 text-center"}, React.createElement("h1", null, day.display));
        })
        )
    );
  }
});


React.render(
  React.createElement(WeekDayBox, {url: URL, pollInterval: POLL_INTERVAL, days: DAYS, hours: HOURS}),
  document.getElementById('content')
);
