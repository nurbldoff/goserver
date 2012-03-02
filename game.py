import time
from collections import namedtuple

from tornado.escape import json_encode

class IllegalMove(Exception):
    pass


class PositionAlreadyTaken(IllegalMove):
    pass


class NoOpponent(IllegalMove):
    pass


class Board(object):
    def __init__(self, size):
        self.positions = [[[] for i in range(size)] for j in range(size)]

    def place_stone(self, player, position, cleanup=True):
        row, col = position
        if self.positions[row][col]:
            raise PositionAlreadyTaken
        else:
            self.positions[row][col].append(player)
            if cleanup:
                return self.check_for_captures()
            else:
                return []

    def check_for_captures(self):
        return []


class Game(object):
    """
    This class represents a game of Go.
    """

    def __init__(self, black_player, white_player=None,
                 board_size=19, handicap=0, time=None):
        self.players = [black_player, white_player]
        self.handicap = handicap
        self.moves = []
        self.time = time

        self.captures = [0, 0]
        self.board = Board(board_size)

        self.messages = []  # list of status and chat messages
        self.sockets = []

    def get_active_player_index(self):
        return len(self.moves) % 2

    def get_active_player(self):
        return self.players[self.get_active_player_index()]

    def announce_move(self):
        """Announce over websockets that a move was made. It's then up to the
        clients to request it, if they are interested."""
        for socket in self.sockets:
            socket.write_message("move")

    def announce_chat(self):
        """Announce over websockets that a chatmessage was sent."""
        for socket in self.sockets:
            socket.write_message("chat")

    def announce_join(self):
        """Announce over websockets that a player has joined the game."""
        for socket in self.sockets:
            socket.write_message("join")

    def add_player(self, user, handicap):
        """Add a white player to an existing game."""
        self.players[1] = user
        self.handicap = handicap
        self.announce_join()

    def validate_move(self, player, position):
        """Check if a move is legal"""
        # here should be some go logic to check if the move is OK
        if not all(self.players):
            raise NoOpponent
        if player != self.get_active_player():
            print player, self.get_active_player()
            raise IllegalMove

    def make_move(self, time, position, player=None):
        """Make a move."""
        self.validate_move(player, position)
        captures = self.board.place_stone(player, position)
        self.moves.append({"player": player,
                           "position": position,
                           "time": time})
        self.captures[self.get_active_player_index()] += len(captures)
        self.announce_move()

    def add_message(self, time, user, content):
        """Send a chat message"""
        self.messages.append({"time": time, "user": user, "content": content})
        self.announce_chat()

    def get_board_string(self):
        s = ""
        n = 0
        for row in self.board.positions:
            for place in row:
                if place:
                    if self.players[0] in place:
                        s += "b"
                    elif self.players[1] in place:
                        s += "w"
                else:
                    s += "."
        return s

    def get_game_state(self):
        state = {}
        state["type"] = "board"
        state["black"] = self.players[0]["name"]
        state["white"] = self.players[1]["name"] if self.players[1] else None
        state["active_player"] = ("b", "w")[self.get_active_player_index()]
        if self.moves:
            state["last_move"] = tuple(self.moves[-1]["position"])
        else:
            state["last_move"] = (-1, -1)
        state["board"] = self.get_board_string()
        #return ";".join([active_player, last_move, board])
        return state

    def get_moves(self, start=0):
        """Return a list of all moves from number <start>, defaults to just
        the last move."""
        if start == -1:
            start = len(moves) - 2
        moves = self.moves[start:]
        return [dict([("n", start+i)] + m) for i, m in enumerate(moves.items())]
