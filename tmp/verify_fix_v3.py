from datetime import date, timedelta
from typing import List, Optional

def calculate_twr_v3(daily_values: List[dict]) -> Optional[float]:
    if not daily_values or len(daily_values) < 2:
        return None
    sorted_days = sorted(daily_values, key=lambda x: x["fecha"])
    compound = 1.0
    has_started = False
    v_prev = 0.0
    for day in sorted_days:
        v_end = day["asset_value"]
        flow = day["net_flow"]
        if not has_started:
            if v_end > 0:
                has_started = True
                v_prev = v_end
            continue
        if v_prev <= 0 and v_end > 0:
            v_prev = v_end
            continue
        if v_prev > 0:
            r_t = (v_end - flow) / v_prev
            if 0.01 < r_t < 10.0:
                compound *= r_t
        v_prev = v_end
    return round((compound - 1) * 100, 2)

def test_v3():
    print("Testing Simplified Asset TWR...")
    base_date = date(2024, 1, 1)
    
    # Case: Buy 1000 on Day 2. Price remains 1000. Sell 500 on Day 4. Price goes to 600.
    # Day 2: AssetV=1000, Flow=1000. has_started=T, v_prev=1000.
    # Day 3: AssetV=1000, Flow=0. r_t=(1000-0)/1000=1.0. v_prev=1000.
    # Day 4: AssetV=500 (Sold 500), Flow=-500. r_t=(500-(-500))/1000 = 1000/1000 = 1.0. v_prev=500.
    # Day 5: AssetV=600 (Gains), Flow=0. r_t=(600-0)/500 = 1.2 (+20%).
    # Result should be 20%.
    
    daily_values = [
        {"fecha": base_date, "asset_value": 0.0, "net_flow": 0.0},
        {"fecha": base_date + timedelta(1), "asset_value": 1000.0, "net_flow": 1000.0},
        {"fecha": base_date + timedelta(2), "asset_value": 1000.0, "net_flow": 0.0},
        {"fecha": base_date + timedelta(3), "asset_value": 500.0, "net_flow": -500.0},
        {"fecha": base_date + timedelta(4), "asset_value": 600.0, "net_flow": 0.0},
    ]
    
    twr = calculate_twr_v3(daily_values)
    print(f"Asset TWR: {twr}%")
    # Expected: 20%.

if __name__ == "__main__":
    test_v3()
