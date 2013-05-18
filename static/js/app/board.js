// stuff for visualizing the board

define( ['knockout-2.2.1', 'd3'], function (ko, d3) {

    var draw_board = function (board, coord) {
        board.append("svg:image")
            .attr("xlink:href", "/static/images/goban_whole4_small.jpg")
            .attr("x", "0")
            .attr("y", "0")
            .attr("width", "100%")
            .attr("height", "100%");

        // the axiscoorddata gives the y coordinates for horizontal lines
        var axiscoorddata = d3.range(0, 19, 1);

        // Using the axiscoorddata to generate vertical lines.
        board.selectAll("line.vertical")
            .data(axiscoorddata)
            .enter().append("svg:line")
            .attr("x1", coord)
            .attr("y1", coord(0))
            .attr("x2", coord)
            .attr("y2", coord(18))
            .style("stroke", "black");

        board.selectAll("line.horizontal")
            .data(axiscoorddata)
            .enter().append("svg:line")
            .attr("x1", coord(0))
            .attr("y1", coord)
            .attr("x2", coord(18))
            .attr("y2", coord)
            .style("stroke", "black");

        // Draw the dots
        board.selectAll("circle")
            .data([[3, 3],  [9, 3],  [15, 3],
                   [3, 9],  [9, 9],  [15, 9],
                   [3, 15], [9, 15], [15, 15]]).enter()
            .append("circle").attr("fill", "black")
            .attr("r", 2)
            .attr("cx", function (d) {return coord(d[0]);})
            .attr("cy", function (d) {return coord(d[1]);});
    };

    var create_shadows = function (defs, spacing) {

        // create filter with id #drop-shadow
        // height=130% so that the shadow is not clipped
        var filter = defs.append("filter")
                .attr("id", "drop-shadow");
                // .attr("height", "100")
                // .attr("width", "100");
        // .append("feColorMatrix")
        // .attr("type", "matrix")
        // .attr("values", "0 0 0 0   0 " +
        //                 "0 0 0 0.9 0 " +
        //                 "0 0 0 0.9 0 " +
        //                 "0 0 0 0.5 0")

        // SourceAlpha refers to opacity of graphic that this filter will be applied to
        // convolve that with a Gaussian
        filter.append("feGaussianBlur")
            .attr("in", "SourceAlpha")
            .attr("stdDeviation", spacing/15);
            //.attr("result", "shadow");

        // translate output of Gaussian blur to the right and downwards
        filter.append("feOffset")
            //.attr("in", "shadow")
            .attr("dx", spacing/20)
            .attr("dy", spacing/10);

        // Set the alpha of the shadows
        filter.append("feComponentTransfer")
            .attr("result", "shadow")
            .append("feFuncA")
            .attr("type", "linear")
            .attr("slope", 0.6);

        // Merge the stones and the shadows
        var feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode")
            .attr("in", "shadow");
        feMerge.append("feMergeNode")
            .attr("in", "SourceGraphic");

    };

    var create_gradients = function (defs) {
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
    };


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
                //.attr("viewbox", "0 0 18 18")
                .attr("preserveAspectRatio", "xMidYMid meet");
        self.resize();
        var margin = 0,
            spacing = self.width / size;
        var coord = function (pos) {
            return 0.5 + Math.round(pos * spacing + spacing/2);
        };

        self.board = board;
        draw_board(board, coord);

        var stones = board.append("g");  // SVG group to contain all stones

        var defs = board.append("svg:defs");

        create_shadows(defs, spacing);
        create_gradients(defs);

        // The shadow must be added to the group of stones as a whole, because it
        // must be drawn beneath all of them
        stones.style("filter", "url(#drop-shadow)");

        var moveline = d3.svg.line()
                .defined(function (m) {return m.position;})
                .x(function(m) { return coord(m.position[0]); })
                .y(function(m) { return coord(m.position[1]); })
                .interpolate("cardinal");
        var path = board.append("path")
                .style("stroke", "rgba(0,100,255,0.7)")
                .style("stroke-width", 2)
                .style("fill", "none")
                .style("pointer-events", "none");

        var marker = board.append("circle") // last stone marker
                .attr("id", "marker")
                .attr("r", spacing / 4)
                .attr("fill", "rgba(0,0,0,0)")
                .style("stroke", "red")
                .style("stroke-width", spacing / 15)
                .style("pointer-events", "none");

        var stone_mouseover = function (m, i) {
            var s = d3.select(this);
            board.append("text").text(m.n + 1)
                .attr("id", "number" + m.n)
                .attr("dominant-baseline", "central")
                .attr("text-anchor", "middle")
                .attr("x", coord(m.position[0]))
                .attr("y", coord(m.position[1]))
                .style("fill", m.n % 2 === 0 ? "white" : "black")
                .style("pointer-events", "none");
            //s.attr("r", s.attr("r") * 1.1);
        };
        var stone_mouseout = function (m, i) {
            var s = d3.select(this);
            board.select("#number" + m.n).remove();
            //s.attr("depth", 10).attr("r", s.attr("r") / 1.1);
        };

        // Automatically handle model changes
        ko.computed(function() {

            var current_move = model.current_move();
            var captures = model.captures();
            var moves = model.moves().slice(0, current_move)
                    // Filter out moves without position (pass) and captured stones
                    .filter(function (m) {return (m.position &&
                                                  captures[0].indexOf(m.n) === -1 &&
                                                  captures[1].indexOf(m.n) === -1);});

            var last_move = moves.slice(-1)[0];
            var stone = stones.selectAll("circle").data(
                moves, function(m) { return m.n; }); // need to key the moves on number,
                                                     // to be able to remove captures
            stone  // stone appearance
                .attr("r", 0.95 * spacing/2)
                .style("fill", function(m) {
                    return "url(#" + ["black", "white"][m.player] + "gradient)";})
                .attr("cx", function(m) {return coord(m.position[0]);})
                .attr("cy", function(m) {return coord(m.position[1]);})
                .on("mouseover", stone_mouseover)
                .on("mouseout", stone_mouseout);

            stone.enter().append("circle");  // Update stones
            stone.exit().remove();  // Remove stones that aren't present anymore

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