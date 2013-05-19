define(['knockout', 'd3',
        'app/board'], function (ko, d3, GoBoard) {

    return function (gameid, username) {
        var self = this;

        self.id = gameid;
        self.username = username;

        self.moves = ko.observableArray([]);
        self.current_move = ko.observable(0);
        self.cursor = ko.observable(0);

        self.black = ko.observable();
        self.white = ko.observable();
        self.turn = ko.observable(0);

        self.finished = ko.observable(false);

        self.playing = ko.computed(function () {
            return self.username == self.black() || self.username == self.white();
        });

        self.captures = ko.computed(function () {
            var captures = [[], []], moves = self.moves();
            for (var i=0; i < self.current_move(); i++) {
                if (moves[i].captures)
                    captures[moves[i].player] = captures[moves[i].player].concat(
                        moves[i].captures);
            }
            //console.log(captures);
            return captures;
        });

        self.show_path = ko.observable(false);

        self.error = ko.observable("");
        ko.computed(function () {
            self.error();
            $("#error").fadeIn(100).fadeOut(5000);
        });

        self.size = 19;
        var default_timeout = 1000;

        // Init the board, connect to updates
        self.board = new GoBoard("#goban", self.size, 700);
        ko.computed(function () {
            self.board.update_stones(self.moves(), self.current_move(), self.captures());
        });
        ko.computed(function () {
            self.board.update_path(self.show_path(), self.moves(), self.current_move());
        });
        self.board.goban.on("click", function (d, i) {
            var coords = d3.mouse(this),
                pos = self.board.get_position(coords);
            self.make_move(pos);
        });

        self.make_move = function (pos) {
            if ((pos[0] >= 0 && pos[0] < 19) && (pos[1] >= 0 && pos[1] < 19)) {
                $.ajax({url: "/game/" + self.id + "/move", type: "POST",
                        data: {position: pos[0] + "," + pos[1]},
                        success: function (data) {
                            console.log(data);
                            self.error(data.error);
                        }});
            }
        };

        self.pass = function () {
            $.ajax({url: "/game/" + self.id + "/move", type: "POST",
                    data: {position: "null"},
                    success: function (data) {self.error(data.error);}});
        };

        self.resign = function () {
            $.ajax({url: "/game/" + self.id + "/move", type: "POST",
                    data: {position: "null", resign: true},
                    success: function (data) {self.error(data.error);}});
        };

        self.get_state = function () {
            $.get("/game/" + self.id + "/state",
                  function (data) {
                      console.log(data);
                      self.black(data.black);
                      self.white(data.white);
                      //self.size(data.size);
                  }, "json");
        };

        self.poll = function(timeout) {
            $.ajax({url: "/game/" + self.id + "/updates", type: "POST",
                    data: {cursor: self.cursor}, timeout: timeout,
                    success: function (data) {self._update(data);
                                              self.poll(self.default_timeout);},
                    error: function () {
                        window.setTimeout(function() {self.poll(timeout * 2);},
                                          500);}});
        };

        self._update = function (data) {
            var updates = data.updates;
            console.log(updates);
            for (var i in updates) {
                if (updates[i].move) {
                    var move = updates[i].move;
                    self.moves.push(move);
                    self.update_turn(move.player);
                    if (move.finished)
                        self.finished(true);
                }
                if (updates[i].join) {
                    var user = updates[i].join.user;
                    if (self.black())
                        self.white(user);
                    else
                        self.black(user);
                }
                ko.postbox.publish("move", move);
            }
            if (self.current_move() == self.cursor()) {
                self.current_move(data.cursor);
            }
            console.log("moves", self.moves());
            self.cursor(data.cursor);
        };

        // Check the status of the game
        self.get_state();

        // let the polling begin!
        self.poll(default_timeout);

        self.update_turn = function (player) {
            if (player == 1) {
                if (self.turn() == 0)
                    console.log("strange, it was already black's turn...");
                self.turn(0);
            } else {
                if (self.turn() == 1)
                    console.log("strange, it was already white's turn...");
                self.turn(1);
            }
        };

        self.next_move = function () {
            self.current_move(Math.min(self.moves().length, self.current_move() + 1));
        };

        self.prev_move = function () {
            self.current_move(Math.max(0, self.current_move() - 1));
        };

        // Update the slider's max value when new moves arrive
        ko.computed(function () {
            var input = document.getElementById("move_slider");
            input.setAttribute("max", self.moves().length);
        });

    };
});