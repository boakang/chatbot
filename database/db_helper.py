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
    def get_summary_stats(self) -> Dict:
        """Lấy doanh số tổng quát (Admin)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(sale_dollars) as TotalRevenue,
                    SUM(bottles_sold) as TotalBottles,
                    COUNT(DISTINCT store_id) as TotalStores
                FROM dbo.Iowa_Liquor_Sales2022
            """)
            row = cursor.fetchone()
            stats = {
                'total_revenue': row[0] if row[0] else 0,
                'total_bottles': row[1] if row[1] else 0,
                'total_stores': row[2] if row[2] else 0
            }
            conn.close()
            return stats
        except Exception as e:
            print(f"Error getting summary stats: {e}")
            return {}

    def get_top_products(self, limit: int = 5) -> List[Dict]:
        """Lấy danh sách sản phẩm bán chạy nhất"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT TOP {limit} product_name, SUM(sale_dollars) as Revenue
                FROM dbo.Iowa_Liquor_Sales2022
                GROUP BY product_name
                ORDER BY Revenue DESC
            """)
            
            products = []
            for row in cursor.fetchall():
                products.append({
                    'name': row[0],
                    'revenue': row[1]
                })
            conn.close()
            return products
        except Exception as e:
            print(f"Error getting top products: {e}")
            return []

    # ========== USER FUNCTIONS ==========
    def get_sales_by_store(self, store_id: str) -> List[Dict]:
        """Tra cứu doanh số theo ID cửa hàng"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 10 date, store_name, product_name, sale_dollars, bottles_sold
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE store_id = ?
                ORDER BY date DESC
            """, (store_id,))
            
            sales = []
            for row in cursor.fetchall():
                sales.append({
                    'date': row[0].strftime('%d/%m/%Y') if row[0] else "N/A",
                    'store_name': row[1],
                    'product_name': row[2],
                    'revenue': row[3],
                    'bottles': row[4]
                })
            conn.close()
            return sales
        except Exception as e:
            print(f"Error getting store sales: {e}")
            return []

    def get_sales_by_city(self, city: str) -> List[Dict]:
        """Tra cứu doanh số theo tên thành phố"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 10 date, store_name, product_name, sale_dollars
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE city LIKE ?
                ORDER BY date DESC
            """, (f"%{city}%",))
            
            sales = []
            for row in cursor.fetchall():
                sales.append({
                    'date': row[0].strftime('%d/%m/%Y') if row[0] else "N/A",
                    'store_name': row[1],
                    'product_name': row[2],
                    'revenue': row[3]
                })
            conn.close()
            return sales
        except Exception as e:
            print(f"Error getting city sales: {e}")
            return []
