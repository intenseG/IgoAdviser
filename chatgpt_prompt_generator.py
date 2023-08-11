import argparse
import pandas as pd

COLUMN_TYPE = ["現在の手数", "現在の手番", "実戦手", "実戦手の勝率", "実戦の手を打った場合、何目優勢か(マイナスは劣勢)", \
               "最善手", "最善手の勝率", "最善手を打った場合、何目優勢か(マイナスは劣勢)", "実戦手を打った後のAIの進行", \
               "最善手を打った後のAIの進行", "実戦手の代わりに最善手を打った場合、どの程度陣地が増加するか(マイナスは減少)", \
               "最善手を打った場合の、プレイヤーの陣地", "実戦手を打った場合の、プレイヤーの陣地", \
               "実戦手の代わりに最善手を打った場合、どの程度黒の死石が増加するか(マイナスは減少)", \
                "実戦手の代わりに最善手を打った場合、どの程度白の死石が増加するか(マイナスは減少)"]
AREA_TYPE = ["左上", "上辺", "右上", "左辺", "中央", "右辺", "左下", "下辺", "右下"]

def convert_color(color):
    return "黒" if color == "B" else "白"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", "-f", help="Input CSV file path.", required=True, type=str)
    parser.add_argument("--output_file", "-o", help="Output file path.", required=True, type=str)
    parser.add_argument("--target_num", "-n", help="Target move number.", required=True, type=int)
    args = parser.parse_args()

    df = pd.read_csv(args.input_file)
    target_data = df.loc[df["move_num"] == args.target_num]

    data_list = []
    move_num = target_data["move_num"].values[0].astype(str)
    data_list.append(f"・{COLUMN_TYPE[0]}: {move_num}")
    color = convert_color(target_data["color"].values[0])
    data_list.append(f"・{COLUMN_TYPE[1]}: {color}")
    move = target_data["move"].values[0]
    data_list.append(f"・{COLUMN_TYPE[2]}: {move}")
    winrate = format(target_data["winrate"].values[0] * 100, '.1f') + '%'
    data_list.append(f"・{COLUMN_TYPE[3]}: {winrate}")
    score_lead = format(target_data["score_lead"].values[0], '.1f')
    data_list.append(f"・{COLUMN_TYPE[4]}: {score_lead}")
    best_move = target_data["best_move"].values[0]
    data_list.append(f"・{COLUMN_TYPE[5]}: {best_move}")
    best_winrate = format(target_data["best_winrate"].values[0] * 100, '.1f') + '%'
    data_list.append(f"・{COLUMN_TYPE[6]}: {best_winrate}")
    best_score_lead = format(target_data["best_score_lead"].values[0], '.1f')
    data_list.append(f"・{COLUMN_TYPE[7]}: {best_score_lead}")

    pv_list = target_data["pv"].str.split(" ").values.tolist()[0]
    pv = ",".join(pv_list)
    data_list.append(f"・{COLUMN_TYPE[8]}: {pv}")
    best_pv_list = target_data["best_pv"].str.split(" ").values.tolist()[0]
    best_pv = ",".join(best_pv_list)
    data_list.append(f"・{COLUMN_TYPE[9]}: {best_pv}")

    data_list.append(f"・{COLUMN_TYPE[10]}")
    best_ownership_diff_list = target_data["best_ownership_diff"].str.split(" ").values.tolist()[0]
    for i, bod in enumerate(best_ownership_diff_list):
        data_list.append(f"- {AREA_TYPE[i]}: {bod}")

    data_list.append(f"・{COLUMN_TYPE[11]}")
    best_ownership_list = target_data["best_ownership"].str.split(" ").values.tolist()[0]
    for i, bo in enumerate(best_ownership_list):
        data_list.append(f"- {AREA_TYPE[i]}: {bo}")

    data_list.append(f"・{COLUMN_TYPE[12]}")
    ownership_list = target_data["ownership"].str.split(" ").values.tolist()[0]
    for i, o in enumerate(ownership_list):
        data_list.append(f"- {AREA_TYPE[i]}: {o}")

    with open(args.output_file, "w", encoding="utf-8") as w:
        w.write("\n".join(data_list))

if __name__ == "__main__":
    main()