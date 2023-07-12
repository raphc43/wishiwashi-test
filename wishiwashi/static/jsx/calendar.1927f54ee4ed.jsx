var WeekDayBox = React.createClass({
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
        rows.push(<SlotRow data={this.state.data} key={'row' + i} days={this.props.days} row={row}/>)
    }
    return (
      <div className="container">
      <WeekDays days={this.props.days} />
      {rows}
      </div>
    );
  }
});

var SlotEntry = React.createClass({
  render: function() {
      var day = this.props.day;
      var row = this.props.row;
      return (
            <div>
            {this.props.entries.map(function(entry, index){
                var style = {color: 'white', fontWeight: '800', padding: '1px', margin: '1px'};
                if(entry.collect){
                    style.backgroundColor = '#FF8300';
                }else{
                    style.backgroundColor = '#06799F';
                }
                return (<div key={'e5' + row + day + index} style={style} className="row">
                            <div className="col-xs-12">{entry.order}</div>
                            <div className="col-xs-12"><small>{entry.postcode}</small></div>
                        </div>);
            })}
            </div>
      );
  }
});

var SlotEmpty = React.createClass({
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

    return <p style={style}>{slot}</p>;
  }
});


var Slot = React.createClass({
  render: function() {
    var empty = true;
    var populateSlot = function(row, day, data){
        if(typeof data[row] !== 'undefined' && typeof data[row][day] !== 'undefined' && data[row][day] !== '') {
            empty = false;
            return <SlotEntry row={row} day={day} key={'entry' + row + ',' + day}  entries={data[row][day]} />;
        } else {
            return <SlotEmpty row={row} day={day}/>
        }
    };
    return (
        <div key={this.props.row + ',' + this.props.id} className="col-xs-2 text-center success">
        {populateSlot(this.props.row, this.props.id, this.props.data)}
        </div>
    );
  }
});

var SlotRow = React.createClass({
  render: function() {
    var row = this.props.row;
    var data = this.props.data;
    return (
        <div className="row">
        <hr/>
        {this.props.days.map(function(day) { 
            return <Slot key={'slot-' + day.key + ',' + row } id={day.key} row={row} data={data} />
        })}
        </div>
    );
  }
});


var WeekDays = React.createClass({
  render: function() {
   return (
        <div className="row">
        {this.props.days.map(function(day) { 
            return <div key={day.key} className="col-xs-2 text-center"><h1>{day.display}</h1></div>;
        })} 
        </div>
    );
  }
});


React.render(
  <WeekDayBox url={URL} pollInterval={2000} days={DAYS} hours={HOURS} />,
  document.getElementById('content')
);
