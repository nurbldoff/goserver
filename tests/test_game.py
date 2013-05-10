import random
import textwrap
import unittest

from game import MoveValidator, IllegalMove, BLACK, WHITE, FREE, OUTSIDE


class TestCheckMove(unittest.TestCase):

    def setUp(self):
        self.size = 5
        self.validator = MoveValidator(self.size)

    def _create_moves(self, positions, color=None):
        moves = []
        for i, pos in enumerate(positions):
            moves.append(dict(position=pos,
                              player=i % 2 if color is None else color))
        return moves

    def _create_moves_from_ascii(self, ascii):
        moves = []
        for row, line in enumerate(ascii.split()):
            for col, char in enumerate(line):
                if char != "+":
                    moves.append(dict(position=(col, row),
                                      player=["X", "O"].index(char)))
        return moves

    def _make_board(self, ascii="""+++++
                                   +OOO+
                                   OX+XO
                                   +OOXO
                                   +++O+"""):
        self.validator.build_board(self._create_moves_from_ascii(ascii))

    # Tests for helper functions

    def test_peek(self):
        self._make_board()
        self.assertEquals(self.validator.peek((0, 0)), FREE)
        self.assertEquals(self.validator.peek((2, 10)), OUTSIDE)
        self.assertEquals(self.validator.peek((2, 1)), WHITE)
        self.assertEquals(self.validator.peek((1, 2)), BLACK)

    def test_connected(self):
        self._make_board()
        self.assertEquals(set(self.validator.connected((0, 0))),
                          set([(1, 0), (0, 1)]))
        self.assertEquals(set(self.validator.connected((1, 1))),
                          set([(2, 1), (0, 1), (1, 0), (1, 2)]))

    def test_peek_neigbors(self):
        self._make_board()
        self.assertEquals(set(self.validator.peek_neighbors((0, 0))),
                          set([FREE, FREE]))
        self.assertEquals(set(self.validator.peek_neighbors((1, 1))),
                          set([FREE, FREE, WHITE, BLACK]))

    def test_get_group(self):
        self._make_board()
        self.assertEquals(self.validator.get_group((0, 0)), set())
        self.assertEquals(self.validator.get_group((1, 1)),
                          set([(1, 1), (2, 1), (3, 1)]))
        self.assertEquals(self.validator.get_group((1, 2)),
                          set([(1, 2)]))

    def test_freedoms(self):
        self._make_board()
        self.assertEquals(self.validator.freedoms((0, 0)), set())
        self.assertEquals(self.validator.freedoms((1, 1)),
                          set([(1, 0), (2, 0), (3, 0),
                               (0, 1), (4, 1), (2, 2)]))
        self.assertEquals(self.validator.freedoms((1, 2)), set([(2, 2)]))

    # Tests for 'check'

    def test_check_position_not_taken(self):
        previous_moves = self._create_moves([(1, 2), (3, 4)])
        move = {"player": 0, "position": (1, 3)}
        self.assertEquals(self.validator.check(move, previous_moves), [])

    def test_check_position_taken(self):
        previous_moves = self._create_moves([(1, 2), (3, 4)])
        move = {"player": 0, "position": (1, 2)}
        with self.assertRaises(IllegalMove):
            self.validator.check(move, previous_moves)

    def test_check_no_freedoms(self):
        previous_moves = self._create_moves([(1, 0),
                                         (0, 1), (2, 1),
                                             (1, 2)], color=1)
        move = {"player": 0, "position": (1, 1)}
        with self.assertRaises(IllegalMove):
            self.validator.check(move, previous_moves)

    def test_check_some_freedoms(self):
        previous_moves = self._create_moves([(1, 0),
                                         (0, 1), (2, 1),
                                             (1, 2)])
        move = {"player": 0, "position": (1, 1)}
        self.assertEquals(self.validator.check(move, previous_moves), [])

    def test_check_part_of_small_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++O++
                                                          +O+X+
                                                          ++O++
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves), [])

    def test_check_part_of_small_group_without_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++OO+
                                                          +O+XO
                                                          ++OO+
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        with self.assertRaises(IllegalMove):
            self.validator.check(move, previous_moves)

    def test_check_part_of_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOO+
                                                          OX+XO
                                                          +OOXO
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves), [])

    def test_check_part_of_group_taking_the_last_freedom(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOO+
                                                          OX+XO
                                                          +OOXO
                                                          +++O+""")
        move = {"player": 0, "position": (2, 2)}
        with self.assertRaises(IllegalMove):
            self.validator.check(move, previous_moves)
        move = {"player": 1, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves),
                          [4, 5, 9])

    def test_check_part_of_edge_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOOO
                                                          OX+XX
                                                          +OOXX
                                                          ++++O""")
        move = {"player": 1, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves), [5])
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves), [])

    def test_check_capture_single_stone(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++X++
                                                          +XOX+
                                                          +++++
                                                          +++++""")
        move = {"player": 0, "position": (2, 3)}
        self.assertEquals(self.validator.check(move, previous_moves), [2])

    def test_check_capture_edge_group(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +++XX
                                                          +++OO
                                                          +++XX
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(self.validator.check(move, previous_moves),
                          [2, 3])
