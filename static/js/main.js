requirejs.config({
    baseUrl: '/static/js/libs',
    paths: {
        app: '../app'
    },
    shim: {
        d3: {exports: 'd3'}
    }
});


// Start the main app logic.
require(
    ['jquery', 'knockout', 'd3', 'knockout-postbox', 'app/game', 'app/chat'],
    function ($, ko, d3, postbox, GameViewModel, ChatViewModel) {
        var gameid = $("#game-id").val(),
            username = $("#username").val(),
            mv = new GameViewModel(gameid, username),
            chat = new ChatViewModel(gameid, username);
        ko.applyBindings(mv, document.getElementById("game-info"));
        ko.applyBindings(chat, document.getElementById("chat"));
    }
);