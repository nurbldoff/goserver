// Copyright 2009 FriendFeed
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may
// not use this file except in compliance with the License. You may obtain
// a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations
// under the License.

var Go = Go || {};  // the main "namespace"

$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    // if (!Go.game) {
    //     // figure out which game we're showing
    //     var game_id = window.location.pathname.substring(
    //         window.location.pathname.lastIndexOf('/') + 1);
    //     Go.game = Go.Game(Go.get_game_state(game_id));
    // }
    Go.boardview = new Go.BoardView(Go.game.moves);
    Go.infoview = new Go.InfoView(Go.game);
    Go.chatview = new Go.ChatView(Go.game.messages);
    //console.log(Go.game);
});

// Change template escaping to {{...}} to match tornado
//_.templateSettings.interpolate = /\{\{(.+?)\}\}/g;

jQuery.postJSON = function(url, args, callback) {
    args._xsrf = Go.get_cookie("_xsrf");
    console.log("Posting:", $.param(args));
    $.ajax(
        {url: url, data: $.param(args), dataType: "text", type: "POST",
         success: function(response) {
             if (callback) {
                 callback(
                     eval("(" + response + ")"));
             }},
         error: function(response) {
             console.log("ERROR:", response);
         }
        }
    );
};

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

jQuery.fn.disable = function() {
    this.enable(false);
    return this;
};

jQuery.fn.enable = function(opt_enable) {
    if (arguments.length && !opt_enable) {
        this.attr("disabled", "disabled");
    } else {
        this.removeAttr("disabled");
    }
    return this;
};

// // Monkeypatching backbone to add xsrf cookie... doesn't work though.
// Backbone.Model.prototype.toJSON = function() {
//     console.log("toJSON", _.clone(this.attributes));
//     return _(_.clone(this.attributes)).extend(
//         {_xsrf: Go.get_cookie("_xsrf")});
// };

// Main namespace
Go = {

    chat_updater: {
        // Gets updates about the chatroom, e.g. new messages, joins and leaves
        errorSleepTime: 500,
        cursor: null,

        poll: function() {
            var args = {"_xsrf": Go.get_cookie("_xsrf")};
            if (Go.chat_updater.cursor) args.cursor = Go.chat_updater.cursor;
            $.ajax({url: "/room/" + Go.game.id + "/updates",
                    type: "POST", dataType: "text",
                    data: $.param(args), success: Go.chat_updater.on_success,
                    error: Go.chat_updater.on_error});
        },

        on_success: function(response) {
            try {
                Go.chat_updater.new_updates(eval("(" + response + ")"));
            } catch (e) {
                Go.chat_updater.on_error(response);
                return;
            }
            Go.chat_updater.errorSleepTime = 500;
            window.setTimeout(Go.chat_updater.poll, 0);
        },

        on_error: function(response) {
            Go.chat_updater.errorSleepTime *= 2;
            console.log(response);
            console.log("Chat poll error; sleeping for",
                        Go.chat_updater.errorSleepTime, "ms");
            window.setTimeout(Go.chat_updater.poll,
                              Go.chat_updater.errorSleepTime);
        },

        new_updates: function(response) {
            if (!response.updates) return;
            console.log("message:", response.updates);
            var updates = response.updates;
            Go.game.messages.add(updates);
            this.cursor = updates[updates.length-1].id;
            //console.log(updates.length, "new messages, cursor:", Go.cursor);
            // for (var i = 0; i < messages.length; i++) {
            //     Go.show_message(messages[i]);
            // }
        },
    },

    game_updater: {
        // Gets updates about game state; e.g. moves, joins, etc

        errorSleepTime: 500,
        cursor: null,

        poll: function() {
            var args = {"_xsrf": Go.get_cookie("_xsrf")};
            //if (Go.game_updater.cursor) args.cursor = Go.game_updater.cursor;
            args.cursor = Go.game.moves.length - 1;
            $.ajax({url: "/game/" + Go.game.id + "/updates",
                    type: "POST", dataType: "text",
                    data: $.param(args), success: Go.game_updater.on_success,
                    error: Go.game_updater.on_error});
        },

        on_success: function(response) {
            // Callback for when the poll request gets a reply
            try {
                console.log("response:", response);
                Go.game_updater.new_updates(eval("(" + response + ")"));
            } catch (e) {
                console.log("Why?", e);
                Go.game_updater.on_error(response);
                return;
            }
            Go.game_updater.errorSleepTime = 500;
            window.setTimeout(Go.game_updater.poll, 0);
        },

        on_error: function(response) {
            // Callback for when the polling fails
            Go.game_updater.errorSleepTime *= 2;
            console.log(response);
            console.log("Game poll error; sleeping for",
                        Go.game_updater.errorSleepTime, "ms");
            window.setTimeout(Go.game_updater.poll,
                              Go.game_updater.errorSleepTime);
        },

        new_updates: function(response) {
            // What to do when game updates are received
            if (!response.updates) return;
            console.log("game update:", response.updates);
            var updates = response.updates;
            Go.game.update(updates);
            //this.cursor = updates[updates.length-1].id;
        },
    },


    send_move: function(move_data) {
        // Send a new move to the server
        console.log("send_move: ", move_data);

        // This seems like a nicer way...
        //move = new Move(move_data);
        //Go.game.moves.create(move_data);

        $.postJSON(Go.game.moves.url(), move_data, function(response) {
            // FIXME: Do something with the response.
            if (response.error) {
                console.log(response.error);
            }
        });
    },

    send_message: function(message_data) {
        // Send a new message to the server
        console.log("send_message: ", message_data);
        $.postJSON(Go.game.messages.url(), message_data,
                   function(response) {
                       // FIXME: Do something with the response
                   });
    },

    get_game_state: function(game_id) {
        var state;
        $.get("/game/"+game_id+"/state", function(data) {
            state = data;
        });
        state = eval('(' + state + ')');
        console.log(state);
        return state;
    },

    get_active_player: function() {
        return Go.game.moves.length % 2;
    },

    get_cookie: function(name) {
        var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
        return r ? r[1] : undefined;
    },

};


