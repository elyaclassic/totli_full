"""PWA login rows must be created from the user and employee forms."""
import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Agent, Driver, Employee, User
from app.routes.info import info_users_add
from app.utils.auth import hash_password
from main import agent_login, driver_login, employee_add


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _admin(db):
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        full_name="Admin",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return admin


def test_user_add_agent_can_pwa_login():
    db = _session()
    try:
        admin = _admin(db)
        result = asyncio.run(info_users_add(
            request=None,
            username="ali",
            password="secret",
            full_name="Ali Valiyev",
            role="agent",
            is_active=True,
            phone="",
            pwa_phone="+998901112233",
            vehicle_number="",
            vehicle_type="",
            db=db,
            current_user=admin,
        ))
        assert result.status_code == 303
        agent = db.query(Agent).filter(Agent.phone == "+998901112233").one()
        assert agent.full_name == "Ali Valiyev"
        assert agent.is_active is True
        user = db.query(User).filter(User.username == "ali").one()
        assert user.phone == "+998901112233"
        assert user.role == "agent"
        login = asyncio.run(agent_login("+998901112233", "+998901112233", db))
        assert login["success"] is True
        assert login["agent"]["id"] == agent.id
    finally:
        db.close()


def test_user_add_driver_stores_vehicle_and_can_pwa_login():
    db = _session()
    try:
        admin = _admin(db)
        result = asyncio.run(info_users_add(
            request=None,
            username="driver1",
            password="secret",
            full_name="Vali Haydovchi",
            role="driver",
            is_active=True,
            phone="",
            pwa_phone="+998907770000",
            vehicle_number="01 A 123 BC",
            vehicle_type="van",
            db=db,
            current_user=admin,
        ))
        assert result.status_code == 303
        driver = db.query(Driver).filter(Driver.phone == "+998907770000").one()
        assert driver.full_name == "Vali Haydovchi"
        assert driver.vehicle_number == "01 A 123 BC"
        assert driver.vehicle_type == "van"
        login = asyncio.run(driver_login("+998907770000", "+998907770000", db))
        assert login["success"] is True
        assert login["driver"]["id"] == driver.id
    finally:
        db.close()


def test_user_add_regular_does_not_create_agent():
    db = _session()
    try:
        admin = _admin(db)
        asyncio.run(info_users_add(
            request=None,
            username="office",
            password="secret",
            full_name="Ofis",
            role="user",
            is_active=True,
            phone="+998900000001",
            pwa_phone="",
            vehicle_number="",
            vehicle_type="",
            db=db,
            current_user=admin,
        ))
        assert db.query(Agent).count() == 0
        assert db.query(Driver).count() == 0
        assert db.query(User).filter(User.username == "office").one().phone == "+998900000001"
    finally:
        db.close()


def test_employee_add_agent_and_driver_create_pwa_rows():
    db = _session()
    try:
        agent_result = asyncio.run(employee_add(
            request=None,
            full_name="Sardor Agent",
            code="AGX",
            position="",
            department="",
            phone="",
            salary=0,
            employee_type="agent",
            pwa_phone="+998901234567",
            vehicle_number="",
            vehicle_type="",
            is_active=True,
            db=db,
        ))
        assert agent_result.status_code == 303
        employee = db.query(Employee).filter(Employee.code == "AGX").one()
        assert employee.phone == "+998901234567"
        assert employee.position == "Agent"
        agent = db.query(Agent).filter(Agent.phone == "+998901234567").one()
        assert agent.employee_id == employee.id
        assert agent.code == "AGX"
        login = asyncio.run(agent_login("+998901234567", "+998901234567", db))
        assert login["success"] is True

        asyncio.run(employee_add(
            request=None,
            full_name="Karim Haydovchi",
            code="DRX",
            position="",
            department="",
            phone="",
            salary=0,
            employee_type="driver",
            pwa_phone="+998909998877",
            vehicle_number="10 B 777 AA",
            vehicle_type="truck",
            is_active=True,
            db=db,
        ))
        driver = db.query(Driver).filter(Driver.phone == "+998909998877").one()
        assert driver.vehicle_number == "10 B 777 AA"
        assert driver.employee_id == db.query(Employee).filter(Employee.code == "DRX").one().id
        dlogin = asyncio.run(driver_login("+998909998877", "+998909998877", db))
        assert dlogin["success"] is True

        asyncio.run(employee_add(
            request=None,
            full_name="Oddiy Xodim",
            code="EMP1",
            position="Ishchi",
            department="Sex",
            phone="+998900000099",
            salary=1000,
            employee_type="regular",
            pwa_phone="",
            vehicle_number="",
            vehicle_type="",
            is_active=True,
            db=db,
        ))
        assert db.query(Agent).count() == 1
        assert db.query(Driver).count() == 1
        regular = db.query(Employee).filter(Employee.code == "EMP1").one()
        assert regular.phone == "+998900000099"
        assert regular.position == "Ishchi"
    finally:
        db.close()
