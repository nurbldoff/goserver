#!/usr/bin/env python

"""
A server to play Go over the web.

Has a simple "REST" API for clients to communicate:

* POST "/login" to log in, with JSON data:

    {"username": "some_user", "password": "some_pass"}

  Sets a cookie to keep the player logged in. Users are created on
  first login. Currently does no check on the password; it can be
  anything.

* GET "/logout" to log out.


* POST "/game/new" creates a new game, and redirects the client to it.

* POST "/game/123" enters the game with number 123, if it exists.
  If there is only one player in the game, join it as white.
  If the game already has two players, enter as a passive spectator.

* POST "/game/123/updates" is used to watch a game for moves, by
  polling. Send "cursor=N" as argument, where N is the number of the
  move you're waiting for (e.g. 0 at the start). If that move has not
  yet happened, wait. If one or more moves have occurred since N,
  you'll immediately get them as JSON, like this:

    {"cursor": 8, "updates": [{"move": {"position": "1,2", "n"=6}},
                              {"move": {...}}, ...]}

  ...where "cursor" is the new cursor to wait for, and so on.

  "n" is the number of the move, starting with 0.
  A "resign" is indicated by the presence of "resign=true" in the move object.
  A "pass" is indicated by a position of "null", or no position.

* POST "/game/123/move" is used to make moves in a game you're playing.
  As data, send JSON on the format:

    {"position": "4,5", "resign": false}

  Both fields are optional.


* POST "/room/123/message" to send a chat message to the room associated with
  game 123, on the form:

    {"body": "This is a message."}

* POST "/room/123/updates" to watch the room for chat messages. Works like
  watching a game, except updates are on the form:

    {"user": "some_user", "body": "Blabla...", "time": 123456.7890}

  "time" is given as epoch.


Note: Polling is sort of primitive, but it's simple and universally
supported. Take care not to hammer the service with updates requests;
keep timeouts fairly long and, preferably, increase them if there are
no updates.
"""

import logging
import time
import os.path
from collections import defaultdict

import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

from game import Game, IllegalMove
from database import Database


define("port", default=8890, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self, db):

        args = dict(db=db)
        handlers = [
            (r"/login", LoginHandler, args),
            (r"/logout", LogoutHandler, args),
            (r"/", GameListHandler, args),
            (r"/game/new", GameNewHandler, args),
            (r"/game/([0-9]+)", GameHandler, args),
            #(r"/auth/login", AuthLoginHandler),
            #(r"/auth/logout", AuthLogoutHandler),
            (r"/room/([0-9]+)/message", MessageNewHandler, args),
            (r"/room/([0-9]+)/updates", MessageUpdatesHandler, args),
            (r"/game/([0-9]+)/updates", GameUpdatesHandler, args),
            (r"/game/([0-9]+)/state", GameStateHandler, args),
            (r"/game/([0-9]+)/move", GameMoveHandler, args),
        ]
        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            autoescape="xhtml_escape",
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self, db):
        self.db = db

    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if not user:
            return None
        return user   # tornado.escape.json_decode(user_json)


class ChatMixin(object):
    waiters = defaultdict(set)
    #cache = defaultdict(list)
    cache_size = 200

    def wait_for_updates(self, room, callback, cursor=None):
        """Adds a request to the waiting list for the given room"""
        cls = ChatMixin
        print "Message cursor:", cursor, "room:", room
        if cursor:
            recent = db.get_chat_messages(room, cursor)
            if recent:
                callback(dict(updates=recent, cursor=recent[-1]["_id"]))
                return
        cls.waiters[room].add(callback)

    def cancel_wait(self, room, callback):
        cls = ChatMixin
        cls.waiters[room].remove(callback)

    def new_updates(self, room, updates, cursor=None):
        """Send out updates to clients waiting on the given room"""
        cls = ChatMixin
        logging.info("Sending update on room '%s' to %d listeners" %
                     (room, len(cls.waiters[room])))
        for callback in cls.waiters[room]:
            try:
                callback(dict(updates=updates, cursor=cursor))
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.waiters[room] = set()
        db.put_chat_messages(updates, room)


