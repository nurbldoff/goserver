import time
from collections import namedtuple, defaultdict

from tornado.escape import json_encode

DEBUG=False


class IllegalMove(Exception):
    pass

# Some constants for what can possibly be at a position
BLACK, WHITE, FREE, OUTSIDE = 0, 1, 2, 3


class MoveValidator(object):

    """Used to validate moves."""

    def __init__(self, size=19):
        self.size = size
        self.board = {}
        self.moves = []

    def check(self, move, previous_moves):
        """Validate a move and return any captures.

        Takes a move and a list of previous moves, and checks that the
        move is legal. If it is, returns a list containing the indexes
        (in the move history) of any captured stones. If it's not
        legal, raises IllegalMove with an explanation.
        """

        captures = set()
        player = move["player"]
        position = move["position"]
        opponent = [BLACK, WHITE][not player]
        self.build_board(previous_moves)

        # check if the move is possible at all
        if self.peek(position) in (BLACK, WHITE, OUTSIDE):
            raise IllegalMove("No room!")

        # OK, let's put a hypothetical stone there.
        self.board[position] = player

        # check if the move is potentially suicidal, i.e. no freedoms for
        # the stone or group.
        maybe_suicide = not self.freedoms(position)
        # It's OK to use up a group's last freedom IFF it causes the
        # immediate capture of opponent stones. We need to check that later.

        # TODO: check for Ko...

        # Now we check if the move makes any captures.
        for stone in self.connected(position, only=[opponent]):
            gr = self.get_group(stone)
            if not self.get_group_freedoms(gr):
                captures.update(gr)

        # completing the suicide check
        if maybe_suicide and len(captures) == 0:
            raise IllegalMove("Suidice move!")

        print "captures", captures
        return self.positions_to_indexes(captures, previous_moves)

    def build_board(self, moves):
        """Build a board representation from the list of all moves."""
        self.board = {}
        new_moves = moves[len(self.moves):]
        for m in new_moves:
            color = [BLACK, WHITE][m["player"]]
            position = m.get("position", False)
            if position:
                self.board[tuple(position)] = color
            captures = m.get("captures", None)
            if captures is not None:
                for cap in captures:
                    del self.board[tuple(moves[cap]["position"])]
        self.moves = moves
    # board = dict([(tuple(m["position"]), [BLACK, WHITE][m["player"]])
    #               for i, m in enumerate(previous_moves)
    #               if m["position"] and not m.get("captured",
    #               False)])
    def print_board(self, board):
        for x in xrange(19):
            for y in xrange(19):
                stone = board.get((x, y))
                if stone is not None:
                    print ("X ", "O ")[stone],
                else:
                    print ". ",
            print

    # define some helper functions
    def peek(self, pos):
        "Returns what's at the requested position"
        x, y = pos
        if (0 <= x < self.size) and (0 <= y < self.size):
            return self.board.get(pos, FREE)
        else:
            return OUTSIDE

    def connected(self, pos, only=[BLACK, WHITE, FREE]):
        """Returns the positions 4-connected to a position, i.e. the direct
        neighbors, if what's there is also in the 'only' argument"""
        x, y = pos
        conn = [p for p in ((x, y + 1), (x - 1, y), (x, y - 1), (x + 1, y))
                if self.peek(p) in only]
        return conn

    def peek_neighbors(self, pos):
        "Returns a tuple of the four neighbors"
        return map(self.peek, self.connected(pos))

    def get_group(self, pos, group=None):
        """Get all stones connected to the given stone"""
        if group is None:
            group = set()
        color = self.peek(pos)
        if color in (BLACK, WHITE):  # only stones can be grouped
            group.add(pos)
            for friend in [n for n in self.connected(pos, only=[color])
                           if not n in group]:
                group = self.get_group(friend, group)
        return group

    def get_group_freedoms(self, group):
        """Returns all freedoms for a given set of stones"""
        freedoms = set()
        #color = peek(iter(group).next())  # ugly way of getting one element
        for stone in group:
            freedoms = freedoms.union(set(self.connected(stone, only=[FREE])))
        return freedoms

    def freedoms(self, pos):
        """Get direct or indirect freedoms for a given stone"""
        return self.get_group_freedoms(self.get_group(pos))

    def positions_to_indexes(self, poss, previous_moves):
        """Convert positions on the board into move indexes, for storage"""
        tmp = set(poss)
        indexes = []
        i = len(previous_moves) - 1
        while tmp:
            m = tuple(previous_moves[i]["position"])
            if m in tmp:
                indexes = [i] + indexes
                tmp.remove(m)
            i -= 1  # count backwards, because only the latest move at the
                    # specific position can be captured now, obviously
        return indexes


