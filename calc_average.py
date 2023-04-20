import os
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", "-f", help="Input data file path.", required=True, type=str)
    parser.add_argument("--output_file", "-o", help="Output file path.", required=True, type=str)
    parser.add_argument("--develop", "-v", help="Developer mode.", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.input_file,  header=[0, 1])
    data = df.describe()
    data_b = df.loc[df[("color", "color")] == "B"].describe()
    data_w = df.loc[df[("color", "color")] == "W"].describe()
    print(data)
    # print(data.loc[("mean", "std"), ("<=90%", "match_rate")])
    # print(data.loc[("mean", "std"), ("<=90%", "winrate_diff")])
    # print(data.loc[("mean", "std"), ("<=90%", "score_diff")])
    # print(data.loc[("mean", "std"), ("<=90%", "blunder")])

    # print(data.loc[("mean", "std"), ("<=95%", "match_rate")])
    # print(data.loc[("mean", "std"), ("<=95%", "winrate_diff")])
    # print(data.loc[("mean", "std"), ("<=95%", "score_diff")])
    # print(data.loc[("mean", "std"), ("<=95%", "blunder")])

    # print(data.loc[("mean", "std"), ("<=98%", "match_rate")])
    # print(data.loc[("mean", "std"), ("<=98%", "winrate_diff")])
    # print(data.loc[("mean", "std"), ("<=98%", "score_diff")])
    # print(data.loc[("mean", "std"), ("<=98%", "blunder")])

    # print(data.loc[("mean", "std"), ("<=100%", "match_rate")])
    # print(data.loc[("mean", "std"), ("<=100%", "winrate_diff")])
    # print(data.loc[("mean", "std"), ("<=100%", "score_diff")])
    # print(data.loc[("mean", "std"), ("<=100%", "blunder")])

    winrate_thresholds = (1.0, 0.9, 0.95, 0.98)
    columns = ("match_rate", "winrate_diff", "score_diff", "blunder")
    data_str_list = ["all", "black", "white"]
    data_list = [data, data_b, data_w]

    for i, d in enumerate(data_list):
        content = ""
        for w in winrate_thresholds:
            m_list = []
            if args.develop:
                s_list = []
            for c in columns:
                m_list.append(str(round(d.loc["mean", (f"<={w:.0%}", c)], 3)))
                if args.develop:
                    s_list.append(str(round(d.loc["std", (f"<={w:.0%}", c)], 3)))
            content += "\t".join(m_list)
            content += "\n"
            if args.develop:
                content += "\t".join(s_list)
                content += "\n"

        file_path_tuple = os.path.splitext(args.output_file)
        out_file_path = f"{file_path_tuple[0]}-{data_str_list[i]}{file_path_tuple[1]}"
        with open(out_file_path, "w", encoding="utf-8") as w:
            w.write(content)

if __name__ == "__main__":
    main()
