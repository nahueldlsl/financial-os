from datetime import datetime, date, timedelta
from typing import List, Optional

def calculate_twr_new(daily_values: List[dict]) -> Optional[float]:
    if not daily_values or len(daily_values) < 2:
        return None
    sorted_days = sorted(daily_values, key=lambda x: x["fecha"])
    compound = 1.0
    has_started = False
    v_prev = 0.0
    for day in sorted_days:
        v_end = day["total_value"]
        flow = day["external_flow"]
        if not has_started:
            if v_end > 0:
                has_started = True
                v_prev = v_end
            continue
        if v_prev > 0:
            # Rt = (V_end - Flow) / V_prev
            r_t = (v_end - flow) / v_prev
            compound *= r_t
        v_prev = v_end
    return round((compound - 1) * 100, 2)

def test_fix():
    print("Testing Fix (New Logic)...")
    base_date = date(2024, 1, 1)
    
    # Case: User deposits 1000 on Day 2. Buys 1000 of stock on Day 3. Stock goes down to 900 on Day 4.
    # Total return: -10%. TWR should be -10%.
    
    # Simulating the data aggregation in calculate()
    daily_values = [
        {"fecha": base_date, "total_value": 0.0, "external_flow": 0.0},
        {"fecha": base_date + timedelta(1), "total_value": 1000.0, "external_flow": 1000.0}, # Deposit 1000
        {"fecha": base_date + timedelta(2), "total_value": 1000.0, "external_flow": 0.0},    # Buy (Total value stays 1000)
        {"fecha": base_date + timedelta(3), "total_value": 900.0, "external_flow": 0.0},     # Market crash (Total value stays 900)
    ]
    
    twr = calculate_twr_new(daily_values)
    print(f"New TWR: {twr}%")
    # Expected: 
    # Day 2: has_started=True, v_prev=1000
    # Day 3: r_t = (1000 - 0) / 1000 = 1.0. compound = 1.0. v_prev=1000
    # Day 4: r_t = (900 - 0) / 1000 = 0.9. compound = 0.9. v_prev=900
    # (0.9 - 1) * 100 = -10%. Correct!

if __name__ == "__main__":
    test_fix()
