$(document).ready(function () {

    $.ajaxSetup({
        async: false
    });


    // figure out which game we're showing
    var tmp = window.location.pathname.split("/");
    var game_id = tmp[tmp.length-1];

    var board_width = window.innerWidth/2;
    var board_size = 19;
    var paper = Raphael("gobanWrap", board_width, board_width);
    paper.stones = paper.set();
    var data;
    var this_player = $("#user").attr("value");

    var game = get_game_state(game_id);

    // peek at the board and display it
    //init_board(game, this_player, board_width, paper);
    redraw_display(game, this_player, board_width, paper);
    draw_board(game, paper);
    draw_moves(0, game, paper);
    //$("#messages").append($("<div>").text(game_state.message));

    update_chat(game_id);  // get the chat history

    // setup a websocket to listen for moves, chat messages and joins
    var hostname = window.location.hostname
    var port = window.location.port
    var ws = new WebSocket("ws://"+hostname+":"+port+"/socket?gameid="+game_id);
    ws.onmessage = function(event) {
        type = event.data;
        switch(type) {
        case "move":
            //data = update_board(game_id, this_player, board_size, board_width,
            //                    paper);
            console.log("Requesting moves from: " + game.moves.length)
            new_moves = get_moves(game_id, game.moves.length);
            start_from = game.moves.length;
            game.moves  = game.moves.concat(new_moves);
            draw_moves(start_from, game, paper);
            redraw_display(game, this_player, board_width, paper);
            console.log("Now have " + game.moves.length + " moves.")
            break;
        case "chat":
            update_chat(game_id);
            break;
        case "join":
            game = get_game_state(game_id);
            redraw_display(game, this_player, board_width, paper);
            break;
        }
    }
    ws.onopen = function() {};  // might be nice to send a greeting or something

    // setup redraw on window resize - doesn't handle zoom though :(
    $(window).bind('resize',function(){
        game.width = window.innerWidth/2;
        draw_board(game, paper);
        draw_moves(0, game, paper);
    });

    // activate the chat button
    send_chat_message = function () {
        $.post("/game/"+game_id, {message: $("#chatInput").attr("value")});
        $("#chatInput").attr("value", "");
    }
    $("#chatButton").click(send_chat_message);
    $('#chatInput').keypress(function(e){
        if(e.which == 13){
            send_chat_message();
        }
    });
});

function get_game_state(game_id) {
    var state;
    $.get("/game/"+game_id+"?get=state", function(data) {
        state = data;
    });
    state = eval('(' + state + ')');
    return state;
}

function get_moves(game_id, from) {
    var state;
    $.get("/game/"+game_id+"?get=moves&from="+from, function(data) {
        state = data;
    });
    return eval('(' + state + ')');
}

function update_chat(game_id) {
    var fr = $("#messages").children().length;
    $.get("/game/"+game_id+"?get=chat&from="+fr, "", function(result) {
        var chat_data = eval('(' + result + ')');
        $.each(chat_data, function(i, message) {
            var $msg = $("<div>");
            $msg.append($("<span>").text(message.user).addClass("chatUser"));
            $msg.append($("<span>").text(message.content));
            $("#messages").append($msg);
            //$("#messages").prop({ scrollTop: $("#messages").prop("scrollHeight") });

        });
        $("#messages").animate({ scrollTop: $("#messages").prop("scrollHeight") }, 300);
    });
    //$("#messages").css("height", "300px");


}

function redraw_display(game, player, width, paper, draw_all) {
    // Updates the game status display
    $("#blackStatusWrap").text(game.black + (game.black == player ? " (You)" : ""));
    $("#whiteStatusWrap").text((game.white ? game.white : "") + (game.white == player ? " (You)" : ""));
    if((game.moves.length % 2) == 1) {
        $("#whiteStatusWrap").attr("class", "activePlayer");
        $("#blackStatusWrap").attr("class", "inactivePlayer");
    } else {
        $("#blackStatusWrap").attr("class", "activePlayer");
        $("#whiteStatusWrap").attr("class", "inactivePlayer");
    }
}

function draw_board(game, paper) {
    // Draw a goban

    // background
    paper.clear()
    var board_bg = paper.image("../static/goban_whole4_small.jpg", 0, 0,
                               paper.width, paper.width);
    var board = paper.set();
    paper.board = board;
    //var bg = paper.rect(1, 1, width, width);
    //bg.attr("fill", "orange");

    // grid
    var delta = paper.width/game.board_size;
    var buffer = [];
    for(var i=0; i<game.board_size; i++) {
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
    var radius = 0.95*(paper.width/game.board_size)/2;

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
    text = paper.text(0, 0, "")
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

    board.click(function(event) {   // Handle mouse clicks
        var posx = event.pageX-$("#gobanWrap").offset().left;
        var posy = event.pageY-$("#gobanWrap").offset().top;
        var row = Math.floor(posy / (paper.height / game.board_size));
        var col = Math.floor(posx / (paper.width / game.board_size));
        $.post("/game/"+game.id, {move: row+","+col});
    });

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


function draw_moves(start_from, game, paper) {
    // Draw the stones, starting from a certain move

    var delta = paper.width/19;
    var stone, shadow, move, row, col, coords;

    // i = row, j = column
    for (var i = start_from; i < game.moves.length; i++) {
        move = game.moves[i];
        row = move.position[0];
        col = move.position[1];
        coords = get_pos(row, col, game.board_size, paper);
        coords.x += Math.random()-0.5;
        coords.y += Math.random()-0.5;
        switch (i % 2)
        {
        case 0:  // black stone
            stone = paper.black_stone.clone();
            stone.transform("T" + coords.x + "," + coords.y);
            stone[0].toBack();
            paper.board.toBack();
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
        stone[2].attr("text", i+1).hide();
        stone.hover(function (a) {this[2].show();},
                    function (a) {this[2].hide();}, stone, stone);

    }
    if (coords) {
        paper.marker.transform("T" + coords.x + "," + coords.y);
        paper.marker.toFront();
        paper.marker.show();
    }
}

function get_pos(row, col, size, paper) {
    var delta = paper.width / size;
    return({x: delta/2 + delta*col - 0.5, y: delta/2 + delta*row - 0.5});
}
