def rewrite_csv(csv_file, fieldnames, existing_rows, new_row):
    found = False
    for i, r in enumerate(existing_rows):
        if r.get('id') == new_row['id']:
            existing_rows[i] = new_row
            found = True
            break
    if not found:
        existing_rows.append(new_row)
        
    with csv_file.open(mode="w", encoding="utf-8-sig", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
