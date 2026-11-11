#!/usr/bin/env python3
"""Cổng chống hạ phiên bản (03-gitflow-va-release.md, mục "Ghim phụ thuộc theo nhánh").

So file khoá hiện tại với bản ở <base-ref>.
  HẠ  = package vẫn còn, bản cao nhất cũ biến mất và một bản thấp hơn xuất hiện. Exit 1.
  XOÁ = package biến mất hẳn, hoặc chỉ bớt một bản. Không phải HẠ: chỉ báo, exit 0.

Đọc file khoá TOML có khối [[package]] với name và version. Đã kiểm thử với Cargo.lock; poetry.lock và uv.lock
cùng dạng nhưng chưa kiểm thử. Phiên bản không đọc được (ví dụ PEP 440) hoặc file không có khối [[package]]
thì dừng với exit 2, không pass ngầm.

Dùng:  python3 scripts/check-downgrade.py <base-ref> <file-khoá>...
       python3 scripts/check-downgrade.py --self-test
Ngoại lệ: scripts/downgrade-allow.txt, mỗi dòng `<tên package>  # <ticket, lý do, số đo>`. Thiếu lý do thì exit 2.
Ngoại lệ do người dùng chốt, agent không tự thêm.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOW = Path(__file__).with_name("downgrade-allow.txt")  # shortcut: cho phép theo tên, không theo phiên bản; gỡ dòng sau khi merge
VERSION = re.compile(r"^(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


class Fail(Exception):
    """Lỗi đầu vào hoặc môi trường: exit 2, không phải kết luận 'sạch'."""


def key(version):
    m = VERSION.match(version)
    if not m:
        raise Fail(f"phiên bản không đọc được: {version!r}")
    core = [int(x) for x in m.group(1).split(".")]
    while len(core) > 1 and core[-1] == 0:  # 1.2 == 1.2.0
        core.pop()
    if m.group(2) is None:
        return tuple(core), (1,)  # bản chính thức lớn hơn mọi bản tiền phát hành
    pre = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in m.group(2).split("."))
    return tuple(core), (0,) + pre


def packages(text):
    out, name = {}, None
    for line in text.splitlines():
        if line.strip() == "[[package]]":
            name = None
        elif m := re.match(r'name\s*=\s*"([^"]+)"', line):
            name = m.group(1)
        elif name and (m := re.match(r'version\s*=\s*"([^"]+)"', line)):
            out.setdefault(name, set()).add(m.group(1))
            name = None  # mỗi khối chỉ nhận version đầu tiên
    return out


def compat_group(version):
    """Nhóm tương thích kiểu semver: 1.x.y -> (1,), 0.3.x -> (0, 3), 0.0.4 -> (0, 0, 4)."""
    key(version)  # kiểm định dạng trước
    core = [int(x) for x in VERSION.match(version).group(1).split(".")]
    i = next((n for n, x in enumerate(core) if x), len(core) - 1)
    return tuple(core[: i + 1])


def downgrades(old, new):
    found = []
    for name in sorted(old.keys() & new.keys()):
        o_max, n_max = max(old[name], key=key), max(new[name], key=key)
        if key(n_max) < key(o_max) and new[name] - old[name]:
            found.append((name, o_max, n_max))
            continue
        # Package có nhiều nhóm major (syn 1.x và 2.x): bản cao nhất giữ nguyên vẫn có thể che việc hạ 1.x.
        for g in sorted({compat_group(v) for v in old[name]} & {compat_group(v) for v in new[name]}):
            o = max((v for v in old[name] if compat_group(v) == g), key=key)
            n = max((v for v in new[name] if compat_group(v) == g), key=key)
            if key(n) < key(o):
                found.append((name, o, n))
    return found


def allowed():
    out = {}
    if ALLOW.exists():
        for n, line in enumerate(ALLOW.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, _, why = line.partition("#")
            if not name.strip() or not why.strip():
                raise Fail(f"{ALLOW}:{n}: ngoại lệ phải có dạng `<tên>  # <lý do>`, nhận {line!r}")
            out[name.strip()] = why.strip()
    return out


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def check(ref, files):
    if git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise Fail(f"base-ref không tồn tại: {ref!r}")
    allow, bad = allowed(), 0
    root = Path(git("rev-parse", "--show-toplevel").stdout.strip() or ".").resolve()
    for f in files:
        if not Path(f).is_file():
            raise Fail(f"{f}: không có trong cây làm việc (gõ sai đường dẫn?)")
        try:  # git show ref:path tính từ gốc repo, không từ cwd
            rel = Path(f).resolve().relative_to(root).as_posix()
        except ValueError:
            raise Fail(f"{f}: nằm ngoài repo {root}")
        shown = git("show", f"{ref}:{rel}")
        if shown.returncode != 0:
            print(f"check-downgrade: {f}: không có ở {ref}, không có gì để so")
            continue
        old, new = packages(shown.stdout), packages(Path(f).read_text(encoding="utf-8"))
        if not old or not new:
            raise Fail(f"{f}: không đọc được khối [[package]] (định dạng chưa hỗ trợ?)")
        for name, o, n in downgrades(old, new):
            if name in allow:
                print(f"check-downgrade: cho phép {name} {o} -> {n} ({allow[name]})")
            else:
                print(f"HẠ: {f}: {name} {o} -> {n}", file=sys.stderr)
                bad += 1
        gone = sorted(old.keys() - new.keys())
        if gone:
            print(f"check-downgrade: XOÁ (không phải hạ): {', '.join(gone)}")
    if bad:
        print("check-downgrade: có package bị hạ. Sửa tay khối của package về bản cũ rồi kiểm lại; "
              "KHÔNG tự thêm ngoại lệ.", file=sys.stderr)
        return 1
    print("check-downgrade: OK")
    return 0


LOCK = ('[[package]]\nname = "{0}"\nversion = "{1}"\nsource = "registry+https://example.invalid/index"\n'
        'checksum = "abc"\ndependencies = [\n "name 9.9.9",\n "version 0.0.1",\n]\n\n')
BASE = dict(serde="1.0.100", tokio="1.20.0", syn="1.0.109 2.0.20", gone="0.1.0", ver="1.9.0", zero="1.2.0")


def lock(**over):
    """Dựng Cargo.lock giả từ BASE; giá trị None thì bỏ package, 'a b' thì hai bản."""
    pkgs = {k: v for k, v in {**BASE, **over}.items() if v is not None}
    return "version = 3\n\n" + "".join(LOCK.format(n, v) for n, vs in pkgs.items() for v in vs.split())


def self_test():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "scripts").mkdir()
        tool, allow_file = d / "scripts" / "check-downgrade.py", d / "scripts" / "downgrade-allow.txt"
        tool.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
        git_ = lambda *a: subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                         capture_output=True, text=True, check=True)
        (d / "Cargo.lock").write_text(lock(), encoding="utf-8")
        git_("init", "-q")
        git_("add", "-A")
        git_("commit", "-q", "-m", "base")

        def run(want, what, new_lock=None, ref="HEAD", files=("Cargo.lock",), contains="", cwd=None):
            if new_lock is not None:
                (d / "Cargo.lock").write_text(new_lock, encoding="utf-8")
            r = subprocess.run([sys.executable, str(tool), ref, *files], cwd=cwd or d, capture_output=True, text=True)
            out = r.stdout + r.stderr
            if r.returncode != want or contains not in out:
                raise AssertionError(f"{what}: cần exit {want} chứa {contains!r}, nhận exit {r.returncode}: {out}")

        run(0, "không đổi gì", lock())
        run(0, "nâng bản", lock(serde="1.0.200"))
        run(0, "1.9.0 -> 1.10.0 là nâng (so số, không so chuỗi)", lock(ver="1.10.0"))
        run(0, "1.2.0 -> 1.2 là cùng một bản", lock(zero="1.2"))
        run(1, "hạ tokio phải đỏ", lock(tokio="1.19.0"), contains="tokio 1.20.0 -> 1.19.0")
        run(1, "bản chính thức -> tiền phát hành là hạ", lock(tokio="1.20.0-rc.1"), contains="tokio 1.20.0 -> 1.20.0-rc.1")
        run(1, "bản cao nhất biến mất, bản thấp hơn xuất hiện: hạ", lock(syn="1.0.200"), contains="syn 2.0.20 -> 1.0.200")
        run(1, "hạ trong nhóm 1.x khi 2.x giữ nguyên", lock(syn="1.0.50 2.0.20"), contains="syn 1.0.109 -> 1.0.50")
        run(0, "nâng trong nhóm 1.x khi 2.x giữ nguyên", lock(syn="1.0.200 2.0.20"))
        run(0, "xoá hẳn package không phải hạ", lock(gone=None), contains="XOÁ (không phải hạ): gone")
        run(0, "chỉ bớt bản cao nhất, bản thấp còn nguyên: không phải hạ", lock(syn="1.0.109"))

        allow_file.write_text("tokio  # TICKET-1: hạ vì CVE, đã đo 3 lần\n", encoding="utf-8")
        run(0, "ngoại lệ có lý do", lock(tokio="1.19.0"), contains="cho phép tokio 1.20.0 -> 1.19.0 (TICKET-1")
        allow_file.write_text("tokio\n", encoding="utf-8")
        run(2, "ngoại lệ thiếu lý do phải exit 2", lock(tokio="1.19.0"), contains="phải có dạng")
        allow_file.write_text("serde  # chỉ serde, không phải tokio\n", encoding="utf-8")
        run(1, "ngoại lệ của package khác không che tokio", lock(tokio="1.19.0"), contains="tokio 1.20.0 -> 1.19.0")
        allow_file.unlink()

        run(2, "phiên bản không đọc được phải exit 2", lock(serde="1.0.x"), contains="không đọc được")
        run(2, "base-ref sai phải exit 2, không pass ngầm", lock(), ref="khong-co-ref", contains="base-ref không tồn tại")
        run(2, "file không có khối [[package]] phải exit 2", '{"lockfileVersion": 3}\n', contains="không đọc được khối")
        run(2, "đường dẫn file gõ sai phải exit 2, không pass ngầm", files=("Cargo.lcok",), contains="không có trong cây làm việc")
        (d / "svc").mkdir()
        (d / "svc" / "api.lock").write_text(lock(), encoding="utf-8")
        git_("add", "-A")
        git_("commit", "-q", "-m", "svc")
        (d / "Cargo.lock").write_text(lock(), encoding="utf-8")
        (d / "svc" / "api.lock").write_text(lock(tokio="1.0.0"), encoding="utf-8")
        run(1, "chạy từ thư mục con vẫn so đúng file", files=("api.lock",), contains="tokio 1.20.0 -> 1.0.0", cwd=d / "svc")
        run(1, "đường dẫn tuyệt đối vẫn so đúng file", files=(str(d / "svc" / "api.lock"),), contains="tokio 1.20.0 -> 1.0.0")
        (d / "Moi.lock").write_text(lock(), encoding="utf-8")
        run(0, "file khoá mới (không có ở base) không có gì để so", files=("Moi.lock",), contains="không có ở HEAD")
    print("check-downgrade --self-test: OK")
    return 0


def main(argv):
    try:
        if argv == ["--self-test"]:
            return self_test()
        if len(argv) < 2 or argv[0].startswith("-"):
            print("dùng: check-downgrade.py <base-ref> <file-khoá>... | --self-test", file=sys.stderr)
            return 2
        return check(argv[0], argv[1:])
    except Fail as e:
        print(f"check-downgrade: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
