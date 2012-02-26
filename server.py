import os

import tornado.ioloop
import tornado.web
from tornado import websocket
from tornado.escape import json_encode

from game import Game, Player, IllegalMove


class BaseHandler(tornado.web.RequestHandler):

    def get_login_url(self):
        return u"/login"

    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if user_json:
            return tornado.escape.json_decode(user_json)
        else:
            return None


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if not self.current_user in users:
            self.redirect("/login")
        new = self.get_argument('new', default=None)
        if new == "game":  # starting a new game!
            new_game_id = len(games)
            player = users[self.current_user]["player"]
            games[new_game_id] = Game(black_player=player, white_player=None)
            self.redirect("/game/%d" % new_game_id)
        else:
            self.render("templates/game_list.html", title="Ongoing games",
                        games=games)


class ClientSocket(websocket.WebSocketHandler):

    def __init__(self, *args, **kwargs):
        self.game = None
        websocket.WebSocketHandler.__init__(self, *args, **kwargs)

    #@tornado.web.authenticated
    def open(self):
        game_id = self.get_argument('gameid', default=None)
        if game_id:
            self.game = games[int(game_id)]
            self.game.sockets.append(self)
            print "WebSocket opened to game", game_id

    def on_message(self, message):
        pass

    def on_close(self):
        print "WebSocket closed."
        self.game.sockets.remove(self)


class GameHandler(BaseHandler):

    def initialize(self):
        pass

    @tornado.web.authenticated
    def get(self, game_id, *args, **kwargs):
        game = games.get(int(game_id), None)
        if not game:  # game doesn't exist!
            self.redirect("/")
            return
        move = self.get_argument('move', default=None)
        get = self.get_argument('get', default=None)
        if move:
            player = users[self.current_user]["player"]
            print "Player %s made a move!" % player.name
            position = [int(x) for x in move.split(",")]
            try:
                game.move(position, player)
                s = game.get_game_state()
                #s["message"] = "%s: %d, %d" % (self.current_user, position[0],
                #                              position[1])
                for socket in game.sockets:
                    socket.write_message(json_encode(s))
            except IllegalMove:
                pass
        elif get == "board":
            s = game.get_game_state()
            if (game.players[0] != users[self.current_user]["player"] and
                not all(game.players)):
                s["message"] = "Joined the game as White!"
            elif (game.players[0] == users[self.current_user]["player"] and
                  not all(game.players)):
                s["message"] = "Waiting for an opponent..."
            else:
                s["message"] = ""
            self.write(json_encode(s))
        elif (game.players[0] != users[self.current_user]["player"] and
              not all(game.players)):   # this game has no opponent - join it
            game.players[1] = users[self.current_user]["player"]
            print "players", [g.name for g in game.players if g]
            self.render("templates/game.html", title="Gospel")
            s = game.get_game_state()
            s["message"] = "User '%s' has joined the game!" % self.current_user
            for socket in game.sockets:
                socket.write_message(json_encode(s))
        else:
            self.render("templates/game.html", title="Gospel")


class LoginHandler(BaseHandler):

    def get(self):
        self.render("templates/login.html",
                    next=self.get_argument("next", default="/"),
                    error=self.get_argument("error", default=""))

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        if username not in users:
            self.set_current_user(username)
            users[username] = {"password": password,
                               "player": Player(name=username,
                                                user=self.current_user)}

            self.redirect(self.get_argument("next", u"/"))
        elif username in users and users[username]["password"] == password:
            self.set_current_user(username)
            print username, password, self.current_user
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = (u"?error=" +
                         tornado.escape.url_escape("Login incorrect."))
            self.redirect(u"/login" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


users = {"black": {"password": "black",
                   "player": Player(name="black", user="black")},
         "white": {"password": "white",
                   "player": Player(name="white", user="white")}}

#games = dict([(i, Game(black_player=users["black"]["player"],
#                       white_player=users["white"]["player"])
#                       ) for i in (0, 1, 2)])

games = {}

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    "login_url": "/login",
    "debug": True
}

application = tornado.web.Application([
            (r"/", MainHandler),
            (r"/login", LoginHandler),
            (r"/socket", ClientSocket),
            (r"/game/([0-9]+)", GameHandler)
            ], **settings)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
