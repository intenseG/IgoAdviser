import argparse
import os
import glob


class sgf_data():

    def __init__(self, boardsize):
        self.size = boardsize
        self.komi = 6.5
        self.history = []
        self.move_cnt = 0
        self.content = ""
        self.is_save = True

    def import_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            # print(file_path)
            self.content = f.read()
            lines = self.content.split("\n")
            for line in lines:
                sgf_str = line.rstrip("\n")
                while len(sgf_str) > 3:
                    open_br = sgf_str.find("[")
                    close_br = sgf_str.find("]")
                    if open_br < 0 or close_br < 0:
                        # print("[Error] open_br < 0 or close_br < 0 -> %s" % file_path)
                        break
                    elif close_br == 0:
                        # print("[Error] close_br == 0 -> %s" % file_path)
                        sgf_str = sgf_str[close_br + 1:]
                        continue

                    # print(f"sgf_str[0:open_br]: {sgf_str[0:open_br]}")
                    key = sgf_str[0:open_br].lstrip(";").replace(' ', '')
                    # print(f"key: {key}")
                    val = sgf_str[open_br + 1:close_br]
                    # print(f"val: {val}")

                    if key == "SZ":
                        if val == str(self.size):
                            self.size = int(val)
                        else:
                            self.is_save = False
                            print(f"{self.size}路盤ではありません。")
                    elif key == "KM":
                        if val == "375":
                            self.komi = 7.5
                        elif val == "0":
                            if "HA[0]" in self.content:
                                if "RU[Japanese]" in self.content:
                                    self.komi = 6.5
                                elif "RU[Chinese]" in self.content:
                                    self.komi = 7.5
                            else:
                                self.is_save = False
                                print(f"コミ({val})は互先のものではありません。")
                    elif key == "B" or key == "W":
                        # print(val)
                        if key == "B":
                            self.history.append(val)
                        elif key == "W":
                            self.history.append(val)
                        self.move_cnt += 1

                    # print(sgf_str)
                    sgf_str = sgf_str[close_br + 1:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", "-d", help="Input SGFs directory path.", type=str)
    parser.add_argument("--output_dir", "-o", help="Output SGFs directory path.", type=str)
    parser.add_argument("--boardsize", "-b", default=19, help="Board size.", type=int)
    parser.add_argument("--min_move_count", "-m", default=50, help="Minimum movement number.", type=int)
    args = parser.parse_args()

    input_files = []
    if args.input_dir:
        input_files = glob.glob(os.path.join(args.input_dir, "*"))

    if args.output_dir:
        out_dir = args.output_dir
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

    sd_list = []
    for sgf in input_files:
        print(sgf)
        sd_list.append(sgf_data(args.boardsize))
        sd_list[-1].import_file(sgf)

    for i, sd in enumerate(sd_list):
        if sd.is_save and sd.move_cnt < args.min_move_count:
            sd.is_save = False
            print(f"最低必要手数({str(args.min_move_count)})を満たしていません。")
        content = sd.content
        if "KM[375]" in sd.content:
            content = sd.content.replace("KM[375]", "KM[7.5]")
        elif "KM[0]" in sd.content and "RU[Japanese]" in sd.content:
            if "HA[0]" in sd.content:
                if "RU[Japanese]" in sd.content:
                    content = sd.content.replace("KM[0]", "KM[6.5]")
                elif "RU[Chinese]" in sd.content:
                    content = sd.content.replace("KM[0]", "KM[7.5]")
        if sd.is_save:
            out_path = os.path.join(out_dir, os.path.basename(input_files[i]))
            with open(out_path, "w", encoding="utf-8") as w:
                w.write(content)

if __name__ == "__main__":
    main()
