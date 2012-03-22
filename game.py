import time
from collections import namedtuple, defaultdict

from tornado.escape import json_encode


class IllegalMove(Exception):
    pass


class PositionAlreadyTaken(IllegalMove):
    pass


class NoOpponent(IllegalMove):
    pass


def check_move(move, previous_moves, size=19):
    """Check a move against the rules.
    Returns a list of move indexes for any captured stones.
    Raises IllegalMove if the move could not legally be made.
    """
    # board is a dict, representing the board
    BLACK, WHITE, FREE, OUTSIDE = 0, 1, 2, 3
    board = dict([(m["position"], [BLACK, WHITE][m["player"]])
                  for i, m in enumerate(previous_moves)
                  if m["position"] and not m.get("captured", False)])
    captures = set()
    player = move["player"]
    opponent = [BLACK, WHITE][not player]

    # define some helper functions
    def peek(pos):
        "Returns what's at the requested position"
        if 0 <= pos[0] < size and 0 <= pos[1] < size:
            return board.get(pos, FREE)
        else:
            return OUTSIDE

    def connected(pos, only=[BLACK, WHITE, FREE]):
        """Returns the positions connected to a position, i.e. the direct
        neighbors, if what's there matches the 'only' argument"""
        x, y = pos
        conn = [p for p in ((x, y + 1), (x - 1, y), (x, y - 1), (x + 1, y))
                if peek(p) in only]
        return conn

    def peek_neighbors(pos):
        "Returns a tuple of the four neighbors"
        return map(peek, connected(pos))

    def get_group(pos, group=None):
        """Get all stones connected to the given stone"""
        if group is None: group = set()
        group.add(pos)
        color = peek(pos)
        for friend in [n for n in connected(pos, only=[color])
                       if not n in group]:
            group = get_group(friend, group)
        return group

    def get_group_freedoms(group):
        """Returns all freedoms for a given set of stones"""
        freedoms = set()
        color = peek(iter(group).next())  # ugly way of getting one element
        for stone in group:
            freedoms = freedoms.union(set(connected(stone, only=[FREE])))
        return freedoms

    def freedoms(pos):
        """Get direct or indirect freedoms for a given stone"""
        return get_group_freedoms(get_group(pos))

    def positions_to_indexes(poss):
        """Convert positions on the board into move indexes, for storage"""
        tmp = set(poss)
        indexes = []
        i = len(previous_moves) - 1
        while tmp:
            m = previous_moves[i]["position"]
            if m in tmp:
                indexes = [i] + indexes
                tmp.remove(m)
            i -= 1  # count backwards, because only the latest move at the
                    # specific position can be captured now, obviously
        return indexes

    # check if the move is possible at all
    if peek(move["position"]) in (BLACK, WHITE, OUTSIDE):
        raise IllegalMove

    # OK, let's put a hypothetical stone there.
    board[move["position"]] = player

    # check if the move is potentially suicidal, i.e. no freedoms for
    # the stone or group.
    maybe_suicide = not freedoms(move["position"])
    # It's OK to put a stone i a place without freedoms IFF it causes the
    # immediate capture of opponent stones. We need to check that later.

    # TODO: check for Ko...

    # Now we check if the move makes any captures.
    for stone in connected(move["position"], only=[opponent]):
        gr = get_group(stone)
        if not get_group_freedoms(gr):
            captures.update(gr)

    # completing the suicide check
    if maybe_suicide and len(captures) == 0:
        raise IllegalMove

    return positions_to_indexes(captures)


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

        self.captures = [defaultdict(set), defaultdict(set)]
        self.size = board_size

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

    def validate_move(self, move):
        """Try to make the move and calculate captures.
        Will raise errors if something goes wrong."""
        if not all(self.players):
            raise NoOpponent
        if move["player"] != self.get_active_player_index():
            raise IllegalMove
        return check_move(move, self.moves, self.size)

    def make_move(self, time, position, player):
        """Make a move."""
        move = dict(player=self.players.index(player),
                    position=tuple(position), time=time)
        captures = self.validate_move(move)
        if captures:
            #move["captures"] = captures
            self.captures[self.players.index(player)][len(self.moves)] = \
                set(captures)
            for i in captures:
                self.moves[i]["captured"] = True
            #self.captures[self.players.index(player)] += len(captures)
            print "Player '%s' captured %d stones!" % (player["name"],
                                                       len(captures))
        self.moves.append(move)
        #self.captures[self.get_active_player_index()] += len(captures)
        self.announce_move()

    def add_message(self, time, user, content):
        """Send a chat message"""
        self.messages.append({"time": time, "user": user, "content": content})
        self.announce_chat()

    # def get_board_string(self):
    #     s = ""
    #     n = 0
    #     for row in self.board.positions:
    #         for place in row:
    #             if place:
    #                 if self.players[0] in place:
    #                     s += "b"
    #                 elif self.players[1] in place:
    #                     s += "w"
    #             else:
    #                 s += "."
    #     return s

    def get_game_state(self):
        state = {}
        state["type"] = "state"
        state["board_size"] = self.size
        state["black"] = self.players[0]["name"]
        state["white"] = self.players[1]["name"] if self.players[1] else None
        state["active_player"] = ("b", "w")[self.get_active_player_index()]
        if self.moves:
            state["last_move"] = tuple(self.moves[-1]["position"])
        else:
            state["last_move"] = (-1, -1)
        #state["board"] = self.get_board_string()
        state["moves"] = self.get_moves()
        #return ";".join([active_player, last_move, board])
        return state

    def get_moves(self, start=0):
        """Return a dict of all moves from number <start>"""
        if start == -1:
            start = len(self.moves) - 2
        moves = self.moves[start:]
        res = []
        for i, m in enumerate(moves):
            move = dict(m)
            move["n"] = start + i
            move["captures"] = list(self.captures[m["player"]][start + i])
            res.append(move)
        #res = [dict([("n", start + i)] + m.items())
        #       for i, m in enumerate(moves)]
        return res
