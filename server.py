import os
import time

import tornado.ioloop
import tornado.web
from tornado import websocket
from tornado.escape import json_encode
from tornado.options import define, options

from game import Game, IllegalMove, NoOpponent, PositionAlreadyTaken


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
            player = users[self.current_user]
            game = Game(black_player=player, white_player=None)
            games[new_game_id] = game
            self.redirect("/game/%d" % new_game_id)
            game.add_message(time.time(), "<server>",
                "%s started this game, waiting for an opponent." %
                             self.current_user)
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
        get = self.get_argument('get', default=None)
        fr = int(self.get_argument('from', default=0))
        user = users.get(self.current_user, None)
        if user is None:
            self.redirect("/login")

        elif get == "moves":
            print "Player '%s' requested moves for game %s" % (
                self.current_user, game_id)
            moves = game.get_moves(fr)
            self.write(json_encode(moves))

        elif get == "board":  # requesting the board
            print "Player '%s' requested board for game %s" % (
                self.current_user, game_id)
            s = game.get_game_state()
            self.write(json_encode(s))

        elif get == "state":  # requesting complete game info
            print "Player '%s' requested state for game %s" % (
                self.current_user, game_id)
            s = game.get_game_state()
            s["id"] = game_id
            self.write(json_encode(s))

        elif get == "chat":  # requesting chat messages
            print "Player '%s' requested chat from %d for game %s" % (
                self.current_user, fr, game_id)
            reply = game.messages[fr:]
            self.write(json_encode(reply))
            print json_encode(reply)

        elif user and game.players[0] != user and not all(game.players):
            # this game has no opponent - join it
            print "Player '%s' joined game %s" % (self.current_user, game_id)
            game.add_message(time.time(), "<server>",
                "%s has joined the game! Black may begin." % self.current_user)
            game.add_player(users[self.current_user], 0)
            self.render("templates/game.html")

        else:
            self.render("templates/game.html")

    def post(self, game_id):
        game = games.get(int(game_id), None)
        move = self.get_argument('move', default=None)
        message = self.get_argument('message', default=None)

        if move:  # making a move
            player = users.get(self.current_user, None)
            print "Player %s made a move..." % player["name"],
            position = [int(x) for x in move.split(",")]
            try:
                game.make_move(time.time(), position, player)
            except NoOpponent:
                print "Player %s has no opponent!" % player["name"]
            except PositionAlreadyTaken:
                print "Position taken!"
            except IllegalMove:
                print "Not player %s's turn!" % player["name"]
            except KeyError:
                print "No such user: %s!" % self.current_user
            else:
                print "OK"
        elif message:
            game.add_message(time.time(), self.current_user, message)
            print "posted:", message

class LoginHandler(BaseHandler):

    def get(self):
        self.render("templates/login.html",
                    next=self.get_argument("next", default="/"),
                    error=self.get_argument("error", default=""))

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        if username not in users:
            print "New user %s!" % username
            self.set_current_user(username)
            users[username] = {"password": password,
                               "name": username}
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


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        #self.set_current_user(None)
        self.redirect("/")


users = {"test": {"password": "testpass", "name": "test"}}

games = {}


class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/login",
            debug=True
            )
        handlers = [
            (r"/", MainHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/socket", ClientSocket),
            (r"/game/([0-9]+)", GameHandler)
            ]
        tornado.web.Application.__init__(self, handlers, **settings)


define("port", default=8889, help="run on the given port", type=int)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
