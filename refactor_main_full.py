# Refactor main.py: replace dashboard block with include_router, remove duplicate /info block.
# Run when main.py still has inline dashboard code and/or duplicate /info routes.
import sys
path_main = "main.py"

with open(path_main, "r", encoding="utf-8") as f:
    lines = f.readlines()

n = len(lines)
changed = False

# ---- 1) Dashboard block ----
start_dash = None
for i, line in enumerate(lines):
    if "# DASHBOARDS" in line and i > 0 and "===" in lines[i-1]:
        start_dash = i - 1
        break

end_dash = None
if start_dash is not None:
    for i in range(n - 1, start_dash, -1):
        if 'dashboards/delivery.html"' in lines[i]:
            j = i
            while j < n and "})" not in lines[j]:
                j += 1
            if j < n:
                end_dash = j + 1
            break

if start_dash is not None and end_dash is not None:
    replacement = [
        "# DASHBOARDS — app/routes/dashboard.py (included with routers above)\n",
        "\n",
    ]
    lines = lines[:start_dash] + replacement + lines[end_dash:]
    n = len(lines)
    changed = True
    print("Replaced dashboard block with include_router")

    # Remove imports now only used in dashboard router (check_low_stock stays: purchase/sales/production confirm in main call it)
    lines = [l for l in lines if l.strip() != "from app.utils.dashboard_export import export_executive_dashboard"]
    lines = [l for l in lines if l.strip() != "from app.utils.live_data import executive_live_data, warehouse_live_data, delivery_live_data"]
    n = len(lines)

    # Add dashboard import if missing
    has_dashboard_import = any("dashboard as dashboard_routes" in l for l in lines)
    if not has_dashboard_import:
        for i, l in enumerate(lines):
            if "from app.routes import info as info_routes" in l:
                lines.insert(i + 1, "from app.routes import dashboard as dashboard_routes\n")
                n = len(lines)
                print("Added dashboard_routes import")
                break

# ---- 2) Duplicate /info block ----
start_info = None
for i, line in enumerate(lines):
    if "O'lchov birliklari bo'limi" in line and "moved to app/routes/info" in line:
        start_info = i
        break

end_info = None
if start_info is not None:
    for i in range(len(lines) - 1, start_info, -1):
        if 'url="/info/machines"' in lines[i] and "status_code=303" in lines[i]:
            end_info = i + 2
            break

if start_info is not None and end_info is not None:
    comment = [
        "# /info/* routes (units, categories, price-types, prices, cash, departments, directions, users, positions, regions, machines) — app/routes/info.py\n",
        "\n",
    ]
    lines = lines[:start_info] + comment + lines[end_info:]
    changed = True
    print("Removed duplicate /info block")

if changed:
    with open(path_main, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("main.py saved. Total lines:", len(lines))
else:
    print("Nothing to do (main.py already refactored or markers not found).")
