from meridian.synthetic import generate_customers

import project


def test_smoke_generate_customers() -> None:
    df = generate_customers(3)
    assert df.height == 3
    assert df["customer_id"][0] == "C000001"


def test_project_version_present() -> None:
    assert project.__version__ == "0.1.0"
