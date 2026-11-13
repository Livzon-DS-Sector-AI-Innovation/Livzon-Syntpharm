# mypy: ignore-errors
"""get_ledger_summary 今年新增计数与证书有效期预警的边界测试。

测试库可能已有业务数据，所有断言均基于「插入前后两次 summary 的差值」。
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.certificate import RegistrationCertificate
from app.modules.registration.models.copp_certificate import CoppCertificate
from app.modules.registration.models.domestic_approval import DomesticApproval
from app.modules.registration.service.ledger import EXPIRING_SOON_DAYS, get_ledger_summary


def _domestic(product_name: str, **kwargs) -> DomesticApproval:
    return DomesticApproval(product_name=product_name, **kwargs)


async def test_summary_new_this_year_and_expiring_baseline(db_session: AsyncSession):
    """不插入数据时字段存在且类型正确（不假设库为空）。"""
    summary = await get_ledger_summary(db_session)
    assert summary.domestic_new_this_year >= 0
    assert summary.overseas_new_this_year >= 0
    assert summary.copp_new_this_year >= 0
    assert summary.wc_new_this_year >= 0
    assert summary.expired_count >= 0
    assert summary.expiring_soon_count >= 0
    assert len(summary.expiring_certificates) == summary.expired_count + summary.expiring_soon_count


async def test_new_this_year_counts_by_issue_date(db_session: AsyncSession):
    """今年新增只统计 issue_date 落在当年的记录；去年与空日期不计入。"""
    today = date.today()
    baseline = await get_ledger_summary(db_session)

    db_session.add_all(
        [
            _domestic("测试-今年-1", issue_date=today),
            _domestic("测试-今年-2", issue_date=date(today.year, 1, 1)),
            _domestic("测试-去年", issue_date=date(today.year - 1, 12, 31)),
            _domestic("测试-空日期", issue_date=None),
        ]
    )
    await db_session.flush()

    summary = await get_ledger_summary(db_session)
    assert summary.domestic_new_this_year - baseline.domestic_new_this_year == 2


async def test_expiring_certificates_window_boundary(db_session: AsyncSession):
    """预警窗口：已过期 + 未来 EXPIRING_SOON_DAYS 天内到期；窗口外及空有效期不进入清单。"""
    today = date.today()
    baseline = await get_ledger_summary(db_session)

    expired = _domestic("测试-已过期", valid_until=today - timedelta(days=5))
    in_edge1 = _domestic("测试-窗口内1", valid_until=today + timedelta(days=EXPIRING_SOON_DAYS - 1))
    in_edge2 = _domestic("测试-窗口内2", valid_until=today + timedelta(days=EXPIRING_SOON_DAYS))
    out_edge = _domestic("测试-窗口外", valid_until=today + timedelta(days=EXPIRING_SOON_DAYS + 1))
    no_date = _domestic("测试-无有效期", valid_until=None)
    db_session.add_all([expired, in_edge1, in_edge2, out_edge, no_date])
    await db_session.flush()

    summary = await get_ledger_summary(db_session)
    new_items = {item.product_name: item for item in summary.expiring_certificates}

    # 已过期 + 窗口内（边界含当天）进入清单，窗口外与空日期不进入
    assert new_items["测试-已过期"].days_left == -5
    assert new_items["测试-窗口内1"].days_left == EXPIRING_SOON_DAYS - 1
    assert new_items["测试-窗口内2"].days_left == EXPIRING_SOON_DAYS
    assert "测试-窗口外" not in new_items
    assert "测试-无有效期" not in new_items

    assert summary.expired_count - baseline.expired_count == 1
    assert summary.expiring_soon_count - baseline.expiring_soon_count == 2
    # 清单按有效期升序
    assert summary.expiring_certificates == sorted(
        summary.expiring_certificates, key=lambda item: item.valid_until
    )


async def test_expiring_certificates_ledger_type_and_soft_delete(db_session: AsyncSession):
    """ledger_type 标记来源子表；软删除记录不计入预警与新增。"""
    today = date.today()
    baseline = await get_ledger_summary(db_session)

    db_session.add_all(
        [
            CoppCertificate(product_name="测试-COPP-临期", valid_until=today + timedelta(days=10)),
            _domestic("测试-软删-临期", valid_until=today + timedelta(days=10), is_deleted=True),
            _domestic("测试-软删-今年", issue_date=today, is_deleted=True),
        ]
    )
    await db_session.flush()

    summary = await get_ledger_summary(db_session)
    by_name = {item.product_name: item for item in summary.expiring_certificates}

    assert by_name["测试-COPP-临期"].ledger_type == "copp"
    assert "测试-软删-临期" not in by_name
    assert summary.domestic_new_this_year == baseline.domestic_new_this_year
    assert summary.expiring_soon_count - baseline.expiring_soon_count == 1


async def test_expiring_include_registration_certificates(db_session: AsyncSession):
    """主证书表纳入预警：ledger_type='certificate'、certificate_name 为空、窗口外剔除、不计入今年新增。"""
    today = date.today()
    baseline = await get_ledger_summary(db_session)

    db_session.add_all(
        [
            RegistrationCertificate(
                product_name="测试-主证-已过期", market="中国",
                certificate_type="domestic_approval",
                valid_until=today - timedelta(days=3),
            ),
            RegistrationCertificate(
                product_name="测试-主证-紧急档", market="中国",
                certificate_type="domestic_approval",
                valid_until=today + timedelta(days=150),
            ),
            RegistrationCertificate(
                product_name="测试-主证-临期档", market="美国",
                certificate_type="overseas_registration",
                valid_until=today + timedelta(days=300),
            ),
            RegistrationCertificate(
                product_name="测试-主证-窗口外", market="美国",
                certificate_type="overseas_registration",
                valid_until=today + timedelta(days=EXPIRING_SOON_DAYS + 35),
            ),
        ]
    )
    await db_session.flush()

    summary = await get_ledger_summary(db_session)
    by_name = {item.product_name: item for item in summary.expiring_certificates}

    assert by_name["测试-主证-已过期"].ledger_type == "certificate"
    assert by_name["测试-主证-已过期"].days_left == -3
    assert by_name["测试-主证-已过期"].certificate_name is None
    assert by_name["测试-主证-紧急档"].ledger_type == "certificate"
    assert by_name["测试-主证-临期档"].ledger_type == "certificate"
    assert "测试-主证-窗口外" not in by_name

    assert summary.expired_count - baseline.expired_count == 1
    assert summary.expiring_soon_count - baseline.expiring_soon_count == 2
    # 主证书表无发证日期字段，不参与今年新增统计
    assert summary.domestic_new_this_year == baseline.domestic_new_this_year
    # 清单按有效期升序
    assert summary.expiring_certificates == sorted(
        summary.expiring_certificates, key=lambda item: item.valid_until
    )