Go.Move = Backbone.Model.extend({

    url: function () {
        return "/game/" + Go.game.id + "/move";
    }

});

Go.MoveCollection = Backbone.Collection.extend({

    model: Go.Move,
    cursor: 0,

    initialize: function (spec) {
        this.on("add", function (move, moves, options) {
            console.log("a Move was made by", move.get("player"),
                        move.get("position"));
        });
    },

    url: function() {
        return "/game/" + Go.game.id + "/move";
    }
});

Go.Message = Backbone.Model.extend({
    validate: function(attrs) {
        // Do some validating, perhaps?
    },
});

Go.MessageCollection = Backbone.Collection.extend({
    model: Go.Message,
    cursor: 0,

    initialize: function (spec) {
        this.on("add", function (message, messages, options) {
            console.log("Added message:", message.get("body"));
        });
    },

    url: function() {
        return "/room/" + Go.game.id + "/message";
    }
});

Go.Game = Backbone.Model.extend({
    // Game model
    defaults: {
        captures: [0, 0],
        finished: false
    },

    initialize: function (spec) {
        _.bindAll(this, "add_captures");
        this.moves = new Go.MoveCollection(spec.moves);
        this.messages = new Go.MessageCollection(spec.messages);
        this.moves.each(this.add_captures);
        this.moves.on("add", this.add_captures, this);
    },

    url: function () {return "/game/" + this.id + "/state";},

    update: function (updates) {
        $.each(updates, function (index, update) {
            console.log("Game update:", update);
            if (update.move) {
                Go.game.moves.add(update.move);
            }
            if (update.join) {
                Go.game.set("white", update.join.user);
            }
            if (update.status) {
                if (update.status.finished) {
                    Go.game.set("finished", true);
                }
            }
        });
    },

    add_captures: function (move, index, moves) {
        var captured = move.get("captures");
        if (captured) {
            var player = move.get("n") % 2;
            var caps = this.get("captures");
            caps[player] = caps[player] + captured.length;
            this.set("captures", caps);
        }
    }
});

