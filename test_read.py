import pandas as pd
import json

file_path = r'C:\Users\viken\Documents\TallyToJson converter\output\skumar\xlsx\GSTReturn_07_06_2026.xlsx'

df = pd.read_excel(file_path, sheet_name='b2b,sez,de', skiprows=4) # GSTR-1 usually has 4 header rows
print(df.head().to_dict(orient='records'))
