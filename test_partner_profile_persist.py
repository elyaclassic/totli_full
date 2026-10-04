"""Kontragent formasi rekvizitlari saqlanishi."""
import asyncio
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Partner
from main import partner_add, partner_edit


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


PROFILE = dict(
    legal_name="Totli MCHJ",
    contact_person="Ali Valiyev",
    phone2="+998901112233",
    landmark="Bozor yonida",
    latitude="41.31",
    longitude="69.24",
    visit_day="0",
    category="A",
    region="tashkent",
    customer_type="wholesale",
    sales_channel="direct",
    product_categories="food",
    inn="123456789",
    account="20208000123456789001",
    bank="Ipak Yuli",
    mfo="00444",
    oked="10730",
    pinfl="12345678901234",
    contract_number="SH-15",
    contract_date="2026-03-01",
    notes="Shartnoma asosida",
)


def test_partner_add_persists_requisites():
    db = _session()
    try:
        result = asyncio.run(partner_add(
            request=None,
            name="Do'kon 1",
            type="customer",
            phone="+998901234567",
            address="Chilonzor",
            credit_limit=1000000,
            discount_percent=5,
            db=db,
            **PROFILE,
        ))
        assert result.status_code == 303
        partner = db.query(Partner).filter(Partner.name == "Do'kon 1").one()
        assert partner.legal_name == "Totli MCHJ"
        assert partner.contact_person == "Ali Valiyev"
        assert partner.phone2 == "+998901112233"
        assert partner.landmark == "Bozor yonida"
        assert partner.latitude == 41.31
        assert partner.longitude == 69.24
        assert partner.visit_day == 0
        assert partner.category == "A"
        assert partner.region == "tashkent"
        assert partner.customer_type == "wholesale"
        assert partner.sales_channel == "direct"
        assert partner.product_categories == "food"
        assert partner.inn == "123456789"
        assert partner.account == "20208000123456789001"
        assert partner.bank == "Ipak Yuli"
        assert partner.mfo == "00444"
        assert partner.oked == "10730"
        assert partner.pinfl == "12345678901234"
        assert partner.contract_number == "SH-15"
        assert partner.contract_date == date(2026, 3, 1)
        assert partner.notes == "Shartnoma asosida"
        assert partner.balance in (None, 0)
    finally:
        db.close()


def test_partner_edit_updates_requisites_without_touching_balance():
    db = _session()
    try:
        partner = Partner(
            name="Eski nom",
            type="customer",
            phone="+998900000000",
            balance=-250000,
            inn="000",
        )
        db.add(partner)
        db.commit()
        db.refresh(partner)

        result = asyncio.run(partner_edit(
            partner_id=partner.id,
            name="Yangi nom",
            type="both",
            phone="+998907654321",
            address="Yunusobod",
            credit_limit=0,
            discount_percent=0,
            db=db,
            **PROFILE,
        ))
        assert result.status_code == 303
        db.refresh(partner)
        assert partner.name == "Yangi nom"
        assert partner.type == "both"
        assert partner.balance == -250000
        assert partner.inn == "123456789"
        assert partner.bank == "Ipak Yuli"
        assert partner.visit_day == 0
        assert partner.contract_date == date(2026, 3, 1)
    finally:
        db.close()
