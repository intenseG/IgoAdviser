from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
from signal import SIGINT
from typing import Optional

from pysgf import SGF, SGFNode

SUPPORTED_RULES = (
    "tromp-taylor",
    "chinese",
    "chinese-ogs",
    "chinese-kgs",
    "japanese",
    "korean",
    "stone-scoring",
    "aga",
    "bga",
    "new-zealand",
    "aga-button",
)


class GameData:
    def __init__(
        self,
        board_x_size: int,
        board_y_size: int,
        komi: float,
        rules: str,
        initial_stones: list[list[str]],
        moves: list[list[str]],
        player_black: str,
        player_white: str,
    ) -> None:
        self.board_x_size = board_x_size
        self.board_y_size = board_y_size
        self.komi = komi
        self.rules = rules
        self.initial_stones = initial_stones
        self.moves = moves
        self.player_black = player_black
        self.player_white = player_white

    @staticmethod
    def from_sgf(filename: str) -> GameData:
        root = SGF.parse_file(filename, "utf-8")

        assert root.get_property("SZ") is not None
        bx, by = root.board_size
        assert 0 <= bx <= 19 and 0 <= by <= 19

        if root.get_property("KM") is None:
            print(f"No KM property in {filename}")
        if root.komi == 375:
            print("Interpret komi 375 as 7.5")
            root.set_property("KM", 7.5)

        if root.get_property("RU") is None:
            print(f"No RU property in {filename}")
            if root.komi == 6.5:
                root.set_property("RU", "japanese")
            elif root.komi == 7.5:
                root.set_property("RU", "chinese")

        initial_stones = [[m.player, m.gtp()] for m in root.move_with_placements if not m.is_pass]

        nodes = [root]
        node = root
        while node.children:
            assert len(node.children) == 1
            node = node.children[0]
            nodes.append(node)
        assert isinstance(node, SGFNode)
        assert node.nodes_from_root == nodes
        moves: list[list[str]] = []
        prev_player = ""
        for node in nodes[1:]:
            assert node.move is not None
            m = node.move
            if m.player == prev_player:
                moves.append([m.PLAYERS.replace(m.player, ""), "pass"])
            moves.append([m.player, m.gtp()])
            prev_player = m.player
        while moves and moves[-1][1].lower() == "pass":
            moves.pop()
        assert moves

        player_black = "player_1"
        if root.get_property("PB") is not None:
            player_black = root.get_property("PB")
        player_white = "player_2"
        if root.get_property("PW") is not None:
            player_white = root.get_property("PW")

        return GameData(bx, by, root.komi, root.ruleset, initial_stones, moves, player_black, player_white)

    def to_query(self, id_: str, max_visits: Optional[int] = None) -> str:
        assert 1 <= self.board_x_size <= 19 and 1 <= self.board_y_size <= 19
        assert abs(self.komi) <= 150
        assert self.komi * 10 % 5 == 0
        assert self.rules.lower() in SUPPORTED_RULES

        query_dict = {
            "id": f"{id_}",
            "boardXSize": self.board_x_size,
            "boardYSize": self.board_y_size,
            "komi": self.komi,
            "rules": self.rules,
            "initialStones": self.initial_stones,
            "moves": self.moves,
            "analyzeTurns": list(range(len(self.moves) + 1)),
        }
        if max_visits is not None:
            assert max_visits >= 1
            query_dict["maxVisits"] = max_visits

        return json.dumps(query_dict)


class AnalysisEngine:
    def __init__(self, cmd: list[str], result_filename: str) -> None:
        print(f"engine command: \"{' '.join(cmd)}\"")
        with open(result_filename, "w", encoding="utf-8") as f:
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=f, stderr=sys.stderr)

    @property
    def proc(self) -> subprocess.Popen[bytes]:
        return self._proc

    def write_query(self, query: str) -> None:
        def write_query_target() -> None:
            if self._proc.stdin is not None:
                self._proc.stdin.write(f"{query}\n".encode("utf-8"))
                self._proc.stdin.flush()
            else:
                print("proc.stdin is None")

        t = threading.Thread(target=write_query_target)
        t.start()
        t.join()


