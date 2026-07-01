"""Product module test fixtures."""

import pytest


@pytest.fixture
def sample_product_data():
    return {
        "name": "阿莫西林胶囊",
        "major_category": "SM",
        "formulation_code": "AA",
        "product_type": "API",
        "spec": "0.5g",
    }
