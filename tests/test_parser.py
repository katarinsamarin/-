from src.scraper import parse_html


HTML = """
<html><body>
<h4>Intermediary attestation for the previous academic year 2025-2026</h4>
<div>
  <div>25.Б02-мкн</div>
  <div>12.09.2026 10:00 Экзамен Алгебра</div>
</div>
<div>
  <div>25.Б03-мкн</div>
  <div>15.09.2026 12:30 Exam Analysis</div>
</div>
</body></html>
"""


def test_parser_finds_groups():
    result = parse_html(HTML, ("25.Б02-мкн", "25.Б03-мкн"))
    assert result
    assert {x["group"] for x in result} == {"25.Б02-мкн", "25.Б03-мкн"}
