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

    # ─── SUMMARY ───────────────────────────────────────────────────────────────

    def get_summary_stats(self) -> Dict:
        """Lấy doanh số tổng quát"""
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
                'total_stores': row[2] if row[2] else 0,
            }
            conn.close()
            return stats
        except Exception as e:
            print(f"Error getting summary stats: {e}")
            return {}

    # ─── COUNTY / CITY / STORE DRILL-DOWN ──────────────────────────────────────

    def get_counties(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[str]:
        """Lấy danh sách tất cả county (có thể lọc theo ngày)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT county
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE county IS NOT NULL AND county != ''
            """
            params = []
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " ORDER BY county"
            cursor.execute(query, params)
            counties = [row[0] for row in cursor.fetchall()]
            conn.close()
            return counties
        except Exception as e:
            print(f"Error getting counties: {e}")
            return []

    def get_cities_by_county(self, county: str,
                             from_date: Optional[str] = None,
                             to_date: Optional[str] = None) -> List[str]:
        """Lấy danh sách thành phố trong một county"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT city
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE county = ? AND city IS NOT NULL AND city != ''
            """
            params = [county]
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " ORDER BY city"
            cursor.execute(query, params)
            cities = [row[0] for row in cursor.fetchall()]
            conn.close()
            return cities
        except Exception as e:
            print(f"Error getting cities: {e}")
            return []

    def get_stores_by_city(self, city: str, county: str,
                           from_date: Optional[str] = None,
                           to_date: Optional[str] = None) -> List[Dict]:
        """Lấy danh sách cửa hàng trong một city"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT store_id, store_name
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE city = ? AND county = ?
                  AND store_id IS NOT NULL AND store_name IS NOT NULL
            """
            params = [city, county]
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " ORDER BY store_name"
            cursor.execute(query, params)
            stores = [{'store_id': row[0], 'store_name': row[1]} for row in cursor.fetchall()]
            conn.close()
            return stores
        except Exception as e:
            print(f"Error getting stores: {e}")
            return []

    def get_revenue_by_store(self, store_id: str,
                             from_date: Optional[str] = None,
                             to_date: Optional[str] = None) -> Dict:
        """Tổng doanh thu của một cửa hàng"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT store_name,
                       SUM(sale_dollars) as TotalRevenue,
                       SUM(bottles_sold) as TotalBottles
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE store_id = ?
            """
            params = [store_id]
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " GROUP BY store_name"
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'store_name': row[0],
                    'total_revenue': row[1] if row[1] else 0,
                    'total_bottles': row[2] if row[2] else 0,
                }
            return {}
        except Exception as e:
            print(f"Error getting store revenue: {e}")
            return {}

    def get_revenue_by_county(self, county: str,
                              from_date: Optional[str] = None,
                              to_date: Optional[str] = None) -> Dict:
        """Tổng doanh thu của một county"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT SUM(sale_dollars) as TotalRevenue,
                       SUM(bottles_sold) as TotalBottles,
                       COUNT(DISTINCT store_id) as TotalStores
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE county = ?
            """
            params = [county]
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'total_revenue': row[0] if row[0] else 0,
                    'total_bottles': row[1] if row[1] else 0,
                    'total_stores': row[2] if row[2] else 0,
                }
            return {}
        except Exception as e:
            print(f"Error getting county revenue: {e}")
            return {}

    # ─── PRODUCT RANKINGS ──────────────────────────────────────────────────────

    def get_top_products(self, limit: int = 5,
                         from_date: Optional[str] = None,
                         to_date: Optional[str] = None) -> List[Dict]:
        """Top N sản phẩm bán nhiều nhất (theo bottles_sold)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = f"""
                SELECT TOP {limit} product_name,
                       SUM(bottles_sold) as TotalBottles,
                       SUM(sale_dollars) as TotalRevenue
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " GROUP BY product_name ORDER BY TotalBottles DESC"
            cursor.execute(query, params)
            products = []
            for row in cursor.fetchall():
                products.append({
                    'name': row[0],
                    'bottles': row[1] if row[1] else 0,
                    'revenue': row[2] if row[2] else 0,
                })
            conn.close()
            return products
        except Exception as e:
            print(f"Error getting top products: {e}")
            return []

    def get_bottom_products(self, limit: int = 5,
                            from_date: Optional[str] = None,
                            to_date: Optional[str] = None) -> List[Dict]:
        """Top N sản phẩm bán ít nhất (theo bottles_sold)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = f"""
                SELECT TOP {limit} product_name,
                       SUM(bottles_sold) as TotalBottles,
                       SUM(sale_dollars) as TotalRevenue
                FROM dbo.Iowa_Liquor_Sales2022
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " GROUP BY product_name ORDER BY TotalBottles ASC"
            cursor.execute(query, params)
            products = []
            for row in cursor.fetchall():
                products.append({
                    'name': row[0],
                    'bottles': row[1] if row[1] else 0,
                    'revenue': row[2] if row[2] else 0,
                })
            conn.close()
            return products
        except Exception as e:
            print(f"Error getting bottom products: {e}")
            return []
