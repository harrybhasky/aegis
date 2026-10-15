from orchestrator_langgraph import parse_wns_from_opensta, parse_tns_from_opensta, parse_area_from_yosys

sample_opensta = """
Some startup text
Worst negative slack (WNS) -0.321
Total negative slack (TNS) -12.34
"""

sample_yosys = """
Some yosys text
Estimated area 12,345
"""

def test_parse_wns():
    assert abs(parse_wns_from_opensta(sample_opensta) - (-0.321)) < 1e-6

def test_parse_tns():
    assert abs(parse_tns_from_opensta(sample_opensta) - (-12.34)) < 1e-6

def test_parse_area():
    assert abs(parse_area_from_yosys(sample_yosys) - 12345.0) < 1e-6
