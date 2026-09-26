with open('extract_smart.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace part assignments
text = text.replace('part = cells[1]\n', 'part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))\n')
text = text.replace('part_r = cells[6]\n', 'part_r = " ".join(list(dict.fromkeys([c for c in cells[6:8] if c and c not in (",,", "ÆÆ")])))\n')

# Specific for table 3 left which has 1,2,3 for part
text = text.replace(
    'elif ti == 3 and nc == 11:\n            # Left: 0,1,4,5\n            sr = cells[0]\n            part = cells[1]',
    'elif ti == 3 and nc == 11:\n            # Left: 0,1,4,5\n            sr = cells[0]\n            part = " ".join(list(dict.fromkeys([c for c in cells[1:4] if c and c not in (",,", "ÆÆ")])))'
)

# Specific for table 1 right which has 6,7,8,9,10 for part
text = text.replace(
    '# Right: 5,6,11(Pack),13,14\n            sr_r = cells[5]\n            part_r = cells[6]',
    '# Right: 5,6,11(Pack),13,14\n            sr_r = cells[5]\n            part_r = " ".join(list(dict.fromkeys([c for c in cells[6:11] if c and c not in (",,", "ÆÆ")])))'
)

# Specific for table 5 right which has 5,6,7,8,9 for part
text = text.replace(
    '# Right: 4,5,10(HSN),11,12\n            sr_r = cells[4]\n            part_r = cells[5]',
    '# Right: 4,5,10(HSN),11,12\n            sr_r = cells[4]\n            part_r = " ".join(list(dict.fromkeys([c for c in cells[5:10] if c and c not in (",,", "ÆÆ")])))'
)

with open('extract_smart.py', 'w', encoding='utf-8') as f:
    f.write(text)
