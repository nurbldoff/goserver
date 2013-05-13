#! /usr/bin/env python

from getopt import *
import popen2
import sys
import string
import re
import os
import time

debug = 0


def coords_to_sgf(size, board_coords):
    global debug

    board_coords = string.lower(board_coords)
    if board_coords == "pass":
        return ""
    if debug:
        print "Coords: <" + board_coords + ">"
    letter = board_coords[0]
    digits = board_coords[1:]
    if letter > "i":
        sgffirst = chr(ord(letter) - 1)
    else:
        sgffirst = letter
    sgfsecond = chr(ord("a") + int(size) - int(digits))
    return sgffirst + sgfsecond



class GTP_connection:

    #
    # Class members:
    #   outfile         File to write to
    #   infile          File to read from

    def __init__(self, command):
        try:
            infile, outfile = popen2.popen2(command)
        except:
            print "popen2 failed"
            sys.exit(1)
        self.infile  = infile
        self.outfile = outfile

    def exec_cmd(self, cmd):
        global debug

        if debug:
            sys.stderr.write("GTP command: " + cmd + "\n")
        self.outfile.write(cmd + "\n\n")
        self.outfile.flush()
        result = ""
        line = self.infile.readline()
        while line != "\n":
            result = result + line
            line = self.infile.readline()
        if debug:
            sys.stderr.write("Reply: " + line + "\n")

        # Remove trailing newline from the result
        if result[-1] == "\n":
            result = result[:-1]

        if len(result) == 0:
            return "ERROR: len = 0"
        if (result[0] == "?"):
            return "ERROR: GTP Command failed: " + result[2:]
        if (result[0] == "="):
            return result[2:]
        return "ERROR: Unrecognized answer: " + result


class GTP_player:

    # Class members:
    #    connection     GTP_connection

    def __init__(self, command):
        self.connection = GTP_connection(command)
        protocol_version = self.connection.exec_cmd("protocol_version")
        if protocol_version[:5] != "ERROR":
            self.protocol_version = protocol_version
        else:
            self.protocol_version = "1"

    def is_known_command(self, command):
        return self.connection.exec_cmd("known_command " + command) == "true"

    def genmove(self, color):
        print "thinking..."
        if color[0] in ["b", "B"]:
            command = "black"
        elif color[0] in ["w", "W"]:
            command = "white"
        if self.protocol_version == "1":
            command = "genmove_" + command
        else:
            command = "genmove " + command

        return self.connection.exec_cmd(command)

    def black(self, move):
        if self.protocol_version == "1":
            self.connection.exec_cmd("black " + move)
        else:
            self.connection.exec_cmd("play black " + move)

    def white(self, move):
        if self.protocol_version == "1":
            self.connection.exec_cmd("white " + move)
        else:
            self.connection.exec_cmd("play white " + move)

    def komi(self, komi):
        self.connection.exec_cmd("komi " + komi)

    def boardsize(self, size):
        self.connection.exec_cmd("boardsize " + size)
        if self.protocol_version != "1":
            self.connection.exec_cmd("clear_board")

    def handicap(self, handicap, handicap_type):
        if handicap_type == "fixed":
            result = self.connection.exec_cmd("fixed_handicap %d" % (handicap))
        else:
            result = self.connection.exec_cmd("place_free_handicap %d"
                                              % (handicap))

        return string.split(result, " ")

    def loadsgf(self, endgamefile, move_number):
        self.connection.exec_cmd(string.join(["loadsgf", endgamefile,
                                 str(move_number)]))

    def list_stones(self, color):
        return string.split(self.connection.exec_cmd("list_stones " + color), " ")

    def quit(self):
        return self.connection.exec_cmd("quit")

    def showboard(self):
        board = self.connection.exec_cmd("showboard")
        if board and (board[0] == "\n"):
            board = board[1:]
        return board

    def get_random_seed(self):
        result = self.connection.exec_cmd("get_random_seed")
        if result[:5] == "ERROR":
            return "unknown"
        return result

    def set_random_seed(self, seed):
        self.connection.exec_cmd("set_random_seed " + seed)

    def get_program_name(self):
        return self.connection.exec_cmd("name") + " " + \
               self.connection.exec_cmd("version")

    def final_score(self):
        return self.connection.exec_cmd("final_score")

    def score(self):
        return self.final_score(self)

    def cputime(self):
        if (self.is_known_command("cputime")):
            return self.connection.exec_cmd("cputime")
        else:
            return "0"


