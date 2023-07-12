function updateHeatmapDaily(url){
      d3.select("#heatmap_chart svg").remove();

      var margin = { top: 50, right: 0, bottom: 100, left: 30 },
          width = 1150 - margin.left - margin.right,
          height = 470 - margin.top - margin.bottom,
          gridSize = Math.floor(width / 24),
          legendElementWidth = 120,
          buckets = 9,
          colors = ["#ffffd9","#edf8b1","#c7e9b4","#7fcdbb","#41b6c4","#1d91c0","#225ea8","#253494","#081d58"], // alternatively colorbrewer.YlGnBu[9]
          days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
          times = ["1-2", "2-3", "3-4", "4-5", "5-6", "6-7", "7-8", "8-9", "9-10", "10-11", "11-12", "12-13", "13-14", "14-15", "15-16", "16-17", "17-18", "18-19", "19-20", "20-12", "21-22", "22-23", "23-24", "24-"];

      var svg = d3.select("#heatmap_chart").append("svg")
          .attr("width", width + margin.left + margin.right)
          .attr("height", height + margin.top + margin.bottom)
          .append("g")
          .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      var dayLabels = svg.selectAll(".dayLabel")
          .data(days)
          .enter().append("text")
            .text(function (d) { return d; })
            .attr("x", 0)
            .attr("y", function (d, i) { return i * gridSize; })
            .style("text-anchor", "end")
            .attr("transform", "translate(-6," + gridSize / 1.5 + ")")
            .attr("class", function (d, i) { return ((i >= 0 && i <= 4) ? "dayLabel mono axis axis-workweek" : "dayLabel mono axis"); });

      var timeLabels = svg.selectAll(".timeLabel")
          .data(times)
          .enter().append("text")
            .text(function(d) { return d; })
            .attr("x", function(d, i) { return i * gridSize; })
            .attr("y", 0)
            .style("text-anchor", "middle")
            .attr("transform", "translate(" + gridSize / 2 + ", -6)")
            .attr("class", function(d, i) { return ((i >= 7 && i <= 16) ? "timeLabel mono axis axis-worktime" : "timeLabel mono axis"); });

      var heatmapChart = function(tsvFile) {
        d3.tsv(tsvFile,
        function(d) {
          return {
            day: +d.day,
            hour: +d.hour,
            value: +d.value
          };
        },
        function(error, data) {
          var colorScale = d3.scale.quantile()
              .domain([0, buckets - 1, d3.max(data, function (d) { return d.value; })])
              .range(colors);

          var cards = svg.selectAll(".hour")
              .data(data, function(d) {return d.day+':'+d.hour;});

          cards.append("title");

          cards.enter().append("rect")
              .attr("x", function(d) { return (d.hour - 1) * gridSize; })
              .attr("y", function(d) { return (d.day - 1) * gridSize; })
              .attr("rx", 4)
              .attr("ry", 4)
              .attr("class", "hour bordered")
              .attr("width", gridSize)
              .attr("height", gridSize)
              .style("fill", colors[0]);

          cards.transition().duration(1000)
              .style("fill", function(d) { return colorScale(d.value); });

          cards.select("title").text(function(d) { return d.value; });
          cards.exit().remove();

          var legend = svg.selectAll(".legend")
              .data([0].concat(colorScale.quantiles()), function(d) { return d; });

          legend.enter().append("g")
              .attr("class", "legend");

          legend.append("rect")
            .attr("x", function(d, i) { return legendElementWidth * i; })
            .attr("y", height)
            .attr("width", legendElementWidth)
            .attr("height", gridSize / 2)
            .style("fill", function(d, i) { return colors[i]; });

          legend.append("text")
            .attr("class", "mono")
            .text(function(d) { return "≥ " + Math.round(d); })
            .attr("x", function(d, i) { return legendElementWidth * i; })
            .attr("y", height + gridSize);

          legend.exit().remove();
        });  
      };

      heatmapChart(url);
}
// handle on click event
d3.select('#heatmap_monthly_opts')
  .on('change', function() {
    var url = d3.select(this).property('value');
    if (document.getElementById("heatmap_pickups").checked){
        url = url + "&pickups=1";
    }else{
        url = url + "&pickups=";
    }
    if (document.getElementById("heatmap_deliveries").checked){
        url = url + "&deliveries=1";
    }else{
        url = url + "&deliveries=";
    }
    updateHeatmapDaily(url);
});

d3.select('#heatmap_pickups')
  .on('change', function() {
    var url = d3.select("#heatmap_monthly_opts").property('value');
    if(this.checked){
        url = url + "&pickups=1";
    }else{
        url = url + "&pickups=";
    }
    if (document.getElementById("heatmap_deliveries").checked){
        url = url + "&deliveries=1";
    }else{
        url = url + "&deliveries=";
    }
    updateHeatmapDaily(url);
});
d3.select('#heatmap_deliveries')
  .on('change', function() {
    var url = d3.select("#heatmap_monthly_opts").property('value');
    if(this.checked){
        url = url + "&deliveries=1";
    }else{
        url = url + "&deliveries=";
    }
    if (document.getElementById("heatmap_pickups").checked){
        url = url + "&pickups=1";
    }else{
        url = url + "&pickups=";
    }
    updateHeatmapDaily(url);
});


