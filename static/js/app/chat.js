define( ['knockout-2.2.1'], function (ko) {

    return function (roomid) {
        var self = this;
        self.roomid = roomid;

        self.messages = ko.observableArray();

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
                console.log("last message", self.messages());
                var latest_msg = self.messages().slice(-1)[0];
                // Check that the new message id is larger than the latest we showed.
                if (self.messages().length == 0 ||
                    (latest_msg && (updates[i]._id > self.messages().slice(-1)[0]._id))) {
                    self.messages.push(updates[i]);
                }
            }
            var $messages = $("#messages");
            $messages.animate({scrollTop: $messages[0].scrollHeight});
            self.cursor = data.cursor;
        };

        self.poll(self.default_timeout);
    };

});