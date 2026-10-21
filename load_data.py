import sqlite3, glob, os
import pandas as pd

conn = sqlite3.connect("olist.db")
for f in glob.glob("data/raw/*.csv"):
    name = (os.path.basename(f)
            .replace("olist_", "").replace("_dataset", "").replace(".csv", ""))
    pd.read_csv(f).to_sql(name, conn, if_exists="replace", index=False)
    print("loaded:", name)
conn.close()