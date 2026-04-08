import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

def calculate_twr_old(portfolio_values: List[Tuple[datetime, float]], cashflows: List[Tuple[datetime, float]]) -> Optional[float]:
    # Copy of the current buggy logic
    if not portfolio_values or len(portfolio_values) < 2:
        return None
    val_dict = {d.date() if isinstance(d, datetime) else d: v for d, v in portfolio_values}
    cf_dict = {}
    for date, amount in cashflows:
        date_key = date.date() if isinstance(date, datetime) else date
        cf_dict[date_key] = cf_dict.get(date_key, 0) + amount
    flow_dates = sorted(cf_dict.keys())
    all_dates = sorted(val_dict.keys())
    compound = 1.0
    sub_period_starts = sorted(set([all_dates[0]] + [fd for fd in flow_dates if fd in val_dict and fd != all_dates[0]] + [all_dates[-1]]))
    
    for i in range(len(sub_period_starts) - 1):
        start_date = sub_period_starts[i]
        end_date = sub_period_starts[i + 1]
        v_start = val_dict.get(start_date, 0)
        v_end = val_dict.get(end_date, 0)
        cf_at_start = cf_dict.get(start_date, 0)
        adjusted_start = v_start + abs(cf_at_start) if cf_at_start < 0 else v_start - cf_at_start
        
        if adjusted_start > 0 and i > 0:
            sub_return = v_end / adjusted_start
            compound *= sub_return
        elif i == 0 and v_start > 0:
            sub_return = v_end / v_start if v_start > 0 else 1.0
            compound *= sub_return
            
    return round((compound - 1) * 100, 2)

def test_anomaly():
    print("Testing Anomaly (The Bug)...")
    base_date = datetime(2024, 1, 1)
    
    # Case: User deposits 1000, then buys 1000 of stock. Stock goes down to 900.
    # Total return: -10%. TWR should be -10%.
    
    # Portfolio Values (Assets only, as current AnalyticsService does)
    portfolio_values = [
        (base_date, 0.0),            # Day 1: Start
        (base_date + timedelta(1), 0.0), # Day 2: Deposit 1000 (Assets still 0)
        (base_date + timedelta(2), 1000.0), # Day 3: Buy 1000 (Assets now 1000)
        (base_date + timedelta(3), 900.0), # Day 4: Market Crash (Assets now 900)
    ]
    
    # Current buggy cashflow logic: treats everything as flow
    cashflows = [
        (base_date + timedelta(1), -1000.0), # Deposit
        (base_date + timedelta(2), -1000.0), # Buy
    ]
    
    twr = calculate_twr_old(portfolio_values, cashflows)
    print(f"Buggy TWR: {twr}%")
    # Expected anomaly check: compound likely fails because of zeros or double counting flows

if __name__ == "__main__":
    test_anomaly()