class GameMixin(object):
    waiters = defaultdict(set)
    #cache = defaultdict(list)
    cache_size = 200

    def wait_for_updates(self, gameid, callback, cursor=None):
        """Adds a request to the waiting list for the given room"""
        cls = GameMixin
        print "Game cursor:", cursor
        if cursor is not None:
            recent, cursor = db.get_game_moves(gameid, cursor)
            if recent:
                callback([dict(move=move) for move in recent], cursor)
                return
        cls.waiters[gameid].add(callback)

    def cancel_wait(self, gameid, callback):
        cls = GameMixin
        cls.waiters[gameid].remove(callback)

    def new_updates(self, gameid, updates, cursor=None):
        """Send out updates to clients waiting on the given room"""
        cls = GameMixin
        logging.info("Sending update %s on room '%s' to %d listeners" %
                     (updates, gameid, len(cls.waiters[gameid])))
        for callback in cls.waiters[gameid]:
            try:
                callback(updates, cursor)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.waiters[gameid] = set()

    # def get_game(self, gameid):
    #     game = game_cache.get(gameid)
    #     if game is None:
    #         game = db.get_game(gameid)
    #         if game is not None:
    #             game_cache.put(game)
    #     return game

    # def update_game(self, game):
    #     game_cache.put(game)

    def send_message(self, gameid, body, user="[SERVER]"):
        ChatMixin().new_updates(gameid, [dict(user=user, time=time.time(),
                                              body=body)])


class GameListHandler(BaseHandler, GameMixin):
    @tornado.web.authenticated
    def get(self):
        user = self.get_argument("user", None)
        print "user:", user
        games = db.get_games(user=user)
        #games.sort(key=lambda x: x.get("time", 0), reverse=True)
        self.render("game_list.html", games=games,
                    username=self.current_user)


class GameHandler(BaseHandler, GameMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self, gameid):
        gameid = int(gameid)
        game = db.get_game(gameid)
        if game is not None:
            black, white = game.players
            # Check if the game is waiting for an opponent and, in
            # that case, we join it.
            if white is None and self.current_user != black:
                game.players[1] = self.current_user
                db.update_game(game)
                join = dict(user=self.current_user, time=time.time())
                update = dict(join=join)
                self.new_updates(gameid, [update])
                message = "User '%s' has joined the game as white!" % \
                                                            self.current_user
                self.send_message(gameid, message)
            gamedict = game.get_game_state()
            messages = db.get_chat_messages(gameid, 0)
            gamedict["messages"] = messages
            self.render("index.html", gameid=gameid,
                        username=self.current_user)


class GameNewHandler(BaseHandler, GameMixin):
    """Create a new game"""
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self):
        new_game_id = self.db.get_new_game_id()
        board_size = int(self.get_argument("size", 19))
        player = self.current_user
        game = Game(id=new_game_id, black_player=player,
                    board_size=board_size)
        db.put_game(game)
        self.send_message(game.id, "Welcome, '%s'!" % self.current_user)
        self.send_message(game.id, "You have started a new %dx%d game." %
                          (2 * (board_size,)))
        self.send_message(game.id, "Now we just have to wait for an opponent.")
        self.redirect("/game/" + str(new_game_id))


