# tests/conftest.py
import tempfile

import pytest


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
        "overall_score": 72.0,
    }