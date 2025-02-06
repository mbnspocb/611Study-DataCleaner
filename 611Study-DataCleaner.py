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
                reader = csv.DictReader(f, skipinitialspace=True)
                data = [row for row in reader]
                self.data = data
        self.format()

    def format(self):
        _morning = lambda time_str: datetime.strptime(
            time_str.replace("上午", "AM").replace("下午", "PM"), "%p%I:%M:%S").time()

        _afternoon = lambda time_str: datetime.strptime(
            time_str.replace("上午", "PM").replace("下午", "PM"), "%p%I:%M:%S" # fix typo
        ).time()
        _to_int = lambda x: int(re.match(r"(?<!.)\d+", x).group())
        def contains_chinese_only(s):
                # 匹配中文字符的Unicode范围
            chinese_regex = re.compile(r'[\u4e00-\u9fff]')
                # 匹配日文片假名、平假名的Unicode范围
            japanese_regex = re.compile(r'[\u3040-\u30ff\u31f0-\u31ff]')
                # 匹配韩文谚文的Unicode范围
            korean_regex = re.compile(r'[\uac00-\ud7af]')

                # 判断是否包含中文字符
            has_chinese = bool(chinese_regex.search(s))
                # 判断是否包含日文或韩文字符
            has_japanese_or_korean = bool(japanese_regex.search(s) or korean_regex.search(s))

            return has_chinese and not has_japanese_or_korean

        converter = {
            "年级": int,
            "每周在校学习小时数": _to_int,
            "每月假期天数": _to_int,
            "寒假放假天数": _to_int,
            "24年学生自杀数": _to_int,
            "上学时间": _morning,
            "放学时间\n含晚自习": _afternoon,
            "寒假补课收费总价格": _to_int,
        }
        invalid_limit = {
            "城市": contains_chinese_only,
            "区县": contains_chinese_only,
            "学校名称": contains_chinese_only,
            "年级": range(0, 13),
            "每周在校学习小时数": range(40, 169),  # 24*7=168
            "每月假期天数": range(-1, 16),
            "寒假放假天数": range(-1, 60),
            "24年学生自杀数": range(-1, 51),
        }
        for _ in self.data:
            for key in _:
                if not _[key] and key in converter:
                    continue
                try:
                    if key in converter:
                        _[key] = converter[key](_[key])
                        if key in invalid_limit:
                            if _[key] not in invalid_limit[key]:
                                raise ValueError(key)
                    if key in (invalid_limit.keys() - converter.keys()):
                        if not invalid_limit[key](_[key]):
                            raise ValueError(key,'非中文语言')
                except (ValueError, AttributeError) as ex:
                    _["invalid"] = str(repr(ex))
                    break
    @staticmethod
    def _is_invalid(data: dict[str, int | time | str]):
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
