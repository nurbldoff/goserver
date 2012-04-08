import random
import textwrap
import unittest

from game import check_move, IllegalMove


class TestCheckMove(unittest.TestCase):

    def setUp(self):
        self.size = 5

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

    def test_position_not_taken(self):
        previous_moves = self._create_moves([(1, 2), (3, 4)])
        move = {"player": 0, "position": (1, 3)}
        self.assertEquals(check_move(move, previous_moves, self.size), [])

    def test_position_taken(self):
        previous_moves = self._create_moves([(1, 2), (3, 4)])
        move = {"player": 0, "position": (1, 2)}
        with self.assertRaises(IllegalMove):
            check_move(move, previous_moves, self.size)

    def test_no_freedoms(self):
        previous_moves = self._create_moves([(1, 0),
                                         (0, 1), (2, 1),
                                             (1, 2)], color=1)
        move = {"player": 0, "position": (1, 1)}
        with self.assertRaises(IllegalMove):
            check_move(move, previous_moves, self.size)

    def test_some_freedoms(self):
        previous_moves = self._create_moves([(1, 0),
                                         (0, 1), (2, 1),
                                             (1, 2)])
        move = {"player": 0, "position": (1, 1)}
        self.assertEquals(check_move(move, previous_moves, self.size), [])

    def test_part_of_small_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++O++
                                                          +O+X+
                                                          ++O++
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(check_move(move, previous_moves, self.size), [])

    def test_part_of_small_group_without_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++OO+
                                                          +O+XO
                                                          ++OO+
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        with self.assertRaises(IllegalMove):
            check_move(move, previous_moves, self.size)

    def test_part_of_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOO+
                                                          OX+XO
                                                          +OOXO
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(check_move(move, previous_moves, self.size), [])

    def test_part_of_group_taking_the_last_freedom(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOO+
                                                          OX+XO
                                                          +OOXO
                                                          +++O+""")
        move = {"player": 0, "position": (2, 2)}
        with self.assertRaises(IllegalMove):
            check_move(move, previous_moves, self.size)

    def test_part_of_edge_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOOO
                                                          OX+XX
                                                          +OOXX
                                                          ++++O""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(check_move(move, previous_moves, self.size), [])

    def test_part_of_edge_group_with_freedoms(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +OOOO
                                                          OX+XX
                                                          +OOXX
                                                          +++OO""")
        move = {"player": 0, "position": (2, 2)}
        with self.assertRaises(IllegalMove):
            check_move(move, previous_moves, self.size)

    def test_capture_single_stone(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          ++X++
                                                          +XOX+
                                                          +++++
                                                          +++++""")
        move = {"player": 0, "position": (2, 3)}
        self.assertEquals(check_move(move, previous_moves, self.size),
                          [2])

    def test_capture_edge_group(self):
        previous_moves = self._create_moves_from_ascii("""+++++
                                                          +++XX
                                                          +++OO
                                                          +++XX
                                                          +++++""")
        move = {"player": 0, "position": (2, 2)}
        self.assertEquals(check_move(move, previous_moves, self.size),
                          [2, 3])