class Game(object):
    """
    This class represents a game of Go.
    """

    def __init__(self, id=-1, black_player=None, white_player=None,
                 board_size=19, handicap=0, time=None, dbdict=None):
        if dbdict is not None:
            self.from_dbdict(dbdict)
        else:
            self.id = id
            self.players = [black_player, white_player]
            self.handicap = handicap
            self.moves = []
            self.finished = False
            self.resigned = None
            self.size = board_size
        self.validator = MoveValidator(board_size)

    def get_active_player_index(self):
        return len(self.moves) % 2

    def get_active_player(self):
        return self.players[self.get_active_player_index()]

    def add_player(self, user, handicap):
        """Add a white player to an existing game."""
        self.players[1] = user
        self.handicap = handicap

    def validate_move(self, move):
        """Try to make the move and calculate captures.
        Will raise errors if something goes wrong."""
        if not all(self.players):
            raise IllegalMove("No opponent in the game yet!")
        if move["player"] != self.get_active_player_index():
            raise IllegalMove("Wrong player!")
        if move["position"] is None:
            return []
        else:
            return self.validator.check(move, self.moves)

    def make_move(self, time, position, player, validate=True, resign=False):
        """Make a move."""
        if self.finished:
            raise IllegalMove("Game is already finished!")

        if player not in self.players:
            raise IllegalMove("Not a player in this game!")

        move = dict(player=self.players.index(player),
                    position=tuple(position) if position else None,
                    time=time, n=len(self.moves), resign=resign)

        if resign:
            self.resign(player)
        else:
            captures = self.validate_move(move)
            if captures:
                move["captures"] = captures
                print "Player '%s' captured %d stones!" % (player,
                                                           len(captures))
            print "Valid move!"
            self.moves.append(move)

            #Check if the match is over (both players pass)
            if validate and len(self.moves) >= 2:
                m1, m2 = self.moves[-2:]
                #print m1, m2
                if m1["position"] is None and m2["position"] is None:
                    self.finish()

        return move

    def finish(self):
        """End the game."""
        print "Game finished!"
        self.finished = True
        # Calculate points, etc

    def resign(self, player):
        self.resigned = self.players.index(player)
        self.finish()

    def get_game_state(self):
        state = {
            "id": self.id,
            "finished": self.finished,
            "board_size": self.size,
            "black": self.players[0],
            "white": self.players[1],
            "moves": self.get_moves()
            }
        return state

    def get_moves(self, start=0):
        """Return a dict of all moves from number <start>"""
        if start == -1:
            start = len(self.moves) - 2
        moves = self.moves[start:]
        res = []
        for i, m in enumerate(moves):
            move = dict(m)
            res.append(move)
        return moves

    def build_dbdict(self):
        """Return a dict containing all info about the game, for storage"""
        dbdict = self.get_game_state()
        dbdict["_id"] = dbdict["id"]
        dbdict["time"] = time.time()
        del dbdict["id"]
        #print dbdict
        return dbdict

    def from_dbdict(self, dbdict):
        """Restore a game object from a dbdict representation"""
        self.id = dbdict["_id"]
        self.players = [dbdict["black"], dbdict["white"]]
        #self.handicap = dbdict["handicap"]
        self.moves = dbdict["moves"]
        self.finished = dbdict["finished"]
        self.size = dbdict["board_size"]
