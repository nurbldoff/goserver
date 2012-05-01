#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import logging
import time
import os.path
import uuid
from collections import defaultdict

import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options
from tornado.escape import json_encode

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
            #(r"/game/([0-9]+)", GameHandler, args),
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
        if not user: return None
        return user   # tornado.escape.json_decode(user_json)


class ChatMixin(object):
    waiters = defaultdict(set)
    #cache = defaultdict(list)
    cache_size = 200

    def wait_for_updates(self, room, callback, cursor=None):
        """Adds a request to the waiting list for the given room"""
        cls = ChatMixin
        print "Message cursor:", cursor
        if cursor:
            recent = db.get_chat_messages(room, cursor)
            if recent:
                callback(recent)
                return
        cls.waiters[room].add(callback)

    def cancel_wait(self, room, callback):
        cls = ChatMixin
        cls.waiters[room].remove(callback)

    def new_updates(self, room, updates):
        """Send out updates to clients waiting on the given room"""
        cls = ChatMixin
        logging.info("Sending update on room '%s' to %d listeners" %
                     (room, len(cls.waiters[room])))
        for callback in cls.waiters[room]:
            try:
                callback(updates)
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
        if cursor:
            recent = db.get_game_moves(gameid, cursor)
            if recent:
                callback(recent)
                return
        cls.waiters[gameid].add(callback)

    def cancel_wait(self, gameid, callback):
        cls = GameMixin
        cls.waiters[gameid].remove(callback)

    def new_updates(self, gameid, updates):
        """Send out updates to clients waiting on the given room"""
        cls = GameMixin
        logging.info("Sending update on room '%s' to %d listeners" %
                     (gameid, len(cls.waiters[gameid])))
        for callback in cls.waiters[gameid]:
            try:
                callback(updates)
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
        games = db.get_games(user=user)
        #games.sort(key=lambda x: x.get("time", 0), reverse=True)
        self.render("game_list.html", games=games, user=user)


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
            self.render("index.html", game_data=json_encode(gamedict))


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
        position = self.get_argument("position")
        if position == "null":
            position = None
        else:
            position = [int(p) for p in position.split(",")]
        try:
            move = game.make_move(time=time.time(),
                                  position=position,
                                  player=self.current_user,
                                  validate=True)
            db.update_game(game)
            update = dict(move=move)
            if game.finished:
                update["status"] = dict(finished=True)
                self.send_message(gameid, "The game has ended!")
            self.new_updates(gameid, [update])
            if position is None:
                self.send_message(gameid, "Player '%s' passed." %
                                  self.current_user)
                print "hejsan"
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
            self.finish(json_encode(s))
        else:
            return None


class GameUpdatesHandler(BaseHandler, GameMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, game_id):
        game_id = int(game_id)
        self.game_id = game_id
        cursor = self.get_argument("cursor", None)
        self.wait_for_updates(game_id, self.on_new_updates, cursor)

    def on_new_updates(self, updates):
        # Closed client connection
        if self.request.connection.stream.closed():
            return

        self.finish(dict(updates=updates))

    def on_connection_close(self):
        self.cancel_wait(self.game_id, self.on_new_updates)


class MessageNewHandler(BaseHandler, ChatMixin):
    @tornado.web.authenticated
    def post(self, gameid):
        gameid = int(gameid)
        print self.request.arguments
        #game = get_game(gameid)
        update = {
            "id": db.get_new_message_id(),
            "time": time.time(),
            "user": self.current_user,
            "body": self.get_argument("body"),
            }
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(update)
        self.new_updates(gameid, [update])


class MessageUpdatesHandler(BaseHandler, ChatMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, room):
        room = int(room)
        self.room = room
        cursor = self.get_argument("cursor", None)
        self.wait_for_updates(room, self.on_new_updates, cursor)

    def on_new_updates(self, updates):
        # Closed client connection
        if self.request.connection.stream.closed():
            return

        self.finish(dict(updates=updates))

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