class GameMoveHandler(BaseHandler, GameMixin):
    @tornado.web.authenticated
    def post(self, gameid, **kwargs):
        gameid = int(gameid)
        game = db.get_game(gameid)
        print "Move in game", game.id, "from player", self.current_user
        print self.request.arguments
        position = self.get_argument("position")

        if position == "null":
            position = None
        else:
            position = [int(p) for p in position.split(",")]
        resign = self.get_argument("resign", False)
        # TODO: This stuff should be unnecessary; figure out why it isn't
        if isinstance(resign, str):
            resign = resign.tolower() == "true"

        try:
            move = game.make_move(time=time.time(),
                                  position=position,
                                  player=self.current_user,
                                  validate=True, resign=resign)
            db.put_game_moves(gameid, [move])
            update = dict(move=move)
            color = ["Black", "White"][move["player"]]
            if position is None:
                if resign:
                    self.send_message(gameid, "%s (%s) resigned." %
                                      (color, self.current_user))
                else:
                    self.send_message(gameid, "%s (%s) passed." %
                                      (color, self.current_user))
            else:
                if move.get("captures"):
                    caps = len(move["captures"])
                    self.send_message(gameid, "%s (%s) captured %d stone%s." %
                                      (color, self.current_user,
                                       caps, "s" if caps > 1 else ""))

            if game.finished:
                update["status"] = dict(finished=True)
                self.send_message(gameid, "The game has ended!")
                self.send_message(gameid,
                                  "(Score counting not yet implemented.)")
            self.new_updates(gameid, [update], cursor=move["n"] + 1)
        except IllegalMove, e:
            print "Illegal Move:", e.message
            update = {"error": "Illegal Move:" + e.message}
        #print self.get_argument("position")
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        elif update:
            self.write(update)


class GameStateHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self, game_id):
        game_id = int(game_id)
        game = db.get_game(game_id)
        if game:
            s = game.get_game_state()
            self.finish(s)
        else:
            return None


class GameUpdatesHandler(BaseHandler, GameMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, game_id):
        game_id = int(game_id)
        self.game_id = game_id
        cursor = self.get_argument("cursor")
        cursor = None if cursor == "null" else cursor
        self.wait_for_updates(game_id, self.on_new_updates, cursor)

    def on_new_updates(self, updates, cursor):
        # Closed client connection
        if self.request.connection.stream.closed():
            return

        self.finish(dict(updates=updates, cursor=cursor))

    def on_connection_close(self):
        self.cancel_wait(self.game_id, self.on_new_updates)


class MessageNewHandler(BaseHandler, ChatMixin):
    @tornado.web.authenticated
    def post(self, gameid):
        gameid = int(gameid)
        print self.request.arguments
        #game = get_game(gameid)
        update = {
            "_id": db.get_new_message_id(),
            "time": time.time(),
            "user": self.current_user,
            "body": self.get_argument("body"),
            }
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(update)
        self.new_updates(gameid, [update], update["_id"])


class MessageUpdatesHandler(BaseHandler, ChatMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, room):
        room = int(room)
        self.room = room
        cursor = self.get_argument("cursor", 0)
        self.wait_for_updates(room, self.on_new_updates, cursor)

    def on_new_updates(self, updates):
        # Closed client connection
        if self.request.connection.stream.closed():
            return

        self.finish(updates)

    def on_connection_close(self):
        self.cancel_wait(self.room, self.on_new_updates)


class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect(ax_attrs=["name"])

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        self.set_secure_cookie("user", tornado.escape.json_encode(user))
        self.redirect("/")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.write("You are now logged out")


class LoginHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("login.html",
                    next=self.get_argument("next", default="/"),
                    error=self.get_argument("error", default=""))

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        self.set_current_user(username)
        self.db.put_user(dict(_id=self.db.get_new_user_id(),
                              name=username, password=password))
        self.redirect(self.get_argument("next", u"/"))
        # if username not in users:
        #     print "New user %s!" % username
        #     self.set_current_user(username)
        #     users[username] = {"password": password,
        #                        "name": username}
        #     self.redirect(self.get_argument("next", u"/"))
        # elif username in users and users[username]["password"] == password:
        #     self.set_current_user(username)
        #     print username, password, self.current_user
        #     self.redirect(self.get_argument("next", u"/"))
        # else:
        #     error_msg = (u"?error=" +
        #                  tornado.escape.url_escape("Login incorrect."))
        #     self.redirect(u"/login" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", user)
                #tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        #self.set_current_user(None)
        self.redirect("/")


def timer_callback():
    pass
    #print "Timer called at time:", time.time()


def main():
    tornado.options.parse_command_line()
    app = Application(db)
    app.listen(options.port)
    ioloop = tornado.ioloop.IOLoop.instance()
    timer = tornado.ioloop.PeriodicCallback(timer_callback, 1000, ioloop)
    timer.start()
    ioloop.start()

if __name__ == "__main__":
    db = Database()
    main()
