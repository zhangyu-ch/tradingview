import hashlib
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive/legacy/joinquant-source.zip"
ARCHIVE_README = ROOT / "archive/legacy/README.md"
EXPECTED_SHA256 = "2a7f493e754eaad1cc402ea338a0293c2d77c02e61c041bb689e375e25f28a08"
EXPECTED_MEMBERS = {
    "joinquant/README.md",
    "joinquant/fun.py",
    "joinquant/A股动量排行选股择时.ipynb",
    "joinquant/数据下载.ipynb",
    "notebook/导入聚宽数据.ipynb",
}


def test_joinquant_source_is_archived_outside_active_tree():
    assert not (ROOT / "joinquant").exists()
    assert not (ROOT / "notebook/导入聚宽数据.ipynb").exists()
    assert ARCHIVE.is_file()
    assert ARCHIVE_README.is_file()


def test_joinquant_archive_is_complete_reproducible_and_safe_to_extract():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == EXPECTED_SHA256

    with zipfile.ZipFile(ARCHIVE) as archive:
        names = set(archive.namelist())
        assert names == EXPECTED_MEMBERS
        assert archive.testzip() is None
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute()
            assert ".." not in path.parts
        legacy_helper = archive.read("joinquant/fun.py").decode("utf-8")

    assert "from jqdata import *" in legacy_helper
    assert "import cl" in legacy_helper
    assert "web_batch_get_cl_datas" in legacy_helper


def test_archive_readme_marks_joinquant_as_unsupported_history():
    readme = ARCHIVE_README.read_text(encoding="utf-8")
    assert EXPECTED_SHA256 in readme
    assert "不属于" in readme
    assert "PYTHONPATH" in readme
    assert "jqdata" in readme
    assert "已经从当前运行树移除的 `cl`" in readme
