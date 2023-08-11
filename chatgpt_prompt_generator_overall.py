import argparse
import pandas as pd

COLUMN_TYPE = ["現在の手数", "現在の手番", "実戦手", "実戦手の勝率", "実戦の手を打った場合、何目優勢か(マイナスは劣勢)", \
               "最善手", "最善手の勝率", "最善手を打った場合、何目優勢か(マイナスは劣勢)"]

def convert_color(color):
    return "黒" if color == "B" else "白"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", "-f", help="Input CSV file path.", required=True, type=str)
    parser.add_argument("--output_file", "-o", help="Output file path.", required=True, type=str)
    args = parser.parse_args()

    df = pd.read_csv(args.input_file)

    overall_data_list = []
    for row in df.itertuples():
        data_list = []
        move_num = str(row.move_num)
        data_list.append(move_num)
        color = row.color
        data_list.append(color)
        move = row.move
        data_list.append(move)
        winrate = format(row.winrate * 100, '.1f')
        data_list.append(winrate)
        score_lead = format(row.score_lead, '.1f')
        data_list.append(score_lead)
        best_move = row.best_move
        data_list.append(best_move)
        best_winrate = format(row.best_winrate * 100, '.1f')
        data_list.append(best_winrate)
        best_score_lead = format(row.best_score_lead, '.1f')
        data_list.append(best_score_lead)
        overall_data_list.append(",".join(data_list))

    with open(args.output_file, "w", encoding="utf-8") as w:
        w.write("\n".join(overall_data_list))

if __name__ == "__main__":
    main()