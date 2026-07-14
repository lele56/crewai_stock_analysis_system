# tests/conftest.py
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_analysis_scores():
    return {
        "fundamental_analyst": 75.0,
        "risk_assessment_specialist": 60.0,
        "industry_expert": 80.0,
        "quantitative_analyst": 70.0,
        "overall_score": 72.0,
    }