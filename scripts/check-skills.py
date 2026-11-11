#!/usr/bin/env python3
"""Cổng frontmatter của skill: mọi skills/<tên>/SKILL.md phải đồng đều.

Theo đặc tả Agent Skills (docs/skills.md của Prime Agent):
  name           bắt buộc, khớp tên thư mục, chữ thường a-z 0-9 và dấu gạch ngang, tối đa 64 ký tự
  description    bắt buộc, tối đa 1024 ký tự
  compatibility  tuỳ chọn theo đặc tả, BẮT BUỘC ở repo này để mọi skill nói rõ nó cần gì; tối đa 500 ký tự

Dùng:  python3 scripts/check-skills.py [thư-mục-skills]   mặc định: skills/
       python3 scripts/check-skills.py --self-test
"""
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("thiếu frontmatter (dòng đầu phải là ---)")
    out, key, problems = {}, None, []
    for n, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            return {k: clean(v) for k, v in out.items()}, problems
        if line and not line[0].isspace() and ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip()
            why = yaml_problem(val.strip())
            if why:
                problems.append(f"dòng {n}: giá trị của `{key.strip()}` {why}, YAML đọc sai. "
                                "Đặt cả giá trị trong dấu nháy kép (escape nháy kép bên trong) hoặc viết lại")
        elif key and line.strip():
            out[key] = f"{out[key]} {line.strip()}"  # dòng nối tiếp của khối > hoặc |
    raise ValueError("frontmatter không đóng (thiếu --- thứ hai)")


def yaml_problem(val):
    """Lý do một giá trị một dòng làm YAML đọc sai, hoặc None nếu ổn."""
    if not val or val[0] in ">|[{":
        return None  # shortcut: khối > | và flow [ { không được kiểm cân bằng, cần thì dùng parser YAML thật
    if val[0] == '"':
        inner = val[1:-1] if len(val) > 1 and val.endswith('"') else None
        if inner is None or re.search(r'(?<!\\)"', inner):
            return "là chuỗi nháy kép không đóng đúng hoặc có nháy kép bên trong chưa escape"
        return None
    if val[0] == "'":
        inner = val[1:-1] if len(val) > 1 and val.endswith("'") else None
        if inner is None or "'" in inner.replace("''", ""):
            return "là chuỗi nháy đơn không đóng đúng hoặc có nháy đơn bên trong chưa nhân đôi"
        return None
    if val[0] in "`@%*&!":
        return f"không có nháy mà bắt đầu bằng `{val[0]}` (ký tự dành riêng của YAML)"
    if ": " in val or " #" in val or val.endswith(":"):
        return "có `: ` hoặc ` #` mà không có dấu nháy (Nested mappings are not allowed)"
    return None


def clean(value):
    value = value.lstrip(">|").strip()
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value


def check_skill(path):
    """Trả về danh sách lỗi của một SKILL.md (rỗng = đạt)."""
    try:
        fm, errs = frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [str(e)]
    want = path.parent.name
    name = fm.get("name", "")
    if not name:
        errs.append("thiếu name")
    elif name != want:
        errs.append(f"name {name!r} phải khớp tên thư mục {want!r}")
    elif not NAME.match(name) or len(name) > 64:
        errs.append(f"name {name!r} sai quy tắc (a-z 0-9 và gạch ngang, tối đa 64 ký tự)")
    desc = fm.get("description", "")
    if not desc:
        errs.append("thiếu description")
    elif len(desc) > 1024:
        errs.append(f"description dài {len(desc)} ký tự, tối đa 1024")
    comp = fm.get("compatibility", "")
    if not comp:
        errs.append("thiếu compatibility (nêu rõ skill cần gì để chạy)")
    elif len(comp) > 500:
        errs.append(f"compatibility dài {len(comp)} ký tự, tối đa 500")
    return errs


def check_dir(root):
    files = sorted(Path(root).glob("*/SKILL.md"))
    if not files:
        print(f"check-skills: không thấy SKILL.md nào dưới {root}", file=sys.stderr)
        return 2
    bad = 0
    for d in sorted(Path(root).iterdir()):
        if d.is_dir() and not d.name.startswith((".", "__")) and not (d / "SKILL.md").is_file():
            print(f"{d}: thư mục skill không có SKILL.md, agent sẽ không thấy nó", file=sys.stderr)
            bad += 1
    for f in files:
        for err in check_skill(f):
            print(f"{f}: {err}", file=sys.stderr)
            bad += 1
    if bad:
        return 1
    print(f"check-skills: OK ({len(files)} skill)")
    return 0


