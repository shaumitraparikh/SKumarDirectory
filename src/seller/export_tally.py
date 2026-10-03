import csv
import json
import sys
from pathlib import Path
import pandas as pd

def main():
    if len(sys.argv) < 2:
        print("Usage: python export_tally.py YYYY-MM")
        sys.exit(1)
        
    month = sys.argv[1]
    repo_dir = Path(__file__).parent.parent.parent
    xlsx_file = repo_dir / "data" / "bills" / f"{month}.xlsx"
    csv_file = repo_dir / "data" / "bills" / f"{month}.csv"
    
    rows = []
    if xlsx_file.exists():
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if all_rows:
            headers = [str(c).strip() if c is not None else "" for c in all_rows[0]]
            for r in all_rows[1:]:
                if not any(v is not None and str(v).strip() for v in r):
                    continue
                rows.append({
                    headers[i]: str(r[i]).strip() if i < len(r) and r[i] is not None else ""
                    for i in range(len(headers))
                })
    elif csv_file.exists():
        with csv_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    else:
        print(f"No bills found for month: {month}")
        sys.exit(1)
        
    out_dir = repo_dir / "data" / "monthly_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"DayBook_{month}.xlsx"
    
    daybook_data = []
    hsn_data = []
    
    for row in rows:
            order = json.loads(row['order_json'])
            
            # Format Date
            date = order.get('createdAt', '')
            if date:
                date = date.replace('T', ' ').split('.')[0]
                
            buyer = order.get('buyer', {})
            particulars = buyer.get('name', 'Cash Customer')
            gstin = buyer.get('gstin', '')
            vch_no = order.get('id', '')
            totals = order.get('totals', {})
            
            subtotal = float(totals.get('subTotal', 0))
            grand_total = float(totals.get('grandTotal', 0))
            
            # Default 9% CGST and SGST
            cgst = round(subtotal * 0.09, 2)
            sgst = round(subtotal * 0.09, 2)
            round_off = round(grand_total - subtotal - cgst - sgst, 2)
            
            daybook_data.append({
                'Date': date,
                'Particulars': particulars,
                'Vch No.': vch_no,
                'Sales Tax No.': gstin,
                'Gross Total': grand_total,
                'Sale Net 18% A/c.': subtotal,
                'CGST 9% Received': cgst,
                'SGST 9% Received': sgst,
                'Round Up Sale': round_off,
                'IGST 18% Received': 0
            })
            
            # For items, order['items'] in search_catalog might be a dict or array depending on the codebase state
            items = order.get('items', [])
            if isinstance(items, dict):
                items_list = list(items.values())
            else:
                items_list = items
                
            for item in items_list:
                item_name = item.get('name', item.get('item_name', ''))
                hsn = item.get('hsn', item.get('hsn_code', ''))
                qty = float(item.get('quantity', item.get('qty', 0)))
                # Some versions of app might have unit_price or price
                price = float(item.get('unit_price', item.get('price', item.get('list_price', 0))))
                net = float(item.get('net_amount', qty * price))
                
                hsn_data.append({
                    'Date': date,
                    'Vch No.': vch_no,
                    'Item Name': item_name,
                    'HSN/SAC': hsn,
                    'Qty': qty,
                    'Rate': price,
                    'Taxable Value': net,
                    'CGST Rate': '9%',
                    'CGST Amount': round(net * 0.09, 2),
                    'SGST Rate': '9%',
                    'SGST Amount': round(net * 0.09, 2),
                    'IGST Rate': '0%',
                    'IGST Amount': 0
                })
                
    df_daybook = pd.DataFrame(daybook_data)
    
    header_rows = pd.DataFrame([
        ['List of All Sales Vouchers (export from SKumar POS)', f'{month}', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', ''],
    ], columns=df_daybook.columns)
    
    final_daybook = pd.concat([header_rows, df_daybook], ignore_index=True)
    
    df_hsn = pd.DataFrame(hsn_data)
    if not df_hsn.empty:
        header_rows_hsn = pd.DataFrame([
            ['HSN Summary (export from SKumar POS)', f'{month}', '', '', '', '', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', '', '', '', '', '', ''],
        ], columns=df_hsn.columns)
        final_hsn = pd.concat([header_rows_hsn, df_hsn], ignore_index=True)
    else:
        final_hsn = pd.DataFrame()

    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        final_daybook.to_excel(writer, sheet_name='DayBook', index=False)
        if not final_hsn.empty:
            final_hsn.to_excel(writer, sheet_name='HSN Summary', index=False)
            
    print(f"Exported successfully to {out_file}")

if __name__ == '__main__':
    main()
