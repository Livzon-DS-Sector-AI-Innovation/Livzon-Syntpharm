import pytest

from app.modules.hr.org_feishu import APP_ID_SETTING, load_hr_platform_credentials


class _Result:
    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[str, str]]:
        return self._rows


class _Session:
    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self._rows = rows

    async def execute(self, *args: object, **kwargs: object) -> _Result:
        return _Result(self._rows)


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [(APP_ID_SETTING, "cli_configured")],
    ],
)
async def test_sync_requires_both_credentials_in_hr_settings(rows: list[tuple[str, str]]) -> None:
    with pytest.raises(RuntimeError, match="未配置飞书平台应用凭证"):
        await load_hr_platform_credentials(_Session(rows))  # type: ignore[arg-type]