def self_test():
    ok = "---\nname: {n}\ndescription: {d}\ncompatibility: {c}\n---\nbody\n"
    cases = [  # (mô tả, nội dung, chuỗi lỗi phải có hoặc None nếu phải đạt)
        ("đạt", ok.format(n="good", d="d", c="c"), None),
        ("description nhiều dòng (>) và compat có dấu nháy",
         "---\nname: good\ndescription: >\n  dòng một\n  dòng hai\ncompatibility: \"c\"\n---\n", None),
        ("thiếu compatibility", "---\nname: good\ndescription: d\n---\n", "thiếu compatibility"),
        ("compatibility rỗng", ok.format(n="good", d="d", c=""), "thiếu compatibility"),
        ("compatibility quá dài", ok.format(n="good", d="d", c="x" * 501), "compatibility dài 501"),
        ("name khác thư mục", ok.format(n="khac", d="d", c="c"), "phải khớp tên thư mục"),
        ("thiếu name", "---\ndescription: d\ncompatibility: c\n---\n", "thiếu name"),
        ("description quá dài", ok.format(n="good", d="x" * 1025, c="c"), "description dài 1025"),
        ("thiếu description", "---\nname: good\ncompatibility: c\n---\n", "thiếu description"),
        ("không có frontmatter", "# chỉ có thân bài\n", "thiếu frontmatter"),
        ("frontmatter không đóng", "---\nname: good\n", "không đóng"),
        ("compatibility không nháy có ': '", ok.format(n="good", d="d", c="Needs a way: the runner"), "Nested mappings"),
        ("description không nháy có ' #'", ok.format(n="good", d="a # b", c="c"), "Nested mappings"),
        ("giá trị không nháy kết thúc bằng ':'", ok.format(n="good", d="d", c="Needs these:"), "Nested mappings"),
        ("giá trị có ': ' nhưng trong nháy kép", ok.format(n="good", d="d", c='"Needs a way: the runner"'), None),
        ("giá trị có ': ' trong khối >", "---\nname: good\ndescription: >\n  a: b\ncompatibility: c\n---\n", None),
        ("URL có :// không phải mapping", ok.format(n="good", d="d", c="See https://example.com/x"), None),
        ("nháy kép lồng chưa escape", ok.format(n="good", d='"Dùng khi nói "xong" việc"', c="c"), "nháy kép"),
        ("nháy kép không đóng", ok.format(n="good", d='"Dùng khi nói', c="c"), "nháy kép"),
        ("nháy kép escape đúng", ok.format(n="good", d='"Dùng khi nói \\"xong\\" việc"', c="c"), None),
        ("nháy đơn lồng chưa nhân đôi", ok.format(n="good", d="'it's'", c="c"), "nháy đơn"),
        ("nháy đơn nhân đôi đúng", ok.format(n="good", d="'it''s'", c="c"), None),
        ("bắt đầu bằng backtick", ok.format(n="good", d="`foo` helper", c="c"), "ký tự dành riêng"),
        ("bắt đầu bằng @", ok.format(n="good", d="@team skill", c="c"), "ký tự dành riêng"),
        ("bắt đầu bằng *", ok.format(n="good", d="*bold* skill", c="c"), "ký tự dành riêng"),
        ("name viết hoa và gạch dưới", ok.format(n="Bad_Name", d="d", c="c"), "sai quy tắc", "Bad_Name"),
        ("name có hai gạch ngang liền nhau", ok.format(n="a--b", d="d", c="c"), "sai quy tắc", "a--b"),
        ("name dài hơn 64 ký tự", ok.format(n="a" * 65, d="d", c="c"), "sai quy tắc", "a" * 65),
    ]
    for what, content, must, *dirname in cases:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / (dirname[0] if dirname else "good") / "SKILL.md"
            f.parent.mkdir()
            f.write_text(content, encoding="utf-8")
            errs = check_skill(f)
            if must is None and errs or must is not None and not any(must in e for e in errs):
                raise AssertionError(f"{what}: cần {'đạt' if must is None else repr(must)}, nhận {errs}")
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):  # các ca đỏ có chủ ý
        assert check_dir(d) == 2, "thư mục không có skill phải exit 2, không phải OK giả"
        bad = Path(d) / "x" / "SKILL.md"
        bad.parent.mkdir()
        bad.write_text("---\nname: x\ndescription: d\n---\n", encoding="utf-8")
        assert check_dir(d) == 1, "có skill thiếu compatibility phải exit 1"
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):
        good = Path(d) / "good" / "SKILL.md"
        good.parent.mkdir()
        good.write_text(ok.format(n="good", d="d", c="c"), encoding="utf-8")
        assert check_dir(d) == 0
        (Path(d) / "noskillmd").mkdir()
        (Path(d) / "noskillmd" / "README.md").write_text("x", encoding="utf-8")
        assert check_dir(d) == 1, "thư mục skill thiếu SKILL.md phải đỏ, không được bỏ qua im lặng"
    print("check-skills --self-test: OK")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--self-test"]:
        sys.exit(self_test())
    if len(args) > 1 or args[:1] and args[0].startswith("-"):
        print("dùng: check-skills.py [thư-mục-skills] | --self-test", file=sys.stderr)
        sys.exit(2)
    sys.exit(check_dir(args[0] if args else Path(__file__).resolve().parent.parent / "skills"))
