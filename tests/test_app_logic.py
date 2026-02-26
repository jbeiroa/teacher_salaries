import pytest
import os
import re
from src.salary_app import process_citations, parse_report, navigate_carousel, REPORT_SECTIONS

def test_process_citations_format():
    """Verify that [[N]] converts to <sup> links."""
    text = "Inflation was high [[15]]. See reference [[2]]."
    processed = process_citations(text)
    
    assert '<sup><a href="#ref15">15</a></sup>' in processed
    assert '<sup><a href="#ref2">2</a></sup>' in processed
    assert '[[' not in processed

def test_process_citations_anchors():
    """Verify that starting lines with N. get an anchor ID."""
    text = "1. First Reference\n24. Last Reference"
    processed = process_citations(text)
    
    assert '<a id="ref1"></a>1.' in processed
    assert '<a id="ref24"></a>24.' in processed

def test_parse_report_structure(tmp_path, monkeypatch):
    """Test splitting a report into intro, clusters, and synthesis."""
    report_content = """# Intro
Intro text [[1]].

## **Cluster 1: Title 1**
Cluster 1 text.

## **Cluster 2: Title 2**
Cluster 2 text.

## **Synthesis and Future Outlook: Final**
Synthesis text.

## **References**
1. Ref 1.
"""
    report_file = tmp_path / "report_test.md"
    report_file.write_text(report_content)
    
    # Reset REPORT_SECTIONS for test
    REPORT_SECTIONS["en"] = {"intro": "", "clusters": [], "synthesis": ""}
    
    parse_report(str(report_file), "en")
    
    assert "Intro text" in REPORT_SECTIONS["en"]["intro"]
    assert len(REPORT_SECTIONS["en"]["clusters"]) == 2
    assert "Cluster 1 text" in REPORT_SECTIONS["en"]["clusters"][0]
    assert "Synthesis text" in REPORT_SECTIONS["en"]["synthesis"]
    assert "Ref 1" in REPORT_SECTIONS["en"]["synthesis"] 

def test_navigate_carousel_logic():
    from unittest.mock import patch
    
    # Mocking callback_context.triggered[0]['prop_id']
    with patch('src.salary_app.callback_context') as mock_ctx:
        # Case 1: Prev clicked at index 0
        mock_ctx.triggered = [{'prop_id': 'analytics-prev.n_clicks'}]
        assert navigate_carousel(1, 0, 0) == 7
        
        # Case 2: Next clicked at index 0
        mock_ctx.triggered = [{'prop_id': 'analytics-next.n_clicks'}]
        assert navigate_carousel(0, 1, 0) == 1
        
        # Case 3: Next clicked at index 7 (wrap)
        mock_ctx.triggered = [{'prop_id': 'analytics-next.n_clicks'}]
        assert navigate_carousel(0, 1, 7) == 0
        
        # Case 4: Prev clicked at index 7
        mock_ctx.triggered = [{'prop_id': 'analytics-prev.n_clicks'}]
        assert navigate_carousel(1, 0, 7) == 6