def moves_equal(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def format_value(v: float) -> str:
    return f"{v:.3f}"


def add_result_to_csv(katago_result_file: str, game_data: GameData, csv_file: str, verbose: bool = False) -> None:
    with open(katago_result_file, "r") as f:
        katago_results = sorted(
            map(lambda x: json.loads(x), f.read().strip().split("\n")), key=lambda d: d["turnNumber"]
        )
    assert len(katago_results) == len(game_data.moves) + 1

    winrate_thresholds = (1.0, 0.9, 0.95, 0.98)
    features = {"match": [], "match_visits": [], "winrate_diff": [], "score_diff": [], "blunder": []}
    d_player = dict((round(w, 2), copy.deepcopy(features)) for w in winrate_thresholds)
    analysis_results_dict = {"B": d_player, "W": copy.deepcopy(d_player)}
    for current_pos, next_pos, move in zip(katago_results, katago_results[1:], game_data.moves):
        assert current_pos["rootInfo"]["currentPlayer"] == move[0]
        assert current_pos["moveInfos"][0]["order"] == 0
        best_move = current_pos["moveInfos"][0]["move"]
        match = moves_equal(move[1], best_move)
        match_visits = 0
        for move_info in current_pos["moveInfos"]:
            if moves_equal(move[1], move_info["move"]):
                if "isSymmetryOf" in move_info:
                    if move_info["isSymmetryOf"] == best_move:
                        match = True
                match_visits = move_info["visits"]
        assert current_pos["rootInfo"]["currentPlayer"] != next_pos["rootInfo"]["currentPlayer"]
        winrate_diff = (1 - next_pos["rootInfo"]["winrate"] - current_pos["rootInfo"]["winrate"]) * 100
        score_diff = -next_pos["rootInfo"]["scoreLead"] - current_pos["rootInfo"]["scoreLead"]
        score_stdev = max(current_pos["rootInfo"]["scoreStdev"], 0.001)
        blunder = max(-winrate_diff / score_stdev, 0) * 100

        if verbose:
            print(current_pos)
            print(match, match_visits, winrate_diff, score_diff, blunder)

        for threshold in winrate_thresholds:
            w = current_pos["rootInfo"]["winrate"]
            if max(w, 1 - w) <= threshold:
                analysis_results_dict[move[0]][round(threshold, 2)]["match"].append(match)
                analysis_results_dict[move[0]][round(threshold, 2)]["match_visits"].append(
                    match_visits / current_pos["rootInfo"]["visits"]
                )
                analysis_results_dict[move[0]][round(threshold, 2)]["winrate_diff"].append(winrate_diff)
                analysis_results_dict[move[0]][round(threshold, 2)]["score_diff"].append(score_diff)
                analysis_results_dict[move[0]][round(threshold, 2)]["blunder"].append(blunder)

    if verbose:
        print(analysis_results_dict)

    if not os.path.isfile(csv_file):
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("color,name,")
            f.write(",".join([f"<={w:.0%}" for w in winrate_thresholds for _ in range(len(features) + 1)]))
            f.write("\ncolor,name,")
            labels = ["match", "match_rate", "match_visits", "winrate_diff", "score_diff", "blunder"]
            f.write(",".join([lbl for _ in winrate_thresholds for lbl in labels]))
            f.write("\n")

    with open(csv_file, "a", encoding="utf-8") as f:
        for c in "BW":
            line_data = [c]
            line_data.append(game_data.player_black if c == "B" else game_data.player_white)
            for threshold in winrate_thresholds:
                d = analysis_results_dict[c][round(threshold, 2)]
                assert len(d["match"]) == len(d["match_visits"]) == len(d["winrate_diff"]) == len(d["score_diff"]) == len(d["blunder"])
                n = len(d["match"])
                if n == 0:
                    line_data += ["-"] * 6
                else:
                    line_data.append(f'{sum(d["match"])}/{n}')
                    line_data.append(format_value(sum(d["match"]) / n * 100))
                    line_data.append(format_value(sum(d["match_visits"]) / n))
                    line_data.append(format_value(sum(d["winrate_diff"]) / n))
                    line_data.append(format_value(sum(d["score_diff"]) / n))
                    line_data.append(format_value(sum(d["blunder"]) / n))

            f.write(",".join(line_data))
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--engine_command", required=True, help="KataGo analysis engine command")
    parser.add_argument("-k", "--katago_result_dir", default="katago_results")
    parser.add_argument("--sgf_dir", required=True, help="Target SGFs directory")
    parser.add_argument("--komi", type=float, help="Override komi in sgfs if specified")
    parser.add_argument("--rules", choices=SUPPORTED_RULES, help="Override rules in sgfs if specified")
    parser.add_argument("--max_visits", type=int, help="Override maxVisits in config if specified")
    parser.add_argument("--result_csv", required=True, help="Analysis result CSV file (appended if already exists)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = vars(parser.parse_args())

    print(f"args: {args}\n")

    game_data_dict: dict[str, GameData] = dict()
    for sgf_file in sorted(glob.glob(f"{os.path.abspath(args['sgf_dir'])}/*.sgf")):
        sgf_name = os.path.basename(sgf_file).replace(".sgf", "")
        game_data = GameData.from_sgf(sgf_file)
        if args["komi"] is not None:
            game_data.komi = args["komi"]
        if args["rules"] is not None:
            game_data.rules = args["rules"]
        game_data_dict[sgf_name] = game_data

    if not game_data_dict:
        sys.exit()

    katago_result_dir = os.path.abspath(args["katago_result_dir"])
    os.makedirs(katago_result_dir, exist_ok=True)

    katago_result_all_file = f"{katago_result_dir}/all.txt"
    engine = AnalysisEngine(re.split(r"\s+", args["engine_command"].strip()), katago_result_all_file)
    try:
        assert engine.proc.stdin is not None
        for sgf_name, game_data in game_data_dict.items():
            query = game_data.to_query(sgf_name, args["max_visits"])
            print(query)
            engine.write_query(query)
        engine.proc.stdin.close()
        while engine.proc.poll() is None:
            time.sleep(3)
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        engine.proc.send_signal(SIGINT)

        wait_sec = 5
        try:
            returncode = engine.proc.wait(wait_sec)
            print(f"returncode: {returncode}")
            sys.exit(returncode)
        except subprocess.TimeoutExpired as toe:
            print(toe)
            engine.proc.kill()
            sys.exit(1)
    except Exception as e:
        print("Unexpected Exception", file=sys.stderr)
        print(e, file=sys.stderr)
        engine.proc.kill()
        sys.exit(1)

    with open(katago_result_all_file, "r", encoding="utf-8") as f:
        katago_results = list(map(lambda x: json.loads(x), f.read().strip().split("\n")))

    for sgf_name in sorted(game_data_dict.keys()):
        katago_result_file = f"{katago_result_dir}/{sgf_name}.txt"
        with open(katago_result_file, "w", encoding="utf-8") as f:
            for line_dict in katago_results:
                if line_dict["id"] == sgf_name:
                    f.write(json.dumps(line_dict))
                    f.write("\n")

        add_result_to_csv(katago_result_file, game_data_dict[sgf_name], args["result_csv"], args["verbose"])
