$(document).ready(function () {

    // figure out which game we're showing
    var tmp = window.location.pathname.split("/");
    var game_id = tmp[tmp.length-1];

    var board_width = window.innerWidth/2;
    var board_size = 19;
    var paper = Raphael("gobanWrap", board_width, board_width);
    var stones = paper.set();
    var data;
    var this_player = $("#user").attr("value");

    // peek at the board and display it
    data = update_board(game_id, this_player, board_size, board_width, paper);
    update_chat(game_id);  // get the chat history

    // setup a websocket to listen for moves, chat messages and joins
    var hostname = window.location.hostname
    var port = window.location.port
    var ws = new WebSocket("ws://"+hostname+":"+port+"/socket?gameid="+game_id);
    ws.onmessage = function(event) {
        type = event.data;
        switch(type) {
        case "move":
            data = update_board(game_id, this_player, board_size, board_width, paper);
            break;
        case "chat":
            update_chat(game_id);
            break;
        case "join":
            data = update_board(game_id, this_player, board_size, board_width, paper);
            break;
        }
    }
    ws.onopen = function() {};  // might be nice to send a greeting or something

    // setup redraw on window resize - doesn't handle zoom though :(
    $(window).bind('resize',function(){
        var board_width = window.innerWidth/2;
        update_board(game_id, this_player, board_size, board_width, paper, data);
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

function update_board(game_id,  this_player, board_size, board_width, paper, state) {
    if (!state) {
        $.get("/game/"+game_id+"?get=board", "", function(result) {
            state = result
            redraw_display(game_id, this_player, board_size, board_width, paper, result);
        });
    } else {
        redraw_display(game_id, this_player, board_size, board_width, paper, state);
    }
    return state;
}


function update_chat(game_id) {
    var fr = $("#messages").children().length;
    $.get("/game/"+game_id+"?get=chat&from="+fr, "", function(result) {
        var chat_data = eval('(' + result + ')');
        $.each(chat_data, function(i, message) {
            var $msg = $("<div>").text(message.user+":"+message.content);
            $("#messages").append($msg);
            //$("#messages").prop({ scrollTop: $("#messages").prop("scrollHeight") });

        });
        $("#messages").animate({ scrollTop: $("#messages").prop("scrollHeight") }, 300);
    });
    //$("#messages").css("height", $("td.messages").prop("height"));


}

function redraw_display(game_id, player, size, width, paper, data) {
    var game_state = eval('(' + data + ')');
    //if($("#user").text() == "
    $("#blackStatusWrap").text(game_state.black + (game_state.black == player ? " (You)" : ""));
    $("#whiteStatusWrap").text((game_state.white ? game_state.white : "") + (game_state.white == player ? " (You)" : ""));
    if(game_state.active_player == "w") {
        $("#whiteStatusWrap").attr("class", "activePlayer");
        $("#blackStatusWrap").attr("class", "inactivePlayer");
    } else {
        $("#blackStatusWrap").attr("class", "activePlayer");
        $("#whiteStatusWrap").attr("class", "inactivePlayer");
    }
    draw_board(game_id, size, width, paper);
    draw_stones(game_state.board, game_state.last_move, size, width, paper);
    //$("#messages").append($("<div>").text(game_state.message));
}


function draw_board(game_id, size, width, paper) {
    // background
    paper.clear()
    paper.image("../static/goban_whole4_small.jpg", 0, 0, width, width);
    //var bg = paper.rect(1, 1, width, width);
    //bg.attr("fill", "orange");

    // grid
    var delta = width/size;
    var buffer = [];
    for(var i=0; i<size; i++) {
        buffer.push("M");
        buffer.push(delta/2);
        buffer.push(",");
        buffer.push(delta/2+delta*i);
        buffer.push("h");
        buffer.push(width-delta);
        buffer.push("M");
        buffer.push(delta/2+delta*i);
        buffer.push(",");
        buffer.push(delta/2);
        buffer.push("v");
        buffer.push(width-delta);
    }
    var grid = paper.path(buffer.join(""));
    grid.attr("stroke", "#403020");

    // tengen, hoshi
    var marker;
    for (var i = 0; i < 3; i++) {
        for (var j = 0; j < 3; j++) {
            marker = paper.circle((3.5+i*6)*delta, (3.5+j*6)*delta, delta/12);
            marker.attr("stroke-width", 0);
            marker.attr("fill", "black");
        }
    }
    // click targets
    var click_handler = function () {
        //$.get("/game/"+game_id+"?move=" +
        $.post("/game/"+game_id, {move: this.data("col")+","+this.data("row")});
        //alert(this.data("col") + "," + this.data("row"));
    }
    for (var i = 0; i < size; i++) {
        for (var j = 0; j < size; j++) {
            marker = paper.rect(j*delta, i*delta, delta, delta);
            marker.attr("fill", "blue");
            marker.attr("opacity", 0.0);
            marker.data("row", j);
            marker.data("col", i);
            marker.click(click_handler);
            //marker.attr("href", "/game/"+game_id+"?move="+j+","+i);
        }
    }
}


function draw_stones(board, last_move, size, width, paper) {
    // stones
    var delta = width/size;
    var radius = 0.95*(width/size)/2;
    var stone, shadow, what;
    // i = row, j = column
    for (var i = 0; i < size; i++) {
        for (var j = 0; j < size; j++) {
            what = board.charAt(size*i+j);
            switch (what)
            {
            case "b":  // black stone
                shadow = paper.circle(delta/2+j*delta,
                                      delta/2+i*delta+delta/7, radius*0.95);
                shadow.attr("fill", "black").attr("opacity", 0.5);
                shadow.attr("stroke-opacity", 0.4).attr("stroke-width", delta/8);
                stone = paper.circle(delta/2+j*delta, delta/2+i*delta, radius);
                stone.attr("stroke-opacity", 0.2)
                stone.attr("fill", 'r(0.5, 0.2 )#666-#000');
                break;
            case "w":  // white stone
                shadow = paper.circle(delta/2+j*delta, delta/2+i*delta+delta/7,
                                      radius*0.95);
                shadow.attr("fill", "black");
                shadow.attr("stroke-width", delta/8);
                shadow.attr("stroke-opacity", 0.4);
                shadow.attr("opacity", 0.5);
                stone = paper.circle(delta/2+j*delta, delta/2+i*delta, radius);
                stone.attr("fill", 'r(0.5, 0.25)#fff-#aaa');
                stone.attr("stroke-opacity", 0.2)
                break;
            }
            if (i == last_move[0] && j == last_move[1]) {
                marker = paper.circle(delta/2+j*delta,
                                      delta/2+i*delta, radius*0.5);
                marker.attr("stroke-width", delta/8);
                marker.attr("stroke", "#ff0000");
            }
        }
    }
}

function draw_board_simple(state, game_id) {
    // Draw a simple goban

    // get a JSON object containing game info
    var game_state = eval('(' + state + ')');

    // build a table representing a goban
    var $wrap = $('<div>').attr('id', 'gobanWrap');
    var $tbl = $('<table>').attr('id', 'goban');
    for (var i = 0; i < 19; i++) {
        var $row = $('<tr>').attr('class', 'gobanRow')
        for (var j = 0; j < 19; j++) {
            var $marker = $('<td>');
            var what = game_state.board.charAt(19*i+j);
            switch (what)
            {
            case ".":
                $marker.text("+").addClass('emptyPosition');
                break;
            case "b":
                $marker.text("●").addClass('blackStone');
                break;
            case "w":
                $marker.text("●").addClass('whiteStone');
                break;
            }
            $marker.addClass('gobanPosition');
            $marker.attr("row", i).attr("col", j);
            $marker.click(function () {
                $.get("/game/"+game_id+"?move=" +
                      $(this).attr("row")+","+$(this).attr("col"));
            });
            $row.append($marker);
        }
        $tbl.append($row);
    }

    // show whose move it is
    var active_player;
    if(game_state.active_player == "b") {
        active_player = "Black";
    } else {
        active_player = "White";
    }

    $wrap.append($("<p>").text(active_player + "'s turn!"));
    $wrap.append($tbl);
    //$wrap.append($("<p>").text(game_state.board));
    $("#gobanWrap").replaceWith($wrap);
};