class GTP_game:

    # Class members:
    #    whiteplayer     GTP_player
    #    blackplayer     GTP_player
    #    size            int
    #    komi            float
    #    handicap        int
    #    handicap_type   string
    #    handicap_stones int
    #    moves           list of string
    #    resultw
    #    resultb

    def __init__(self, command, serverurl, username, password,
                 size="19", komi="0", handicap=0,
                 handicap_type="fixed", endgamefile="", pause=3.0):

        self.gtp_player = GTP_player(command)
        self.server_player = GoserverPlayer(serverurl, username, password)

        self.size = size
        self.komi = komi
        self.handicap = handicap
        self.handicap_type = handicap_type
        self.endgamefile = endgamefile
        self.sgffilestart = ""
        if endgamefile != "":
            self.init_endgame_contest_game()
        else:
            self.sgffilestart = ""
        self.pause = pause

    def init_endgame_contest_game(self):
        infile = open(self.endgamefile)
        if not infile:
            print "Couldn't read " + self.endgamefile
            sys.exit(2)
        sgflines = infile.readlines()
        infile.close
        size = re.compile("SZ\[[0-9]+\]")
        move = re.compile(";[BW]\[[a-z]{0,2}\]")
        sgf_start = []
        for line in sgflines:
            match = size.search(line)
            if match:
                self.size = match.group()[3:-1]
            match = move.search(line)
            while match:
                sgf_start.append("A" + match.group()[1:])
                line = line[match.end():]
                match = move.search(line)
        self.endgame_start = len(sgf_start) - endgame_start_at
        self.sgffilestart = ";" + string.join(
                                    sgf_start[:self.endgame_start-1], "") + "\n"
        if self.endgame_start % 2 == 0:
            self.first_to_play = "W"
        else:
            self.first_to_play = "B"

    def get_position_from_engine(self, engine):
        black_stones = engine.list_stones("black")
        white_stones = engine.list_stones("white")
        self.sgffilestart = ";"
        if len(black_stones) > 0:
            self.sgffilestart += "AB"
            for stone in black_stones:
                self.sgffilestart += "[%s]" % coords_to_sgf(self.size, stone)
            self.sgffilestart += "\n"
        if len(white_stones) > 0:
            self.sgffilestart += "AW"
            for stone in white_stones:
                self.sgffilestart += "[%s]" % coords_to_sgf(self.size, stone)
            self.sgffilestart += "\n"

    def writesgf(self, sgffilename):
        "Write the game to an SGF file after a game"

        size = self.size
        outfile = open(sgffilename, "w")
        if not outfile:
            print "Couldn't create " + sgffilename
            return
        black_name = self.blackplayer.get_program_name()
        white_name = self.whiteplayer.get_program_name()
        black_seed = self.blackplayer.get_random_seed()
        white_seed = self.whiteplayer.get_random_seed()
        handicap = self.handicap
        komi     = self.komi
        result   = self.resultw

        outfile.write("(;GM[1]FF[4]RU[Japanese]SZ[%s]HA[%s]KM[%s]RE[%s]\n" %
                      (size, handicap, komi, result))
        outfile.write("PW[%s (random seed %s)]PB[%s (random seed %s)]\n" %
                      (white_name, white_seed, black_name, black_seed))
        outfile.write(self.sgffilestart)

        if handicap > 1:
            outfile.write("AB");
            for stone in self.handicap_stones:
                outfile.write("[%s]" %(coords_to_sgf(size, stone)))
            outfile.write("PL[W]\n")

        to_play = self.first_to_play

        for move in self.moves:
            sgfmove = coords_to_sgf(size, move)
            outfile.write(";%s[%s]\n" % (to_play, sgfmove))
            if to_play == "B":
                to_play = "W"
            else:
                to_play = "B"
        outfile.write(")\n")
        outfile.close

    def set_handicap(self, handicap):
        self.handicap = handicap

    def swap_players(self):
        self.server_player, self.gtp_player = self.gtp_player, self.server_player

    def play(self, sgffile):
        "Play a game"
        global verbose

        if verbose >= 1:
            print "Setting boardsize and komi for black\n"
        self.gtp_player.boardsize(self.size)
        self.gtp_player.komi(self.komi)

        free = self.server_player.get_free_games(self.server_player.login())
        if free:
            print "joining an existing game from:", free
            self.server_player.join_game(free.keys()[0])
            print "playing white in game %s" % self.server_player.game
            self.blackplayer = self.server_player
            self.whiteplayer = self.gtp_player
            self.server_player.say("Hello, I'm playing white!")
        else:
            print "no open games, starting a new one..."
            self.server_player.start_game()
            print "playing black in new game %s" % self.server_player.game
            self.whiteplayer = self.server_player
            self.blackplayer = self.gtp_player
            self.server_player.say("Hello, I'm playing black!")

        self.handicap_stones = []

        if self.endgamefile == "":
            if self.handicap < 2:
                self.first_to_play = "B"
            else:
                self.handicap_stones = self.blackplayer.handicap(self.handicap, self.handicap_type)
                for stone in self.handicap_stones:
                    self.whiteplayer.black(stone)
                self.first_to_play = "W"
        # else:
        #     self.blackplayer.loadsgf(self.endgamefile, self.endgame_start)
        #     self.blackplayer.set_random_seed("0")
        #     self.whiteplayer.loadsgf(self.endgamefile, self.endgame_start)
        #     self.whiteplayer.set_random_seed("0")
        #     if self.blackplayer.is_known_command("list_stones"):
        #         self.get_position_from_engine(self.blackplayer)
        #     elif self.whiteplayer.is_known_command("list_stones"):
        #         self.get_position_from_engine(self.whiteplayer)

        to_play = self.first_to_play

        self.moves = []
        passes = 0
        won_by_resignation = ""
        dt = 0.2
        while passes < 2:
            t0 = time.time()
            if to_play == "B":
                move = self.blackplayer.genmove("black")
                if move[:5] == "ERROR":
                    # FIXME: write_sgf
                    sys.exit(1)

                if move[:6] == "resign":
                    if verbose >= 1:
                        print "Black resigns"
                    won_by_resignation = "W+Resign"
                    self.whiteplayer.black(move)
                    break
                else:
                    self.moves.append(move)
                    if move.lower().startswith("pass"):
                        self.whiteplayer.black(move)
                        passes = passes + 1
                        if verbose >= 1:
                            print "Black passes"
                    else:
                        passes = 0
                        self.whiteplayer.black(move)
                        if verbose >= 1:
                            print "Black plays " + move
                to_play = "W"
            else:
                move = self.whiteplayer.genmove("white")
                if move[:5] == "ERROR":
                    # FIXME: write_sgf
                    sys.exit(1)

                if move[:6] == "resign":
                    if verbose >= 1:
                        print "White resigns"
                    won_by_resignation = "B+Resign"
                    self.blackplayer.white(move)
                    break
                else:
                    self.moves.append(move)
                    if string.lower(move[:4]) == "pass":
                        self.blackplayer.white(move)
                        passes = passes + 1
                        if verbose >= 1:
                            print "White passes"
                    else:
                        passes = 0
                        self.blackplayer.white(move)
                        if verbose >= 1:
                            print "White plays " + move
                to_play = "B"

            if verbose >= 2:
                print self.gtp_player.showboard() + "\n"
            dt = time.time() - t0
            if passes < 2:
                time.sleep(self.pause)

        if won_by_resignation == "":
            self.result = self.gtp_player.final_score()
            try:
                winner, score = self.result.split("+")
                winner = "white" if winner == "W" else "black"
                self.server_player.say("I think %s won, with score %s!" %
                                    (winner, score))
            except ValueError:
                self.server_player.say("I think it's a draw!")
        else:
            self.result = won_by_resignation
            winner, _ = self.result.split("+")
            winner = "white" if winner == "W" else "black"
            self.server_player.say("I think %s won by resignation!" % winner)
        print "Result:", self.result
    #    if self.resultb == self.resultw:
    #        print "Result: ", self.resultw
    #    else:
    #        print "Result according to W: ", self.resultw
    #        print "Result according to B: ", self.resultb
        # FIXME:   $self->writesgf($sgffile) if defined $sgffile;
        if sgffile != "":
            self.writesgf(sgffile)

    def result(self):
        return (self.resultw, self.resultb)

    def cputime(self):
        cputime = {}
        cputime["white"] = self.whiteplayer.cputime()
        cputime["black"] = self.blackplayer.cputime()
        return cputime

    def quit(self):
        self.blackplayer.quit()
        self.whiteplayer.quit()



