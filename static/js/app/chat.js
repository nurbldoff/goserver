define( ['knockout-2.2.1'], function (ko) {

    return function (roomid) {
        var self = this;
        self.roomid = roomid;

        self.messages = ko.observableArray();
        self.new_message = ko.observable("");

        self.cursor = 0;
        self.default_timeout = 1000;

        self.send_message = function (msg) {
            $.ajax({url: "/room/" + roomid + "/message", type: "POST",
                    data: {body: self.new_message()},
                    success: function (data) {}});
        };

        self.poll = function(timeout) {
            $.ajax({url: "/room/" + roomid + "/updates", type: "POST",
                    data: {cursor: self.cursor}, timeout: timeout,
                    success: function (data) {self._update(data);
                                              self.poll(self.default_timeout);},
                    error: function () {
                        window.setTimeout(function() {self.poll(timeout * 2);},
                                          500);}});
        };

        self._update = function (data) {
            console.log(data.updates);
            var updates = data.updates;
            for (var i in updates) {
                self.messages.push({user: updates[i].user,
                                    body: updates[i].body,
                                    time: updates[i].time});
            }
            console.log(self.messages());
            self.new_message("");
            var $messages = $("#messages");
            $messages.animate({scrollTop: $messages[0].scrollHeight});
            self.cursor = data.cursor;
        };

        self.poll(self.default_timeout);
    };

});