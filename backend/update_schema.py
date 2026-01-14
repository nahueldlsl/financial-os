import sqlite3

def update_schema():
    print("Connecting to financial.db...")
    con = sqlite3.connect("financial.db")
    cur = con.cursor()
    
    try:
        # Add cached_price
        try:
            cur.execute("ALTER TABLE asset ADD COLUMN cached_price FLOAT")
            print("Added column: cached_price")
        except sqlite3.OperationalError as e:
            print(f"Could not add cached_price: {e}")

        # Add last_updated
        try:
            cur.execute("ALTER TABLE asset ADD COLUMN last_updated DATETIME")
            print("Added column: last_updated")
        except sqlite3.OperationalError as e:
            print(f"Could not add last_updated: {e}")
            
        con.commit()
        print("Schema update committed.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    update_schema()
