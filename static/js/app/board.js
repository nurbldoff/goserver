// stuff for visualizing the board

define( ['knockout-2.2.1', 'd3'], function (ko, d3) {

    return function (model, element, size) {

        var self = this;

        self.resize = function () {
            var width = $(element).width();
            board.attr("width", width)
                .attr("height", width);
            self.width = self.height = width;
        };

        // FIXME: This isn't very nice, we don't redraw the board just clip it.
        $(window).on("resize", self.resize);

        self.element = d3.select(element);
        var board = self.element.append("svg:svg")
                .attr("id", "board")
                .attr("viewbox", "0 0 100 100")
                .attr("preserveAspectRatio", "xMidYMid meet");
        self.resize();
        var margin = 0,
            spacing = self.width / size;

        self.board = board;

        var coord = function (pos) {
            return 0.5 + Math.round(pos * spacing + spacing/2);
        };

        board.append("svg:image")
            .attr("xlink:href", "/static/images/goban_whole4_small.jpg")
            .attr("x", "0")
            .attr("y", "0")
            .attr("width", self.width)
            .attr("height", self.height);

        // the yaxiscoorddata gives the y coordinates for horizontal lines
        var yaxiscoorddata = d3.range(spacing/2, self.height, spacing);

        // the xaxiscoorddata gives the x coordinates for vertical lines
        var xaxiscoorddata = d3.range(spacing/2, self.width, spacing);

        // Using the xaxiscoorddata to generate vertical lines.
        board.selectAll("line.vertical")
            .data(xaxiscoorddata)
            .enter().append("svg:line")
            .attr("x1", function(d){return 0.5 + Math.round(d);})
            .attr("y1", Math.floor(spacing/2))
            .attr("x2", function(d){return 0.5 + Math.round(d);})
            .attr("y2", Math.ceil(1 + self.height - spacing/2))
            .style("stroke", "rgb(0,0,0)")
            .style("stroke-width", 1.0);

        // Using the yaxiscoorddata to generate horizontal lines.
        board.selectAll("line.horizontal")
            .data(yaxiscoorddata)
            .enter().append("svg:line")
            .attr("x1", Math.floor(spacing/2))
            .attr("y1", function(d){return 0.5 + Math.round(d);})
            .attr("x2", Math.ceil(1 + self.width - spacing/2))
            .attr("y2", function(d){return 0.5 + Math.round(d);})
            .style("stroke", "rgb(0,0,0)")
            .style("stroke-width", 1.0);

        // Draw the dots
        board.selectAll("circle")
            .data([[3, 3],  [9, 3],  [15, 3],
                   [3, 9],  [9, 9],  [15, 9],
                   [3, 15], [9, 15], [15, 15]]).enter()
            .append("circle").attr("fill", "black")
            .attr("r", spacing/15)
            .attr("cx", function (d) {return coord(d[0]);})
            .attr("cy", function (d) {return coord(d[1]);});

        // board.on("click", function () {
        //     var pos = [Math.floor(d3.event.x / (width/size)),
        //                Math.floor(d3.event.y / (height/size))];
        //     scope.make_move(pos);
        // });

        var stonegroup = board.append("g");
        var defs = board.append("svg:defs");
        // create filter with id #drop-shadow
        // height=130% so that the shadow is not clipped
        var filter = defs.append("filter")
                .attr("id", "drop-shadow")
                .attr("height", "120%")
                .attr("width", "120%");
        // .append("feColorMatrix")
        // .attr("type", "matrix")
        // .attr("values", "0 0 0 0   0 " +
        //                 "0 0 0 0.9 0 " +
        //                 "0 0 0 0.9 0 " +
        //                 "0 0 0 0.5 0")

        // SourceAlpha refers to opacity of graphic that this filter will be applied to
        // convolve that with a Gaussian and store result in blur
        filter.append("feGaussianBlur")
            .attr("in", "SourceAlpha")
            .attr("stdDeviation", spacing/15)
            .attr("result", "shadow");

        // translate output of Gaussian blur to the right and downwards
        // store result in offsetBlur
        filter.append("feOffset")
            .attr("in", "shadow")
            .attr("dx", spacing/20)
            .attr("dy", spacing/10);

        // Set the alpha of the shadows
        filter.append("feComponentTransfer")
            .attr("result", "alphaShadow")
            .append("feFuncA")
            .attr("type", "linear")
            .attr("slope", 0.6);

        // Merge the stones and the shadows
        var feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode")
            .attr("in", "alphaShadow");
        feMerge.append("feMergeNode")
            .attr("in", "SourceGraphic");

        // The shadow must be added to the group of stones as a whole, because it
        // must be drawn beneath all of them
        stonegroup.style("filter", "url(#drop-shadow)");

        // Gradient definitions
        var whitegradient = defs.append("svg:radialGradient")
                .attr("id", "whitegradient")
                .attr("r", 0.9)
                .attr("fx", 0.4).attr("fy", 0.2)
                .attr("cx", 0.5).attr("cy", 0.3);

        whitegradient.append("svg:stop")
            .attr("offset", "0%")
            .attr("stop-color", "#fff");

        whitegradient.append("svg:stop")
            .attr("offset", "100%")
            .attr("stop-color", "#999");

        var blackgradient = defs.append("svg:radialGradient")
                .attr("id", "blackgradient")
                .attr("r", 0.9)
                .attr("fx", 0.4).attr("fy", 0.2)
                .attr("cx", 0.5).attr("cy", 0.3);

        blackgradient.append("svg:stop")
            .attr("offset", "0%")
            .attr("stop-color", "#444");

        blackgradient.append("svg:stop")
            .attr("offset", "100%")
            .attr("stop-color", "#000");

        var moveline = d3.svg.line()
                .defined(function (m) {return m.position})
                .x(function(m) { return coord(m.position[0]); })
                .y(function(m) { return coord(m.position[1]); })
                .interpolate("cardinal");
        var path = board.append("path")
                .style("stroke", "blue")
                .style("stroke-width", 2)
                .style("fill", "none");

        var marker = board.append("circle")
                .attr("r", spacing / 4)
                .attr("fill", "rgba(0,0,0,0)")
                .style("stroke", "red")
                .style("stroke-width", spacing / 15);
        //.style("display", "none");

        // whenever things change, execute this
        ko.computed(function() {
            //board.selectAll('*').remove();

            var current_move = model.current_move();
            var captures = model.captures();
            var moves = model.moves().slice(0, current_move)
                    // Filter out moves without position (pass) and captured stones
                    .filter(function (m) {return (m.position &&
                                                  captures[0].indexOf(m.n) === -1 &&
                                                  captures[1].indexOf(m.n) === -1);});

            var stones = stonegroup.selectAll("circle").data(moves,
                                                             // need to key the moves on
                                                             // number, to be able to remove
                                                             // captures.
                                                             function(m) { return m.n; });

            var last_move = moves.slice(-1)[0];
            stones.style("stroke", null)
                .on("mouseover", function () {
                    console.log(d3.select(this).text());
                });

            // Update stones
            stones.enter().append("circle")
                .attr("r", 0.95 * spacing/2)
                .style("fill", function(m) {
                    return "url(#" + ["black", "white"][m.player] + "gradient)";})
                .attr("cx", function(m) {return coord(m.position[0]);})
                .attr("cy", function(m) {return coord(m.position[1]);})
                .text(function (m, i) {return m.n;});

            // Remove stones that aren't present anymore
            stones.exit().remove();

            // last move marker (a bit buggy, maybe do it in a more "d3" way?)
            if (moves.length > 0 && last_move && last_move.position) {
                marker
                    .attr("cx", coord(last_move.position[0]))
                    .attr("cy", coord(last_move.position[1]));
            }
        });

        ko.computed(function () {
            if (model.show_path()) {
                console.log("path enabled");
                path.attr("d", moveline(model.moves.slice(0, model.current_move())));
            } else {
                path.attr("d", moveline([]));
            }
        });

    };
});