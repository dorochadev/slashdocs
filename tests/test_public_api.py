import slashdocs


def test_public_api_surface() -> None:
    assert callable(slashdocs.attach)
    assert callable(slashdocs.docs)
    assert slashdocs.__version__ == "0.1.0"
    assert set(slashdocs.__all__) == {"attach", "docs", "__version__"}
