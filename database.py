from itertools import islice

import pymongo
from game import Game


class Database(object):
    """A simple MongoDB database wrapper
    """

    def __init__(self, hostname="localhost", port=27017):
        self.hostname = hostname
        self.port = port
        self.connection = pymongo.Connection(self.hostname, self.port)
        self.db = self.connection.goserver
        self.games = self.db.games
        self.users = self.db.users
        self.messages = self.db.messages

    # === games ===

    def get_game(self, gameid):
        game = self.games.find_one({"_id": gameid})
        if game is not None:
            return Game(dbdict=game)

    def get_games(self, user=None, include_finished=False, n=20):
        search = {}
        if not include_finished:
            search["finished"] = False
        if user is not None:
            search["$or"] = [{"black": user}, {"white": user}]
        games = list(islice(self.games.find(search).sort("time", -1), n))
        return games

    def put_game(self, game):
        self.games.insert(game.build_dbdict())

    def update_game(self, game, fields=None):
        gdict = game.build_dbdict()
        #update = dict([(k, gdict.get(k)) for k in fields])
        self.games.save(gdict)  # do a partial update instead!

    def get_game_moves(self, gameid, cursor):
        """ Return all messages starting with 'start_id', optionally
        for a given room. """
        #game = self.get_game(gameid)
        # search = {}
        # search["_id"] = {"$gt": cursor}

        # This is pretty inefficient too..
        result = list(self.games.find({"_id": gameid}, {"moves": 1}))
        moves = result[0]["moves"]
        return moves[int(cursor):], len(moves)
        #return game.find(search).sort("_id")

    def put_game_moves(self, gameid, moves):
        for move in moves:
            move["_id"] = self.get_new_game_move_id(gameid)
        self.games.update({"_id": int(gameid)}, {"$pushAll": {"moves": moves}})

    def get_new_game_move_id(self, gameid):
        """FIX: see above"""
        game = self.games.find_one(_id=gameid)
        return len(game["moves"])

    def get_new_game_id(self):
        """FIX: This is pretty stupid."""
        return self.games.count()

    # === messages ===

    def get_chat_message(self, msgid):
        return self.messages.find_one({"_id": msgid})

    def get_chat_messages(self, room, cursor):
        """ Return all messages starting with cursor, for a given room."""
        search = {}
        search["_id"] = {"$gt": int(cursor)}
        if room is not None:
            search["room"] = room
        return list(self.messages.find(search).sort("_id"))

    def put_chat_messages(self, messages, room=None):
        for msg in messages:
            msg["_id"] = self.get_new_message_id()
            msg["room"] = room
        self.messages.insert(messages)

    def get_new_message_id(self):
        """FIX: see above"""
        return self.messages.count()

    # === users ===

    def get_user(self, name):
        print "getting user by name:", name
        return self.users.find_one(name=name)

    def put_user(self, user):
        self.users.insert(user)

    def get_new_user_id(self):
        """FIX: see above"""
        return self.users.count()
