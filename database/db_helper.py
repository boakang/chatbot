# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pyodbc
from typing import List, Dict, Optional
from config import DefaultConfig

class DatabaseHelper:
    def __init__(self):
        self.config = DefaultConfig()
        self.connection_string = self.config.SQL_CONNECTION_STRING
    
    def get_connection(self):
        """Tạo kết nối đến Azure SQL Database"""
        return pyodbc.connect(self.connection_string)
    
    # ========== ADMIN FUNCTIONS ==========
    def verify_admin_key(self, admin_key: str) -> bool:
        """Xác thực admin key"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM AdminKeys WHERE AdminKey = ? AND IsActive = 1",
                (admin_key,)
            )
            result = cursor.fetchone()[0]
            conn.close()
            return result > 0
        except Exception as e:
            print(f"Error verifying admin key: {e}")
            return False
    
    def get_pending_tickets(self) -> List[Dict]:
        """Lấy danh sách tickets đang chờ phê duyệt"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.TicketID, t.EmployeeID, e.EmployeeName, 
                       t.TicketContent, t.CreatedAt
                FROM Tickets t
                JOIN Employees e ON t.EmployeeID = e.EmployeeID
                WHERE t.Status = 'Pending'
                ORDER BY t.CreatedAt DESC
            """)
            
            tickets = []
            for row in cursor.fetchall():
                tickets.append({
                    'ticket_id': row[0],
                    'employee_id': row[1],
                    'employee_name': row[2],
                    'content': row[3],
                    'created_at': row[4].strftime('%d/%m/%Y %H:%M')
                })
            
            conn.close()
            return tickets
        except Exception as e:
            print(f"Error getting pending tickets: {e}")
            return []
    
    def approve_ticket(self, ticket_id: int, admin_key: str) -> bool:
        """Phê duyệt ticket"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Tickets 
                SET Status = 'Approved', 
                    ApprovedBy = ?, 
                    UpdatedAt = GETDATE()
                WHERE TicketID = ? AND Status = 'Pending'
            """, (admin_key, ticket_id))
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            return affected_rows > 0
        except Exception as e:
            print(f"Error approving ticket: {e}")
            return False
    
    def reject_ticket(self, ticket_id: int, admin_key: str) -> bool:
        """Từ chối ticket"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Tickets 
                SET Status = 'Rejected', 
                    ApprovedBy = ?, 
                    UpdatedAt = GETDATE()
                WHERE TicketID = ? AND Status = 'Pending'
            """, (admin_key, ticket_id))
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            return affected_rows > 0
        except Exception as e:
            print(f"Error rejecting ticket: {e}")
            return False
    
    # ========== USER FUNCTIONS ==========
    def verify_employee(self, employee_id: str) -> Optional[Dict]:
        """Xác thực mã nhân viên"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT EmployeeID, EmployeeName FROM Employees WHERE EmployeeID = ?",
                (employee_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'employee_id': row[0],
                    'employee_name': row[1]
                }
            return None
        except Exception as e:
            print(f"Error verifying employee: {e}")
            return None
    
    def create_ticket(self, employee_id: str, content: str) -> bool:
        """Tạo ticket mới"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Tickets (EmployeeID, TicketContent, Status)
                VALUES (?, ?, 'Pending')
            """, (employee_id, content))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating ticket: {e}")
            return False
    
    def get_user_tickets(self, employee_id: str) -> List[Dict]:
        """Lấy danh sách tickets của nhân viên"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TicketID, TicketContent, Status, CreatedAt, UpdatedAt
                FROM Tickets
                WHERE EmployeeID = ?
                ORDER BY CreatedAt DESC
            """, (employee_id,))
            
            tickets = []
            for row in cursor.fetchall():
                tickets.append({
                    'ticket_id': row[0],
                    'content': row[1],
                    'status': row[2],
                    'created_at': row[3].strftime('%d/%m/%Y %H:%M'),
                    'updated_at': row[4].strftime('%d/%m/%Y %H:%M')
                })
            
            conn.close()
            return tickets
        except Exception as e:
            print(f"Error getting user tickets: {e}")
            return []