Go.BoardView = Backbone.View.extend({
    // Game view
    //model: Go.game.moves,
    el: $('#goban'),
    events: {
        "click": "submit_move"
    },

    initialize: function (model) {
        //_.bindAll(this, "submit_message");
        this.model = model;
        this.model.on("add", this.show_move);
        Go.game_updater.poll();
        this.render();
    },

    render: function () {
        var board_width = window.innerWidth/2;
        this.paper = Raphael("goban", board_width, board_width);
        this.paper.stones = this.paper.set();
        Go.draw_board(Go.game, this.paper);

        for (var i=0; i < Go.game.moves.length; i++) {
            Go.draw_stone(i, Go.game, this.paper);
        }
    },

    submit_move: function (event) {
        var posx = event.pageX-$("#goban").offset().left;
        var posy = event.pageY-$("#goban").offset().top;
        var pos = this.get_move_position(posx, posy);
        console.log("Move: " + pos.row + ", " + pos.col);
        Go.send_move({position: pos.row + "," + pos.col});
    },

    show_move: function(move) {
        Go.draw_stone(move.get("n"), Go.game, Go.boardview.paper);
    },

    get_move_position: function (x, y) {
        var unit = this.paper.height / Go.game.get("board_size");
        var row = Math.floor(y / unit);
        var col = Math.floor(x / unit);
        return {row: row, col: col};
    }
});

Go.InfoView = Backbone.View.extend({
    // Game view
    model: Go.game,
    el: $('#gameinfo'),
    events: {
        "click #passButton": "submit_pass",
    },

    initialize: function (model) {
        _.bindAll(this, "render");
        this.model = model;
        this.model.moves.on("add", this.render);
        this.model.on("change", this.render);
        this.render();
    },

    render: function () {
        console.log("Render info");
	// Compile the template using underscore
	var template = _.template( $("#gameinfo_template").html(), {
            black: Go.game.get("black"),
            white: Go.game.get("white"),
            black_captures: Go.game.get("captures")[0],
            white_captures: Go.game.get("captures")[1]
        } );
	// Load the compiled HTML into the Backbone "el"
	$("#gameinfo").html( template );
	//this.el.html( template );
        if (Go.get_active_player() == 0) {
            $("#blackStatus").addClass("activePlayer");
            $("#whiteStatus").removeClass("activePlayer");
        } else {
            $("#whiteStatus").addClass("activePlayer");
            $("#blackStatus").removeClass("activePlayer");
        }
    },

    submit_pass: function () {
        Go.send_move({position: null});
    }

});


Go.ChatView = Backbone.View.extend({
    // Chat view
    // model: Go.game.messages,
    el: $('#chat'),
    events: {
        "submit #messageform": "submit_message",
        "keypress #messageform": "submit_message_key"
    },

    initialize: function (model) {
        //_.bindAll(this, "submit_message");
        this.model = model;
        Go.game.messages.on("add", this.show_message);
        Go.chat_updater.poll();
        $("#message").select();
        this.render();
    },

    render: function () {
        Go.game.messages.each(function(message, index, all) {
            console.log(message);
            this.show_message(message, 0, 0, index != (all.length-1));
        }, this);
    },

    get_chat_form: function () {
        var form = $("#messageform");
        var message = form.formToDict();
        form.find("input[name=body]").val("");
        return message;
    },

    submit_message: function () {
        var form = this.get_chat_form();
        if (form.body.length > 0) {
            Go.send_message(form);
        }
        $("#messageform").find("input[type=text]").select();
        return false;
    },

    submit_message_key: function (e) {
        if (e.keyCode == 13) {
            var form = this.get_chat_form();
            if (form.body.length > 0) {
                Go.send_message(form);
            }
            return false;
        }
    },

    show_message: function(message, index, messages, noscroll) {
        // Add a new message to the display
        var date = new Date(message.get("time")*1000);
	var template = _.template( $("#chatmessage_template").html(), {
            time: date.toLocaleTimeString(),
            user: message.get("user"),
            body: message.get("body")
        } );
        $("#inbox").append(template);

        if (!noscroll) {
            $("#inbox").animate({ scrollTop: $("#inbox").prop("scrollHeight") }, 500);
        }
    }
});
