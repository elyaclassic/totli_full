# ==========================================
# TOVAR KIRIMI (PURCHASE) ENDPOINTS
# ==========================================
# Bu kod main.py ga qo'shilishi kerak (284-qatordan keyin)

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_list(request: Request, db: Session = Depends(get_db)):
    """Tovar kirimlari ro'yxati"""
    purchases = db.query(Purchase).order_by(Purchase.date.desc()).limit(100).all()
    
    return templates.TemplateResponse("purchases/list.html", {
        "request": request,
        "purchases": purchases,
        "page_title": "Tovar kirimlari"
    })


@app.get("/purchases/new", response_class=HTMLResponse)
async def purchase_new(request: Request, db: Session = Depends(get_db)):
    """Yangi tovar kirimi"""
    products = db.query(Product).filter(Product.is_active == True).all()
    partners = db.query(Partner).filter(Partner.type.in_(["supplier", "both"])).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("purchases/new.html", {
        "request": request,
        "products": products,
        "partners": partners,
        "warehouses": warehouses,
        "page_title": "Yangi tovar kirimi"
    })


@app.post("/purchases/create")
async def purchase_create(
    request: Request,
    partner_id: int = Form(...),
    warehouse_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimini yaratish"""
    # Yangi raqam generatsiya
    today = datetime.now()
    count = db.query(Purchase).filter(
        Purchase.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    number = f"P-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"
    
    purchase = Purchase(
        number=number,
        partner_id=partner_id,
        warehouse_id=warehouse_id,
        status="draft"
    )
    db.add(purchase)
    db.commit()
    
    return RedirectResponse(url=f"/purchases/edit/{purchase.id}", status_code=303)


@app.get("/purchases/edit/{purchase_id}", response_class=HTMLResponse)
async def purchase_edit(request: Request, purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tahrirlash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    products = db.query(Product).filter(Product.is_active == True).all()
    
    return templates.TemplateResponse("purchases/edit.html", {
        "request": request,
        "purchase": purchase,
        "products": products,
        "page_title": f"Tovar kirimi: {purchase.number}"
    })


@app.post("/purchases/{purchase_id}/add-item")
async def purchase_add_item(
    purchase_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimiga mahsulot qo'shish"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    # Mahsulotni qo'shish
    total = quantity * price
    item = PurchaseItem(
        purchase_id=purchase_id,
        product_id=product_id,
        quantity=quantity,
        price=price,
        total=total
    )
    db.add(item)
    
    # Umumiy summani yangilash
    purchase.total = db.query(PurchaseItem).filter(
        PurchaseItem.purchase_id == purchase_id
    ).with_entities(db.func.sum(PurchaseItem.total)).scalar() or 0
    purchase.total += total
    
    db.commit()
    return RedirectResponse(url=f"/purchases/edit/{purchase_id}", status_code=303)


@app.post("/purchases/{purchase_id}/delete-item/{item_id}")
async def purchase_delete_item(purchase_id: int, item_id: int, db: Session = Depends(get_db)):
    """Tovar kirimidan mahsulotni o'chirish"""
    item = db.query(PurchaseItem).filter(PurchaseItem.id == item_id).first()
    if item:
        db.delete(item)
        
        # Umumiy summani yangilash
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        purchase.total = db.query(PurchaseItem).filter(
            PurchaseItem.purchase_id == purchase_id
        ).with_entities(db.func.sum(PurchaseItem.total)).scalar() or 0
        
        db.commit()
    
    return RedirectResponse(url=f"/purchases/edit/{purchase_id}", status_code=303)


@app.post("/purchases/{purchase_id}/confirm")
async def purchase_confirm(purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tasdiqlash va ombor qoldiqlarini yangilash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    if purchase.status != "draft":
        raise HTTPException(status_code=400, detail="Faqat qoralama holatidagi kirimlarni tasdiqlash mumkin")
    
    # Har bir mahsulot uchun ombor qoldiqlarini yangilash
    for item in purchase.items:
        stock = db.query(Stock).filter(
            Stock.warehouse_id == purchase.warehouse_id,
            Stock.product_id == item.product_id
        ).first()
        
        if stock:
            stock.quantity += item.quantity
        else:
            stock = Stock(
                warehouse_id=purchase.warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(stock)
        
        # Mahsulot narxini yangilash (oxirgi kirim narxi)
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.purchase_price = item.price
    
    # Statusni yangilash
    purchase.status = "confirmed"
    
    # Agar partner bo'lsa, balansni yangilash
    if purchase.partner_id:
        partner = db.query(Partner).filter(Partner.id == purchase.partner_id).first()
        if partner:
            partner.balance -= purchase.total  # Qarz (biz to'lashimiz kerak)
    
    db.commit()
    return RedirectResponse(url=f"/purchases", status_code=303)


@app.post("/purchases/{purchase_id}/cancel")
async def purchase_cancel(purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini bekor qilish"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    purchase.status = "cancelled"
    db.commit()
    return RedirectResponse(url="/purchases", status_code=303)
