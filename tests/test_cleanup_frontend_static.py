from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_templates_do_not_load_baidu_analytics():
    templates = ROOT / "web/tradingview_zy_chart/cl_app/templates"
    for path in templates.glob("*.html"):
        source = path.read_text(encoding="utf-8")
        assert "hm.baidu.com" not in source, path.name
        assert "572abd07e459c48e1c15b1cb90a68ee4" not in source, path.name
