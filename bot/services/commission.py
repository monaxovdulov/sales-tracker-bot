"""
Commission calculation service
Handles commission calculation based on client count thresholds
"""

from typing import List, Tuple

# Thresholds: (max_clients, commission_rate)
THRESHOLDS: List[Tuple[int, float]] = [
    (10, 0.05),    # ≤10 clients → 5%
    (99999, 0.10)  # >10 clients → 10%
]

def calc(clients_count: int, amount: float) -> float:
    """
    Calculate commission based on client count and order amount
    
    Args:
        clients_count: Current number of clients for the worker
        amount: Order amount
        
    Returns:
        Commission amount rounded to 2 decimal places
    """
    commission_rate = 0.05  # Default rate
    
    for threshold, rate in THRESHOLDS:
        if clients_count <= threshold:
            commission_rate = rate
            break
    
    commission = amount * commission_rate
    return round(commission, 2) 