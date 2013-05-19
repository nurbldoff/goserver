define( ['knockout'], function (ko) {

    return function (roomid) {
        var self = this;
        self.roomid = roomid;

        self.chat_messages = ko.observableArray();
        self.game_messages = [];

        var _msg_cache = [], chat_cursor = 0, move_cursor = 0;
        self.messages = ko.computed(function () {
            // Interleave chat messages and game moves.
            // Because it gets run on every new message, it caches previous results
            // in order to not be horribly inefficient.
            var time = 0,
                chat_messages = self.chat_messages(),
                game_messages = self.game_messages;

            for (chat_cursor; chat_cursor < chat_messages.length; chat_cursor++) {
                var msg = chat_messages[chat_cursor], captures = [0, 0];
                time = msg.time;
                var start_offset = move_cursor;
                while (move_cursor < game_messages.length &&
                       game_messages[move_cursor].time < time) {
                    var move = game_messages[move_cursor];
                    move_cursor++;
                    if (move.captures) {
                        captures[move.player] += move.captures.length;
                    }
                }
                if (move_cursor > start_offset) {
                    var move_msg = {user: ""};
                    if (move_cursor > start_offset + 1)
                        move_msg.body = "moves: " + (start_offset + 1) + "-" + move_cursor;
                    else
                        move_msg.body = "move: " +  move_cursor;
                    if (captures[0] || captures[1])
                        move_msg.body += ", captures: " + captures[0] + "/" + captures[1];
                    _msg_cache.push(move_msg);
                }
                _msg_cache.push(msg);
            }
            return _msg_cache;
        });

        self.cursor = 0;
        self.default_timeout = 1000;

        self.send_message = function (form) {
            var msg = $("#new-message").val();
            $("#new-message").val("");
            $.ajax({url: "/room/" + roomid + "/message", type: "POST",
                    data: {body: msg},
                    success: function (data) {}});
        };

        self.poll = function(timeout) {
            $.ajax({url: "/room/" + roomid + "/updates", type: "POST",
                    data: {cursor: self.cursor}, timeout: timeout,
                    success: function (data) {self._update(data);
                                              self.poll(timeout * 2);},
                    error: function () {
                        window.setTimeout(function() {self.poll(timeout * 2);},
                                          500);}});
        };

        self._update = function (data) {
            console.log(data.updates);
            var updates = data.updates;
            for (var i in updates) {
                var latest_msg = self.chat_messages().slice(-1)[0];
                // Check that the new message id is larger than the latest we showed.
                if (self.chat_messages().length == 0 ||
                    (latest_msg && (updates[i]._id > self.chat_messages().slice(-1)[0]._id))) {
                    self.chat_messages.push(updates[i]);
                }
            }
            var $messages = $("#messages");
            $messages.animate({scrollTop: $messages[0].scrollHeight});
            self.cursor = data.cursor;
        };

        ko.postbox.subscribe("move", function (msg) {
            //console.log("msg", msg);
            self.game_messages.push(msg);
        });

        // ko.postbox.subscribe("error", function (msg) {
        //     self.game_messages.push(msg);
        // });

        self.poll(self.default_timeout);

    };

});