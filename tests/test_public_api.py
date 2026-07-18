import slashdocs


def test_public_api_surface() -> None:
    assert callable(slashdocs.attach)
    assert callable(slashdocs.docs)
    assert slashdocs.__version__ == "0.2.1"
    assert set(slashdocs.__all__) == {
        "attach",
        "commands_json",
        "commands_page",
        "docs",
        "mdx",
        "__version__",
    }
