Go.draw_board = function (game, paper) {
    // Draw a goban


    console.log("Game:", game)
    // background
    paper.clear()
    var board_bg = paper.image("../static/goban_whole4_small.jpg", 0, 0,
                               paper.width, paper.width);
    var board = paper.set();
    paper.board = board;
    //var bg = paper.rect(1, 1, width, width);
    //bg.attr("fill", "orange");

    // grid
    var delta = paper.width/game.get("board_size");
    var buffer = [];
    for(var i=0; i<game.get("board_size"); i++) {
        buffer.push("M");
        buffer.push(Math.round(delta/2)-0.5);
        buffer.push(",");
        buffer.push(Math.round(delta/2+delta*i)-0.5);
        buffer.push("h");
        buffer.push(Math.round(paper.width-delta));
        buffer.push("M");
        buffer.push(Math.round(delta/2+delta*i)-0.5);
        buffer.push(",");
        buffer.push(Math.round(delta/2)-0.5);
        buffer.push("v");
        buffer.push(Math.round(paper.width-delta));
    }
    var grid = paper.path(buffer.join(""));
    grid.attr("stroke", "#403020");
    board.push(grid);

    // tengen, hoshi (TODO: align better with the grid)
    var marker;
    for (var i = 0; i < 3; i++) {
        for (var j = 0; j < 3; j++) {
            marker = paper.circle((3.5+i*6)*delta-0.5, (3.5+j*6)*delta-0.5,
                                  delta/12);
            marker.attr("stroke-width", 0);
            marker.attr("fill", "black");
            board.push(marker);
        }
    }
    board.push(grid);
    board.push(board_bg);
    paper.board.toBack();

    var stone, shadow, _shadow, text;
    var radius = 0.95*(paper.width/game.get("board_size"))/2;

    // black stone original, vill be cloned for each stone
    _shadow = paper.circle(radius*0.1, radius*0.2, radius*0.7).attr(
        "fill", "black");
    shadow = _shadow.glow(radius*0.05, true, 1.0);
    _shadow.remove();
    stone = paper.circle(0, 0, radius);
    stone.attr("stroke-opacity", 0.0).attr("stroke-width", 1);
    stone.attr("fill", 'r(0.4, 0.25 )#555-#3c3c3c-#111');
    stone.toFront();
    stone.attr("font-size", 5);
    text = paper.text(0, 0, "");
    text.attr("fill", "white");
    $(text.node).addClass("stoneText");
    text.toFront();

    paper.black_stone = paper.set();
    paper.black_stone.push(shadow);
    paper.black_stone.push(stone);
    paper.black_stone.push(text);
    paper.black_stone.text = text;
    paper.black_stone.hide();


    // white stone original
    _shadow = paper.circle(radius*0.1, radius*0.2, radius*0.7).attr(
        "fill", "black");
    shadow = _shadow.glow(radius*0.05, true, 1.0);
    _shadow.remove();
    stone = paper.circle(0, 0, radius);
    stone.attr("fill", 'r(0.4, 0.25)#fff-#ddd-#aaa');
    stone.attr("stroke-opacity", 0.0);
    stone.attr("font-size", 5);
    stone.toFront();
    text = paper.text(0, 0, "")
    text.attr("fill", "black");
    text.toFront();

    paper.white_stone = paper.set();
    paper.white_stone.push(shadow);
    paper.white_stone.push(stone);
    paper.white_stone.push(text);
    paper.white_stone.text = text;
    paper.white_stone.hide();
    paper.white_stone.stone = stone;

    // last move marker. Will be made visible and moved around.
    marker = paper.circle(0, 0, radius*0.5);
    marker.attr("stroke-width", delta/8);
    marker.attr("stroke", "#ff0000");
    paper.marker = paper.set();
    paper.marker.push(marker);
    paper.marker.hide();

    // board.click(function(event) {   // Handle mouse clicks
    //     var posx = event.pageX-$("#gobanWrap").offset().left;
    //     var posy = event.pageY-$("#gobanWrap").offset().top;
    //     var row = Math.floor(posy / (paper.height / game.get("board_size")));
    //     var col = Math.floor(posx / (paper.width / game.get("board_size")));
    //     $.post("/game/"+game.get("id"), {move: row+","+col});
    // });

    // FIXME: Hover function flickers too much.
    // board.hover(function(event) {   // Handle mouse clicks
    //     var posx = event.pageX-$("#gobanWrap").offset().left;
    //     var posy = event.pageY-$("#gobanWrap").offset().top;
    //     var row = Math.floor(posy / (paper.height / game.board_size));
    //     var col = Math.floor(posx / (paper.width / game.board_size));
    //     // try {
    //     //     paper.ghost.remove();
    //     // } catch(err) {}
    //     if(game.moves.length) {
    //         paper.ghost = paper.black_stone.clone();
    //     } else {
    //         paper.ghost = paper.white_stone.clone();
    //     }
    //     paper.ghost.transform("T"+((col+0.5)*delta)+","+((row+0.5)*delta));
    //     paper.ghost.show();
    // }, function(event) {
    //     try {
    //         paper.ghost.remove();
    //     } catch(err) { }
    // });
}

Go.delete_stone =

Go.draw_stone = function (n, game, paper) {
    // Draw a stone for move number n

    var delta = paper.width/game.get("board_size");
    var stone, shadow, move, pos, row, col, coords;

    function get_pos(row, col, size, paper) {
        var delta = paper.width / size;
        return({x: delta/2 + delta*col - 0.5, y: delta/2 + delta*row - 0.5});
    }

    // i = row, j = column
    console.log("Number of moves:", game.moves.length);
    move = game.moves.at(n);
    pos = move.get("position");
    if (pos == null) {
        return;
    }

    row = pos[0];
    col = pos[1];
    coords = get_pos(row, col, game.get("board_size"), paper);
    coords.x += Math.random()-0.5;
    coords.y += Math.random()-0.5;
    switch (n % 2) {
    case 0:  // black stone
        stone = paper.black_stone.clone();
        stone.transform("T" + coords.x + "," + coords.y);
        stone[0].toBack();     // a hack to prevent the shadow
        paper.board.toBack();  // from covering nearby stones
        stone.show();
        paper.stones.push(stone);
        break;
    case 1:  // white stone
        stone = paper.white_stone.clone();
        stone.transform("T" + coords.x + "," + coords.y);
        stone[0].toBack();
        paper.board.toBack();
        stone.show();
        paper.stones.push(stone);
        break;
    }
    stone[2].attr("text", n+1).hide();
    stone.hover(function (a) {this[2].show();},
                function (a) {this[2].hide();}, stone, stone);
    if (move.get("captures")) {
        $.each(move.get("captures"), function (index, capture) {
            paper.stones[capture].remove();
        });
    }
    if (coords) {
        paper.marker.transform("T" + coords.x + "," + coords.y);
        paper.marker.toFront();
        paper.marker.show();
    }
}
