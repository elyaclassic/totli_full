with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 3003-qatorni o'zgartirish (0-indexed: 3002)
lines[3002] = "            phone=pwa_phone or phone,\n"

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("DONE")
