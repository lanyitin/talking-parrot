"""Public API surface tests for ``talking_parrot.regression``.

Realises the **Decision: Module decomposition follows SRP** import surface
contract from the ``regression-runner`` change's ``design.md``.
"""

from __future__ import annotations


def test_public_symbols_exported() -> None:
    """The package re-exports the documented public symbols."""
    import talking_parrot.regression as regression

    expected = {
        "RegressionRunner",
        "score",
        "BaselineStore",
        "JsonBaselineStore",
        "render_report",
        "write_report",
    }
    for name in expected:
        assert hasattr(regression, name), (
            f"talking_parrot.regression is missing public symbol {name!r}; "
            "see Decision: Module decomposition follows SRP in design.md"
        )
    assert expected.issubset(set(regression.__all__))
