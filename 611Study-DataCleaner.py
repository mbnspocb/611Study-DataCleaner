import argparse
import csv
import re
from datetime import datetime, time
from typing import Literal


class DataProcessor:
    def __init__(self, data: str | dict):
        if isinstance(data, dict):
            self.data = data
        else:
            with open(data, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(
                    f,
                    fieldnames=[
                        "时间戳记",
                        "省份",
                        "城市",
                        "区县",
                        "学校名称",
                        "年级",
                        "每周在校学习小时数",
                        "每月假期天数",
                        "寒假放假天数",
                        "24年学生自杀数",
                        "上学时间",
                        "放学时间\n含晚自习",
                        "寒假补课收费总价格",
                        "学生的评论",
                        "",
                    ],
                    skipinitialspace=True,
                )

                self.data = [row for row in reader]

        self.format()

    def format(self):
        def parse_chinese_time(time_str: str) -> time:
            match = re.search(r"(上午|下午)", time_str)
            if not match:
                raise ValueError(f"无法识别的时间格式: {time_str}")
            period = match.group(1)
            return "AM" if period == "上午" else "PM"

        def morning(time_str: str) -> time:
            day_period = parse_chinese_time(time_str)
            time_str = time_str.strip("上午").strip("下午").strip()
            return datetime.strptime(f"{day_period}{time_str}", "%p%I:%M:%S").time()

        def afternoon(time_str: str) -> time:
            day_period = parse_chinese_time(time_str)
            time_str = time_str.strip("上午").strip("下午").strip()
            return datetime.strptime(
                f"{day_period}{time_str}".replace("AM", "PM"), "%p%I:%M:%S"
            ).time()  # fix typo

        def to_int(x):
            return int(re.match(r"(?<!.)\d+", x).group())
        def correct_grade(x):
            num = to_int(x)
            return num if not (12 < num < 20) else 12
        def contains_chinese_only(s):
            # 匹配中文字符的Unicode范围
            chinese_regex = re.compile(r"[\u4e00-\u9fff]")
            # 匹配日文片假名、平假名的Unicode范围
            japanese_regex = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
            # 匹配韩文谚文的Unicode范围
            korean_regex = re.compile(r"[\uac00-\ud7af]")

            # 判断是否包含中文字符
            has_chinese = bool(chinese_regex.search(s))
            # 判断是否包含日文或韩文字符
            has_japanese_or_korean = bool(
                japanese_regex.search(s) or korean_regex.search(s)
            )

            return has_chinese and not has_japanese_or_korean

        converter = {
            "年级": correct_grade,
            "每周在校学习小时数": to_int,
            "每月假期天数": float,
            "寒假放假天数": to_int,
            "24年学生自杀数": to_int,
            "上学时间": morning,
            "放学时间\n含晚自习": afternoon,
            "寒假补课收费总价格": to_int,
        }
        invalid_limit = {
            "城市": contains_chinese_only,
            "区县": contains_chinese_only,
            "学校名称": contains_chinese_only,
            "年级": (1, 12),
            "每周在校学习小时数": (40, 168),  # 24*7=168
            "每月假期天数": (0, 16),
            "寒假放假天数": (0, 60),
            "24年学生自杀数": (0, 30),
        }
        for _ in self.data:
            for key in _:
                if not _[key] and key in converter:
                    continue
                try:
                    if key in converter:
                        _[key] = converter[key](_[key])
                        if key in invalid_limit:
                            small, large = invalid_limit[key]
                            if not (small <= _[key] <= large):
                                raise ValueError(key)
                    if key in (invalid_limit.keys() - converter.keys()):
                        if not invalid_limit[key](_[key]):
                            raise ValueError(key, "非中文语言")
                except (ValueError, AttributeError) as ex:
                    _["invalid"] = str(repr(ex))
                    break

    @staticmethod
    def _is_invalid(data: dict[str, int | float | time | str]):
        return "invalid" in data

    def get_invalid(self):
        filtered_data = list(filter(self._is_invalid, self.data))
        return filtered_data

    def get_valid(self):
        filtered_data = list(filter(lambda x: not self._is_invalid(x), self.data))
        return filtered_data

    def save_csv(self, csv_path, content: Literal["all", "valid"] = "all"):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            fieldnames = [
                "时间戳记",
                "省份",
                "城市",
                "区县",
                "学校名称",
                "年级",
                "每周在校学习小时数",
                "每月假期天数",
                "寒假放假天数",
                "24年学生自杀数",
                "上学时间",
                "放学时间\n含晚自习",
                "寒假补课收费总价格",
                "学生的评论",
                "invalid",
                "",
            ]
            if content == "valid":
                fieldnames.remove("invalid")
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.data if content == "all" else self.get_valid())


parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("output", nargs="?", default="output.csv")
parser.add_argument("--type", choices=["all", "valid"], default="all")
parser.add_argument(
    "--info",
    action="store_true",
    default=False,
)

args = parser.parse_args()

_ = DataProcessor(args.input)
if args.info:
    print(f"数据{len(_.data)}条，有效{len(_.get_valid())}条")
    exit(0)
_.save_csv(args.output, args.type)
