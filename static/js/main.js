requirejs.config({
    baseUrl: '/static/js/libs',
    paths: {
        app: '../app'
    },
    shim: {
        d3: {
            exports: 'd3'
        }
    }
});


// Start the main app logic.
require(
    ['jquery', 'knockout-2.2.1', 'd3', 'app/game', 'app/chat'],
    function ($, ko, d3, GameViewModel, ChatViewModel) {
        //jQuery, canvas and the app/sub module are all
        //loaded and can be used here now.

        var gameid = $("#game-id").val(),
            username = $("#username").val(),
            mv = new GameViewModel(gameid, username),
            chat = new ChatViewModel(gameid, username);
        ko.applyBindings(mv, document.getElementById("game-info"));
        ko.applyBindings(chat, document.getElementById("chat"));
    }
);