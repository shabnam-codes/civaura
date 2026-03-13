import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# ═══════════════════════════════════════════════
# PATHS — relative to this file's location
# ═══════════════════════════════════════════════
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, 'Data')
EXCEL_PATH = os.path.join(DATA_DIR, 'CategoryCode_Mapping.xlsx')
MODEL_PATH = os.path.join(DATA_DIR, 'resolution_model.pkl')

# ═══════════════════════════════════════════════
# STEP 1 — LOAD EXCEL SHEETS
# ═══════════════════════════════════════════════
print("⏳ Loading Excel sheets...")
categories_df   = pd.read_excel(EXCEL_PATH, sheet_name='Complaint Category')
input_fields_df = pd.read_excel(EXCEL_PATH, sheet_name='Input Fields')
movement_df     = pd.read_excel(EXCEL_PATH, sheet_name='Movement Mapping')
fixed_dest_df   = pd.read_excel(EXCEL_PATH, sheet_name='Fixed Destination')
print(f"✅ Complaint Category : {len(categories_df)} rows")
print(f"✅ Input Fields       : {len(input_fields_df)} rows")
print(f"✅ Movement Mapping   : {len(movement_df)} rows")
print(f"✅ Fixed Destination  : {len(fixed_dest_df)} rows")

# ═══════════════════════════════════════════════
# STEP 2 — CLEAN CATEGORIES
# ═══════════════════════════════════════════════
print("\n⏳ Cleaning category data...")
categories_df = categories_df.dropna(subset=['Code', 'Description'])
categories_df['Code'] = pd.to_numeric(categories_df['Code'], errors='coerce')
categories_df = categories_df.dropna(subset=['Code'])
categories_df['Code'] = categories_df['Code'].astype(int)
categories_df['Description'] = categories_df['Description'].str.strip()
print(f"✅ Clean categories   : {len(categories_df)} rows")

# ═══════════════════════════════════════════════
# STEP 3 — BUILD USEFUL LISTS
# ═══════════════════════════════════════════════
print("\n⏳ Building lookup lists...")
category_list = categories_df[['Code', 'Description']].values.tolist()
org_list      = categories_df['OrgCode'].dropna().unique().tolist()
cats_encoded  = categories_df['Code'].astype(str).tolist()
print(f"✅ Category list      : {len(category_list)} entries")
print(f"✅ Org codes          : {len(org_list)} unique")

# ═══════════════════════════════════════════════
# STEP 4 — BUILD ROUTING DICTIONARY
# ═══════════════════════════════════════════════
print("\n⏳ Building routing dictionary...")
routing_dict = {}
for _, row in movement_df.iterrows():
    try:
        key = (int(row['categoryCodeFrom']), str(row['fromOrg']))
        routing_dict[key] = str(row['toOrg'])
    except:
        continue

fixed_dest_dict = {}
for _, row in fixed_dest_df.iterrows():
    try:
        fixed_dest_dict[int(row['FinalCategory'])] = str(row['Destination'])
    except:
        continue

print(f"✅ Routing rules      : {len(routing_dict)} entries")
print(f"✅ Fixed destinations : {len(fixed_dest_dict)} entries")

# ═══════════════════════════════════════════════
# STEP 5 — RESOLUTION TIME MODEL
# ═══════════════════════════════════════════════
print("\n⏳ Setting up resolution time model...")
le_cat = LabelEncoder()
le_org = LabelEncoder()
le_cat.fit(cats_encoded)
le_org.fit(org_list)

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        saved            = pickle.load(f)
    resolution_model = saved['model']
    le_cat           = saved['le_cat']
    le_org           = saved['le_org']
    print("✅ Resolution model  : loaded from saved file")
else:
    print("⏳ Training resolution model on mock data...")
    np.random.seed(42)
    n         = 1000
    mock_cats = np.random.choice(cats_encoded, n)
    mock_orgs = np.random.choice(org_list, n)
    mock_days = np.random.randint(1, 30, n)
    X = np.column_stack([
        le_cat.transform(mock_cats),
        le_org.transform(mock_orgs)
    ])
    resolution_model = LinearRegression()
    resolution_model.fit(X, mock_days)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model'  : resolution_model,
            'le_cat' : le_cat,
            'le_org' : le_org
        }, f)
    print("✅ Resolution model  : trained and saved")

# ═══════════════════════════════════════════════
# STEP 6 — HELPER FUNCTIONS
# ═══════════════════════════════════════════════
def get_resolution_days(category_code, org_code):
    try:
        cat_str = str(category_code)
        org_str = str(org_code)
        if cat_str not in le_cat.classes_:
            cat_str = le_cat.classes_[0]
        if org_str not in le_org.classes_:
            org_str = le_org.classes_[0]
        ci   = le_cat.transform([cat_str])[0]
        oi   = le_org.transform([org_str])[0]
        days = max(1, round(resolution_model.predict([[ci, oi]])[0]))
        return days
    except Exception as e:
        print(f"⚠️ Resolution fallback: {e}")
        return 7

def get_routing(category_code, org_code):
    try:
        key  = (int(category_code), str(org_code))
        dest = routing_dict.get(key)
        if not dest:
            dest = fixed_dest_dict.get(int(category_code), 'GENERAL_DEPT')
        return dest
    except Exception as e:
        print(f"⚠️ Routing fallback: {e}")
        return 'GENERAL_DEPT'

def get_category_name(code):
    try:
        match = categories_df[categories_df['Code'] == int(code)]
        if not match.empty:
            return match.iloc[0]['Description']
        return 'Unknown Category'
    except:
        return 'Unknown Category'

def get_required_fields(category_code):
    try:
        fields = input_fields_df[
            input_fields_df['Code'] == category_code
        ]
        return fields[['FieldName', 'DisplayLable', 'IsMandatory']].to_dict('records')
    except:
        return []

# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
print("\n" + "=" * 45)
print("✅ data_loader.py ready")
print("=" * 45)
print("  categories_df      → full category dataframe")
print("  input_fields_df    → input fields dataframe")
print("  movement_df        → movement mapping dataframe")
print("  fixed_dest_df      → fixed destination dataframe")
print("  category_list      → [[code, description], ...]")
print("  org_list           → [org_code, ...]")
print("  cats_encoded       → [str(code), ...]")
print("  routing_dict       → {(cat,org): dest}")
print("  fixed_dest_dict    → {category: destination}")
print("  resolution_model   → sklearn LinearRegression")
print("  get_resolution_days(category_code, org_code)")
print("  get_routing(category_code, org_code)")
print("  get_category_name(code)")
print("  get_required_fields(category_code)")
