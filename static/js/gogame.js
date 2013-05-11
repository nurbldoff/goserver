'use strict';

var app = angular.module('GoClient', ['gamePoller', 'BoardExternal']);

app.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('((');
    $interpolateProvider.endSymbol('))'); });

angular.module('gamePoller', ['ngResource']).
    factory('gameData', function ($resource) {
        return $resource('/game/:gameid/updates', {}, {
            query: { method: 'POST', params: {}, isArray: false }
        });
    });

function gameCtrl($scope, $timeout, gameData) {
    $scope.gameid = $("input[id=game-id]").val();
    $scope.moves = [];
    $scope.current_move = 0;
    $scope.cursor = 0;

    $scope.make_move = function (pos) {
        console.log(pos);
    };

    (function tick() {
        gameData.query({gameid: $scope.gameid,
                        cursor: $scope.cursor}, {},
                       function (data) {
                           console.log($scope.cursor, data.cursor);
                           if (data.cursor > $scope.cursor) {
                               angular.forEach(data.updates, function(item) {
                                   var move = item.moves[0];
                                   $scope.moves[move.n] = move;
                               });
                               if ($scope.current_move == $scope.cursor)
                                   $scope.current_move = data.cursor;
                               $scope.cursor = data.cursor;

                           }
                           $timeout(tick, 1000);
                       });


    })();
};
