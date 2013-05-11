// Directive for visualizing the board

angular.module('BoardExternal', [])
    .directive('gobanVisualization', function ($scope) {

    var margin = 20,
        spacing = 30,
        width = 19 * spacing + 1,
        height = 19 * spacing + 1,
        color = d3.interpolateRgb("#f77", "#77f");

    return {
        restrict: 'E', // the directive can be invoked only by using
        // <my-directive> tag in the template
        // scope: { // attributes bound to the scope of the directive
        //     moves: '=',
        //     move: '=',
        //     make_move: '='
        // },

        controller: function ($scope) {

        },

        link: function (scope, element, attrs) {
            // initialization, done once per directive tag in template.
            var board = d3.select(element[0])
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);

            board.append("svg:image")
                .attr("xlink:href", "/static/images/goban_whole4_small.jpg")
                .attr("x", "0")
                .attr("y", "0")
                .attr("width", width)
                .attr("height", height);


            // the yaxiscoorddata gives the y coordinates
            // for horizontal lines
            var yaxiscoorddata = d3.range(spacing/2, height, spacing);

            // the xaxiscoorddata gives the x coordinates
            // for vertical lines
            var xaxiscoorddata = d3.range(spacing/2, width, spacing);

            // Using the xaxiscoorddata to generate vertical lines.
            board.selectAll("line.vertical")
                .data(xaxiscoorddata)
                .enter().append("svg:line")
                .attr("x1", function(d){return 0.5 + d;})
                .attr("y1", spacing/2)
                .attr("x2", function(d){return 0.5 + d;})
                .attr("y2", height - spacing/2)
                .style("stroke", "rgb(0,0,0)")
                .style("stroke-width", 1);

            // Using the yaxiscoorddata to generate horizontal lines.
            board.selectAll("line.horizontal")
                .data(yaxiscoorddata)
                .enter().append("svg:line")
                .attr("x1", spacing/2)
                .attr("y1", function(d){return 0.5 + d;})
                .attr("x2", width - spacing/2)
                .attr("y2", function(d){return 0.5 + d;})
                .style("stroke", "rgb(0,0,0)")
                .style("stroke-width", 1);

            board.on("click", function () {
                var pos = [Math.floor(d3.event.x / (width/19)),
                           Math.floor(d3.event.y / (height/19))];
                scope.make_move(pos);
            });

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
                .attr("result", "blur");

            // translate output of Gaussian blur to the right and downwards
            // store result in offsetBlur
            filter.append("feOffset")
                .attr("in", "blur")
                .attr("dx", spacing/20)
                .attr("dy", spacing/10)
                .attr("result", "offsetBlur");

            // Attempring to set the alpha of the shadows, but this doesn't work...
            filter.append("feComponentTransfer")
                .append("feFuncA")
                .attr("type", "linear")
                .attr("slope", 0.2);

            // Merge the stones and the shadows
            var feMerge = filter.append("feMerge");
            feMerge.append("feMergeNode")
                .attr("in", "offsetBlur");
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
                .attr("stop-color", "#aaa");

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

            // whenever the bound expression changes, execute this
            scope.$watch('move', function (newpos, oldpos) {
                //board.selectAll('*').remove();

                var moves = $scope.moves.slice(0, newpos);
                //console.log("newpos", newpos, moves);
                var stones = stonegroup.selectAll("circle").data(moves);

                // var stonegroups = stones.enter().append("g")
                //         .attr("transform", function (m) {
                //             return "translate(" + m.position[0] * spacing + ","
                //                 + m.position[1] * spacing + ")";});

                var last_move = scope.moves.slice(-1)[0];
                stones.style("stroke", null);
                stones.enter().append("circle")
                    .filter(function(m) { return m.position; })
                //.style("fill", function(m) {return m.player == 0 ? "black" : "white";})
                    .style("fill", function(m) {
                        return "url(#" + ["black", "white"][m.player] + "gradient)";})
                    .attr("r", 0.95 * spacing/2)
                    .attr("cx", function(m) {return 0.5 + m.position[0] * spacing + spacing/2;})
                    .attr("cy", function(m) {return 0.5 + m.position[1] * spacing + spacing/2;})

                    .filter(function(m) { return m.n == newpos; })
                    .style("stroke", "red")
                    .style("stroke-width", 2);

                stones.exit().remove();

                // console.log("last move", last_move);
                // if (last_move && last_move.position) {
                //     board.select("circle").append("circle")
                //         .style("fill", "rgba(0,0,0,0)")
                //         .style("stroke", "red")
                //         .style("stroke-width", 3)
                //         .attr("r", spacing/3)
                //         .attr("cx", 0.5 + last_move.position[0] * spacing + spacing/2)
                //         .attr("cy", 0.5 + last_move.position[1] * spacing + spacing/2);
                // }

                // .on("mouseover", function(){d3.select(this).style("fill", "aliceblue");})
                // .on("mouseout", function(){d3.select(this).style("fill", "white");});
            });
        }
    };
});