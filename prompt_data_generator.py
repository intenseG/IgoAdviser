from __future__ import annotations

import os
import glob
import argparse
import json
from pysgf import SGF, SGFNode


TOP_LEFT = [0, 1, 2, 3, 4, 19, 20, 21, 22, 23, 38, 39, 40, 41, 42, 57, 58, 59, 60, 61, 76, 77, 78, 79, 80]
TOP = [5, 6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 26, 27, 28, 29, 30, 31, 32, 43, 44, 45, 46, 47, 48, 49, 50, 51, 62, 63, 64, 65, 66, 67, 68, 69, 70, 81, 82, 83, 84, 85, 86, 87, 88, 89]
TOP_RIGHT = [14, 15, 16, 17, 18, 33, 34, 35, 36, 37, 52, 53, 54, 55, 56, 71, 72, 73, 74, 75, 90, 91, 92, 93, 94]
LEFT = [95, 96, 97, 98, 99, 114, 115, 116, 117, 118, 133, 134, 135, 136, 137, 152, 153, 154, 155, 156, 171, 172, 173, 174, 175, 190, 191, 192, 193, 194, 209, 210, 211, 212, 213, 228, 229, 230, 231, 232, 247, 248, 249, 250, 251]
CENTER = [100, 101, 102, 103, 104, 105, 106, 107, 108, 119, 120, 121, 122, 123, 124, 125, 126, 127, 138, 139, 140, 141, 142, 143, 144, 145, 146, 157, 158, 159, 160, 161, 162, 163, 164, 165, 176, 177, 178, 179, 180, 181, 182, 183, 184, 195, 196, 197, 198, 199, 200, 201, 202, 203, 214, 215, 216, 217, 218, 219, 220, 221, 222, 233, 234, 235, 236, 237, 238, 239, 240, 241, 252, 253, 254, 255, 256, 257, 258, 259, 260]
RIGHT = [109, 110, 111, 112, 113, 128, 129, 130, 131, 132, 147, 148, 149, 150, 151, 166, 167, 168, 169, 170, 185, 186, 187, 188, 189, 204, 205, 206, 207, 208, 223, 224, 225, 226, 227, 242, 243, 244, 245, 246, 261, 262, 263, 264, 265]
BOTTOM_LEFT = [266, 267, 268, 269, 270, 285, 286, 287, 288, 289, 304, 305, 306, 307, 308, 323, 324, 325, 326, 327, 342, 343, 344, 345, 346]
BOTTOM = [271, 272, 273, 274, 275, 276, 277, 278, 279, 290, 291, 292, 293, 294, 295, 296, 297, 298, 309, 310, 311, 312, 313, 314, 315, 316, 317, 328, 329, 330, 331, 332, 333, 334, 335, 336, 347, 348, 349, 350, 351, 352, 353, 354, 355]
BOTTOM_RIGHT = [280, 281, 282, 283, 284, 299, 300, 301, 302, 303, 318, 319, 320, 321, 322, 337, 338, 339, 340, 341, 356, 357, 358, 359, 360]

AREA_LIST = [TOP_LEFT, TOP, TOP_RIGHT, LEFT, CENTER, RIGHT, BOTTOM_LEFT, BOTTOM, BOTTOM_RIGHT]

AREA_TYPE = ["左上", "上辺", "右上", "左辺", "中央", "右辺", "左下", "下辺", "右下"]


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


