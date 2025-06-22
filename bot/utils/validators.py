"""
Validation utilities module
Contains regex patterns and validation functions
"""

import re

# Regex patterns
PHONE_RGX = r"^\d{10,15}$"
MONEY_RGX = r"^\d+(?:[.,]\d{1,2})?$"
URL_RGX = r"^https?://"

def is_phone(s: str) -> bool:
    """
    Validate phone number format
    
    Args:
        s: String to validate
        
    Returns:
        True if valid phone number, False otherwise
    """
    return bool(re.match(PHONE_RGX, s.strip()))

def is_money(s: str) -> bool:
    """
    Validate money format and normalize comma to dot
    
    Args:
        s: String to validate
        
    Returns:
        True if valid money format, False otherwise
    """
    # Normalize comma to dot
    normalized = s.strip().replace(",", ".")
    return bool(re.match(MONEY_RGX, normalized))

def normalize_money(s: str) -> str:
    """
    Normalize money string by replacing comma with dot
    
    Args:
        s: Money string to normalize
        
    Returns:
        Normalized money string
    """
    return s.strip().replace(",", ".")

def is_url(s: str) -> bool:
    """
    Validate URL format
    
    Args:
        s: String to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    return bool(re.match(URL_RGX, s.strip())) 