# ================================================================
#                      Main program
#

import cookielib, urllib, urllib2, re, os, socket, json


class GoserverPlayer(object):

    VERTEX_LETTERS = "abcdefghjklmnopqrst"

    def __init__(self, serverurl="http://localhost:8890",
                 username="gnugo", password="gnugo"):
        self.serverurl = serverurl
        self.username = username
        self.password = password

        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
                self.cookiejar))

        self.game = None
        self.color = None
        self.cursor = 0

    def login(self):
        return self.opener.open(os.path.join(self.serverurl, "login"),
                           urllib.urlencode({"username": self.username,
                                             "password": self.password})).read()

    def get_free_games(self, page):
        games_list = page[page.find("<ul>"):page.find("</ul>")]
        games = {}
        for game in games_list.split("<li>")[1:]:
            lines = [l for l in game.splitlines() if l]
            free = re.match("(.*) is waiting for an opponent.", lines[2])
            if free:
                number, size = re.match(r"(\d+): \((\d+)x\d+\)", lines[0]).groups()
                url, = re.match(r'<a href="(/game/\d+)">', lines[1]).groups()
                print url
                games[number] = dict(opponent=free.groups()[0], size=size, url=url)
        return games

    def join_game(self, game):
        self.opener.open(os.path.join(self.serverurl, "game/%s" % game))
        self.game = game
        self.color = "white"

    def start_game(self):
        p = self.opener.open(os.path.join(self.serverurl, "game/new"))
        url = p.geturl()
        self.game = url.split("/")[-1]
        self.color = "black"
        self.wait_for_updates()

    def wait_for_updates(self):
        t = 10
        while True:
            print "waiting for update...", self.cursor
            try:
                r = self.opener.open(os.path.join(self.serverurl,
                                                  "game/%s/updates" % self.game),
                                     urllib.urlencode({"cursor": self.cursor}),
                                     timeout=t)
            except socket.timeout:
                t = max(2 * t, 60)
            else:
                break
        result = json.loads(r.read())
        print "received updates:", result
        return result

    def resign(self):
        p = self.opener.open(os.path.join(self.serverurl,
                                          "game/%s/move" % self.game),
                             urllib.urlencode({"position": "null",
                                               "resign": "true"}))
        result = json.loads(p.read())
        if result.get("move"):
            self.cursor = int(result["move"]["n"])+1
        return result

    def pass_(self):
        p = self.opener.open(os.path.join(self.serverurl,
                                          "game/%s/move" % self.game),
                             urllib.urlencode({"position": "null"}))
        result = json.loads(p.read())
        if result.get("move"):
            self.cursor = int(result["move"]["n"])+1
        return result

    def move(self, move):
        pos = "%d,%d" % self.vertex_to_coord(move)
        p = self.opener.open(os.path.join(self.serverurl,
                                          "game/%s/move" % self.game),
                             urllib.urlencode({"position": pos}))
        result = json.loads(p.read())
        if result.get("move"):
            self.cursor = int(result["move"]["n"])+1
        return result

    def boardsize(self, _):
        pass

    def komi(self, _):
        pass

    def handicap(self, hcp, hcp_type):
        return []

    def vertex_to_coord(self, vertex):
        return (self.VERTEX_LETTERS.index(vertex[0].lower()),
                int(vertex[1:]) - 1)

    def coord_to_vertex(self, coord):
        return "%s%d" % (self.VERTEX_LETTERS[coord[0]], coord[1] + 1)

    def genmove(self, color):
        while True:
            print "waiting for move"
            result = self.wait_for_updates()
            update = result["updates"][0]
            if "move" in update:
                move = update["move"]
                self.cursor = result["cursor"]
                break
        print move
        if move["position"]:
            return self.coord_to_vertex(move["position"])
        else:
            if move.get("resign"):
                return "resign"
            else:
                return "pass"

    def black(self, move):
        if self.color == "black":
            if move.lower().startswith("resign"):
                self.resign()
            elif move.lower().startswith("pass"):
                self.pass_()
            else:
                self.move(move)
        else:
            raise Exception("wrong color; I'm not black")

    def white(self, move):
        if self.color == "white":
            if move.lower().startswith("resign"):
                self.resign()
            elif move.lower().startswith("pass"):
                self.pass_()
            else:
                self.move(move)
        else:
            raise Exception("wrong color; I'm not white")

    def say(self, message):
        self.opener.open(os.path.join(self.serverurl,
                                      "room/%s/message" % self.game),
                         urllib.urlencode({"body": message}))


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-n", "--name", dest="name")
    parser.add_option("-p", "--password", dest="password")
    parser.add_option("-v", "--verbose", dest="verbose", default=False)

    (options, (command, url)) = parser.parse_args()

    # parser = argparse.ArgumentParser(
    #     description='GTP client runner for GoServer.')
    # parser.add_argument('command', type=str, help="client commandline")
    # parser.add_argument('url', type=str, help="URL to the server")
    # parser.add_argument('--name', type=str, help="login username")
    # parser.add_argument('--password', type=str, help="login password",
    #                     default="")
    # parser.add_argument('--verbose', type=int, default=0)

    # args = parser.parse_args()

    verbose = options.verbose
    game = GTP_game(command, url, options.name, options.password)
    game.play("")
