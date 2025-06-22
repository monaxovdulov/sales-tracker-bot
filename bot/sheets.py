"""
Google Sheets integration module
Handles all operations with Google Sheets API
"""

import time
import gspread
from typing import Optional, Dict, Any
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from config import GSPREAD_CREDENTIALS, SPREADSHEET_ID

# Global variables for caching
_spreadsheet: Optional[gspread.Spreadsheet] = None
_gc: Optional[gspread.Client] = None

def _get_client() -> gspread.Client:
    """Get authenticated gspread client with caching"""
    global _gc
    if _gc is None:
        credentials = Credentials.from_service_account_file(GSPREAD_CREDENTIALS)
        _gc = gspread.authorize(credentials)
    return _gc

def sh() -> gspread.Spreadsheet:
    """Get spreadsheet instance with caching"""
    global _spreadsheet
    if _spreadsheet is None:
        client = _get_client()
        _spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return _spreadsheet

def workers_ws() -> gspread.Worksheet:
    """Get Workers worksheet"""
    return sh().worksheet("Workers")

def clients_ws() -> gspread.Worksheet:
    """Get Clients worksheet"""
    return sh().worksheet("Clients")

def withdrawals_ws() -> gspread.Worksheet:
    """Get Withdrawals worksheet"""
    return sh().worksheet("Withdrawals")

def _retry_api_call(func, max_retries: int = 3, backoff_factor: float = 1.0):
    """Retry API call with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except APIError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = backoff_factor * (2 ** attempt)
                time.sleep(wait_time)
                continue
            raise
    return None

def get_worker(tg_id: int) -> Optional[Dict[str, Any]]:
    """Get worker data by Telegram ID"""
    def _get():
        ws = workers_ws()
        records = ws.get_all_records()
        for record in records:
            if record.get("tg_id") == tg_id:
                return record
        return None
    
    return _retry_api_call(_get)

def add_worker(tg_id: int, username: str) -> None:
    """Add new worker with pending status"""
    def _add():
        ws = workers_ws()
        ws.append_row([tg_id, username, "pending", 0, 0.0])
    
    _retry_api_call(_add)

def approve_worker(tg_id: int) -> None:
    """Approve worker (change status from pending to worker)"""
    def _approve():
        ws = workers_ws()
        records = ws.get_all_records()
        for i, record in enumerate(records, start=2):  # Start from row 2
            if record.get("tg_id") == tg_id:
                ws.update_cell(i, 3, "worker")  # Assuming role is column 3
                break
    
    _retry_api_call(_approve)

def inc_balance(tg_id: int, delta: float) -> None:
    """Increase worker balance"""
    def _inc():
        ws = workers_ws()
        records = ws.get_all_records()
        for i, record in enumerate(records, start=2):
            if record.get("tg_id") == tg_id:
                current_balance = float(record.get("balance", 0))
                new_balance = round(current_balance + delta, 2)
                ws.update_cell(i, 5, new_balance)  # Assuming balance is column 5
                break
    
    _retry_api_call(_inc)

def inc_clients_count(tg_id: int) -> None:
    """Increase worker clients count"""
    def _inc():
        ws = workers_ws()
        records = ws.get_all_records()
        for i, record in enumerate(records, start=2):
            if record.get("tg_id") == tg_id:
                current_count = int(record.get("clients_count", 0))
                new_count = current_count + 1
                ws.update_cell(i, 4, new_count)  # Assuming clients_count is column 4
                break
    
    _retry_api_call(_inc)

def append_client_row(data: Dict[str, Any]) -> None:
    """Append new client row to Clients worksheet"""
    def _append():
        ws = clients_ws()
        row = [
            data.get("worker_tg_id"),
            data.get("worker_username"),
            data.get("phone"),
            data.get("name"),
            data.get("messenger"),
            data.get("order_link"),
            data.get("amount"),
            data.get("status"),
            data.get("receipt_url", ""),
            data.get("timestamp")
        ]
        ws.append_row(row)
    
    _retry_api_call(_append)

def create_withdrawal(tg_id: int, amount: float) -> int:
    """Create withdrawal request and return ID"""
    def _create():
        ws = withdrawals_ws()
        # Get next ID
        records = ws.get_all_records()
        next_id = 1
        if records:
            max_id = max(int(record.get("id", 0)) for record in records)
            next_id = max_id + 1
        
        ws.append_row([next_id, tg_id, amount, "PENDING", ""])
        return next_id
    
    return _retry_api_call(_create)

def update_withdrawal(withdrawal_id: int, status: str) -> None:
    """Update withdrawal status"""
    def _update():
        ws = withdrawals_ws()
        records = ws.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record.get("id", 0)) == withdrawal_id:
                ws.update_cell(i, 4, status)  # Assuming status is column 4
                break
    
    _retry_api_call(_update) 