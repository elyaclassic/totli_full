# ==========================================
# XODIMLAR (EMPLOYEES) MANAGEMENT  
# ==========================================

@app.get("/employees")
async def employees_list(request: Request, db: Session = Depends(get_db)):
    """Xodimlar ro'yxati"""
    employees = db.query(Employee).all()
    return templates.TemplateResponse("employees/list.html", {
        "request": request,
        "employees": employees
    })


@app.post("/employees/add")
async def employee_add(
    request: Request,
    employee_type: str = Form(...),
    full_name: str = Form(...),
    code: str = Form(...),
    salary: float = Form(0),
    position: str = Form(None),
    department: str = Form(None),
    phone: str = Form(None),
    pwa_phone: str = Form(None),
    pwa_password: str = Form(None),
    vehicle_number: str = Form(None),
    vehicle_type: str = Form(None),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Yangi xodim qo'shish (oddiy/agent/haydovchi)"""
    try:
        if employee_type == "regular":
            # Oddiy xodim
            employee = Employee(
                code=code,
                full_name=full_name,
                position=position,
                department=department,
                phone=phone,
                salary=salary,
                hire_date=datetime.now()
            )
            db.add(employee)
            db.commit()
            
        elif employee_type == "agent":
            # Agent yaratish
            agent = Agent(
                full_name=full_name,
                phone=pwa_phone,
                is_active=is_active
            )
            db.add(agent)
            db.commit()
            
            # Oddiy xodim sifatida ham saqlash
            employee = Employee(
                code=code,
                full_name=full_name,
                position="Agent",
                phone=pwa_phone,
                salary=salary,
                hire_date=datetime.now()
            )
            db.add(employee)
            db.commit()
            
        elif employee_type == "driver":
            # Haydovchi yaratish
            driver = Driver(
                full_name=full_name,
                phone=pwa_phone,
                vehicle_number=vehicle_number,
                vehicle_type=vehicle_type,
                is_active=is_active
            )
            db.add(driver)
            db.commit()
            
            # Oddiy xodim sifatida ham saqlash
            employee = Employee(
                code=code,
                full_name=full_name,
                position="Haydovchi",
                phone=pwa_phone,
                salary=salary,
                hire_date=datetime.now()
            )
            db.add(employee)
            db.commit()
        
        return RedirectResponse(url="/employees", status_code=303)
    except Exception as e:
        print(f"Xodim qo'shishda xato: {e}")
        return RedirectResponse(url="/employees?error=1", status_code=303)
