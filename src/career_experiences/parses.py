import os
from math import pi

import pandas as pd
from bokeh.io import export_png
from bokeh.io.export import export_svg
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.transform import cumsum
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config.settings import BASE_DIR
from src.career_experiences.constants import (
    CAREER_EXP_INPUTS_DIR,
    CAREER_EXP_OUTPUTS_DIR,
)

opts = Options()
opts.add_argument("--headless")


def read_files():
    return os.listdir(CAREER_EXP_INPUTS_DIR)


# def get_survey_map(path):
#     df = pd.read_excel(path).fillna("")
#     columns = df.columns
#     survey_map = {}
#     for column in columns[1:]:
#
#         rows = df[column].loc[df[column] != ""]
#         total_row_count = len(rows)
#         unique_select = set()
#         select_count_map = defaultdict(int)
#         for row in rows:
#             if isinstance(row, str) and "," in row:
#                 for r in row.split(","):
#                     unique_select.add(r.strip())
#                     select_count_map[r] += 1
#             else:
#                 select_count_map[row] += 1
#                 unique_select.add(row)
#         unique_select_count = len(unique_select)
#         frequency = unique_select_count / total_row_count
#         is_subject = frequency >= 0.15
#         if not is_subject:
#             survey_map[column] = select_count_map
#
#     return survey_map


def write_chart(output_file_dir, title, p, driver):
    output_dir = os.path.join(output_file_dir, title)
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    export_png(
        p,
        webdriver=driver,
        timeout=500,
        filename=os.path.join(output_dir, f"{title}.png",),
    )
    export_svg(
        p,
        webdriver=driver,
        timeout=500,
        filename=os.path.join(output_dir, f"{title}.svg",),
    )


def generate_pie_chart(df, title, driver, index, output_file_dir):
    df["angle"] = df["value"] / df["value"].sum() * 2 * pi
    colors = ["#f44336", "#2196f3"]
    df["color"] = colors[: len(df)]
    legend = []
    for row in df.iterrows():
        _, remain = row
        legend.append(f"{remain.answer} - {remain.percent} ({remain.value})")
    df["legend"] = legend
    p = figure(
        plot_height=350,
        title=title[index],
        toolbar_location=None,
        tools="hover",
        tooltips="@answer: @value",
        x_range=(-0.5, 1.0),
        output_backend="svg",
    )
    #
    p.wedge(
        x=0,
        y=1,
        radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend_field="legend",
        source=df,
    )

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None
    write_chart(output_file_dir, title[index], p, driver)


def draw_horizontal_bar_chart(df, title, driver, index, output_file_dir):
    labels = []
    for _, row in df.iterrows():
        labels.append(f"{row.answer} - {row.percent} ({row.value})")
    labels = [label[:50] if len(label) > 50 else label for label in labels]
    title_length = len(title[index])
    df["right"] = df["value"]
    df["label"] = labels
    df["y"] = labels
    df["color"] = "#a7c5eb"
    offset = (len(df) - 3) * 60
    width_offset = int(title_length * 6)

    extra = {"height": 300 + offset, "width": 600 + width_offset}

    source = ColumnDataSource(data=df.to_dict(orient="list"))
    p = figure(
        y_range=labels,
        title=title[index],
        toolbar_location=None,
        output_backend="svg",
        **extra,
    )
    p.hbar(
        y="label", height=0.8, color="color", source=source,
    )
    print(title[index])

    write_chart(output_file_dir, title[index], p, driver)


def process_survey(data_frame, filename):
    driver = webdriver.Chrome(
        os.path.join(BASE_DIR, "chromedriver"), options=opts
    )
    skips = data_frame.skip
    title = data_frame.title
    options = data_frame.options
    parsed_filename = filename.split(".")[0]
    output_file_dir = os.path.join(CAREER_EXP_OUTPUTS_DIR, parsed_filename)
    if not os.path.isdir(output_file_dir):
        os.mkdir(output_file_dir)
    with pd.ExcelWriter(
        os.path.join(CAREER_EXP_OUTPUTS_DIR, f"{parsed_filename}.xlsx")
    ) as writer:
        for index, option in enumerate(options):
            is_skip = bool(skips[index])
            row_data = []
            if not is_skip:
                for key, values in option.items():
                    row_data.append((key, *values.values()))
                df = pd.DataFrame(
                    row_data, columns=["answer", "value", "percent"]
                )
                df = df.sort_values(
                    by=["value"], axis=0, ascending=not len(option) < 3
                )
                excel_df = df.sort_values(
                    by=["value"], axis=0, ascending=False
                )
                excel_df = pd.DataFrame(
                    [
                        [
                            "응답수",
                            *excel_df.value.to_list(),
                            sum(excel_df.value),
                        ],
                        [
                            "응답률",
                            *excel_df.percent.to_list(),
                            (
                                f'{sum([float(p.split("%")[0]) for p in excel_df.percent])}%'
                            ),
                        ],
                    ],
                    columns=["구분", *excel_df.answer.to_list(), "합계"],
                )
                if len(option) < 3:
                    generate_pie_chart(
                        df, title, driver, index, output_file_dir
                    )
                    # show(p)
                else:
                    draw_horizontal_bar_chart(
                        df, title, driver, index, output_file_dir
                    )
            else:
                df = pd.DataFrame(
                    zip(option.keys(), option.values()),
                    columns=["key", "value"],
                )
                df = df.sort_values(by=["value"], axis=0, ascending=False)
                excel_df = pd.DataFrame(
                    [["응답수", *df.value.to_list(), sum(df.value)]],
                    columns=["구분", *df.key.to_list(), "합계"],
                )
            excel_df.to_excel(
                writer,
                sheet_name=title[index].replace("?", ""),
                index=False,
                header=True,
            )


def parse():
    files = read_files()
    for file in files:
        df = pd.read_json(os.path.join(CAREER_EXP_INPUTS_DIR, file))
        df["skip"] = df["skip"].fillna(False)
        process_survey(df, file)


def main():
    parse()


if __name__ == "__main__":
    main()
