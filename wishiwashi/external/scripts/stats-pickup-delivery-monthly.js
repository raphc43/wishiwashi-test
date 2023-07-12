function updatePickupDeliveryMonthly(url, div_id){
    d3.select(div_id + " svg").remove();

    var margin = {top: 40, right: 20, bottom: 30, left: 40},
        width = 1150 - margin.left - margin.right,
        height = 400 - margin.top - margin.bottom;

    var x0 = d3.scale.ordinal()
        .rangeRoundBands([0, width], .1);

    var x1 = d3.scale.ordinal();

    var y = d3.scale.linear()
        .range([height, 0]);

    var color = d3.scale.ordinal()
        .range(["#228B22", "#8a89a6"]);

    var xAxis = d3.svg.axis()
        .scale(x0)
        .orient("bottom");

    var yAxis = d3.svg.axis()
        .scale(y)
        .orient("left")
        .tickFormat(d3.format("1s"));

    var tip = d3.tip()
      .attr('class', 'd3-tip')
      .offset([-10, 0])
      .html(function(d) {
        return "<strong>" + d.name + ":</strong> <span style='color:red'>" + d.value+ "</span>";
      });

    var svg = d3.select(div_id).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    svg.call(tip);

    d3.tsv(url, function(error, data) {
      if (error) throw error;

      var orderTypes = d3.keys(data[0]).filter(function(key) { return key !== "day"; });

      data.forEach(function(d) {
        d.orders = orderTypes.map(function(name) { return {name: name, value: +d[name]}; });
      });

      x0.domain(data.map(function(d) { return d.day; }));
      x1.domain(orderTypes).rangeRoundBands([0, x0.rangeBand()]);
      y.domain([0, d3.max(data, function(d) { return d3.max(d.orders, function(d) { return d.value; }); })]);

      svg.append("g")
          .attr("class", "x axis")
          .attr("transform", "translate(0," + height + ")")
          .call(xAxis);

      svg.append("g")
          .attr("class", "y axis")
          .call(yAxis)
          .append("text")
          .attr("transform", "rotate(-90)")
          .attr("y", 6)
          .attr("dy", ".71em")
          .style("text-anchor", "end")
          .text("Frequency");

      var state = svg.selectAll(".day")
          .data(data)
          .enter().append("g")
          .attr("class", "day")
          .attr("transform", function(d) { return "translate(" + x0(d.day) + ",0)"; });

      state.selectAll("rect")
          .data(function(d) { return d.orders; })
          .enter().append("rect")
          .attr("width", x1.rangeBand())
          .attr("x", function(d) { return x1(d.name); })
          .attr("y", function(d) { return y(d.value); })
          .attr("height", function(d) { return height - y(d.value); })
          .style("fill", function(d) { return color(d.name); })
          .on('mouseover', tip.show)
          .on('mouseout', tip.hide);

      var legend = svg.selectAll(".legend")
          .data(orderTypes.slice().reverse())
          .enter().append("g")
          .attr("class", "legend")
          .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

      legend.append("rect")
          .attr("x", width - 18)
          .attr("width", 18)
          .attr("height", 18)
          .style("fill", color);

      legend.append("text")
          .attr("x", width - 24)
          .attr("y", 9)
          .attr("dy", ".35em")
          .style("text-anchor", "end")
          .text(function(d) { return d; });

    });
}