def moves_equal(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def format_value(v: float) -> str:
    return f"{v:.3f}"


def convert_value(x):
    x = (float(x) + 1) / 2
    return x


def add_result_to_csv(katago_result_file: str, game_data: GameData, csv_file: str, verbose: bool = False) -> None:
    with open(katago_result_file, "r") as f:
        katago_results = sorted(
            map(lambda x: json.loads(x), f.read().strip().split("\n")), key=lambda d: d["turnNumber"]
        )
    assert len(katago_results) == len(game_data.moves) + 1

    features = {"color": [], "move": [], "winrate": [], "score_lead": [], "ownership": [], "ownership_diff": [], \
                "pv": [], "best_move": [], "best_winrate": [], "best_score_lead": [], "best_ownership": [], \
                "best_ownership_diff": [], "best_pv": []}
    debug_cnt = 0
    for current_pos, next_pos, move in zip(katago_results, katago_results[1:], game_data.moves):
        debug_cnt += 1
        assert current_pos["rootInfo"]["currentPlayer"] == move[0]
        assert current_pos["moveInfos"][0]["order"] == 0
        best_move = current_pos["moveInfos"][0]["move"]
        best_winrate = 0
        current_winrate = 0
        current_score_lead = 0
        best_score_lead = 0
        best_ownership = []
        current_ownership = []
        best_ownership_diff = []
        current_ownership_diff = []
        pv = []
        best_pv = []
        for move_info in current_pos["moveInfos"]:
            if moves_equal(move[1], move_info["move"]):
                current_winrate = move_info["winrate"]
                current_score_lead = move_info["scoreLead"]
                ownership_list = []
                # debug_val = sum(list(map(convert_value, move_info["ownership"])))
                # print(f"{move[1]}: {str(debug_val)}")
                for l in AREA_LIST:
                    area_data = [move_info["ownership"][i] for i in l]
                    area_sum = sum(list(map(convert_value, area_data)))
                    ownership_list.append(round(area_sum, 1))
                current_ownership = ownership_list
                # current_ownership = move_info["ownership"]
                pv = move_info["pv"]
            if moves_equal(best_move, move_info["move"]):
                best_winrate = move_info["winrate"]
                best_score_lead = move_info["scoreLead"]
                best_ownership_list = []
                debug_cnt2 = 0
                for l in AREA_LIST:
                    area_data = [move_info["ownership"][i] for i in l]
                    area_sum = sum(list(map(convert_value, area_data)))
                    if debug_cnt == 50:
                        print(f"{debug_cnt}手目")
                        print(AREA_TYPE[debug_cnt2])
                        print(list(map(convert_value, area_data)))
                        print(round(area_sum, 1))
                        # print(move_info["ownership"])
                        debug_cnt2 += 1
                    best_ownership_list.append(round(area_sum, 1))
                best_ownership = best_ownership_list
                best_pv = move_info["pv"]
        assert current_pos["rootInfo"]["currentPlayer"] != next_pos["rootInfo"]["currentPlayer"]
        # score_diff = -next_pos["rootInfo"]["scoreLead"] - current_pos["rootInfo"]["scoreLead"]
        current_ownership_diff = [round(a - b, 3) for a, b in zip(current_ownership, best_ownership)]
        best_ownership_diff = [round(b - a, 3) for a, b in zip(current_ownership, best_ownership)]

        if verbose:
            print(current_pos)

        features["color"].append(current_pos["rootInfo"]["currentPlayer"])
        features["move"].append(move[1])
        features["winrate"].append(current_winrate)
        features["score_lead"].append(current_score_lead)
        features["ownership"].append(current_ownership)
        features["ownership_diff"].append(current_ownership_diff)
        features["pv"].append(pv)
        features["best_move"].append(best_move)
        features["best_winrate"].append(best_winrate)
        features["best_score_lead"].append(best_score_lead)
        features["best_ownership"].append(best_ownership)
        features["best_ownership_diff"].append(best_ownership_diff)
        features["best_pv"].append(best_pv)

    if verbose:
        print(features)

    if not os.path.isfile(csv_file):
        with open(csv_file, "w", encoding="utf-8") as f:
            labels = ["move_num", "color", "move", "winrate", "score_lead", "ownership", "ownership_diff", "pv", "best_move", "best_winrate", "best_score_lead", "best_ownership", "best_ownership_diff", "best_pv"]
            f.write(",".join([lbl for lbl in labels]))
            f.write("\n")

    with open(csv_file, "a", encoding="utf-8") as f:
        # print(len(features["color"]))
        for i in range(len(features["color"])):
            line_data = []
            # print(str(i + 1))
            # print(features["ownership"][i])
            line_data.append(str(i + 1))
            line_data.append(features["color"][i])
            line_data.append(features["move"][i])
            line_data.append(format_value(features["winrate"][i]))
            line_data.append(format_value(features["score_lead"][i]))
            line_data.append(" ".join(map(str, features["ownership"][i])))
            line_data.append(" ".join(map(str, features["ownership_diff"][i])))
            line_data.append(" ".join(features["pv"][i]))
            line_data.append(features["best_move"][i])
            line_data.append(format_value(features["best_winrate"][i]))
            line_data.append(format_value(features["best_score_lead"][i]))
            line_data.append(" ".join(map(str, features["best_ownership"][i])))
            line_data.append(" ".join(map(str, features["best_ownership_diff"][i])))
            line_data.append(" ".join(features["best_pv"][i]))

            f.write(",".join(line_data))
            f.write("\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--katago_result_dir", default="katago_results")
    parser.add_argument("-s", "--sgf_dir", help="SGF directory path.")
    parser.add_argument("--result_csv", required=True, help="Analysis result CSV file (appended if already exists)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    game_data_dict: dict[str, GameData] = dict()
    for sgf_file in sorted(glob.glob(f"{os.path.abspath(args.sgf_dir)}/*.sgf")):
        sgf_name = os.path.basename(sgf_file).replace(".sgf", "")
        game_data = GameData.from_sgf(sgf_file)
        game_data_dict[sgf_name] = game_data

    katago_result_dir = os.path.abspath(args.katago_result_dir)

    for sgf_name in sorted(game_data_dict.keys()):
        katago_result_file = f"{katago_result_dir}/{sgf_name}.txt"
        add_result_to_csv(katago_result_file, game_data_dict[sgf_name], args.result_csv, args.verbose)

if __name__ == "__main__":
    main()
