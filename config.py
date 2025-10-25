#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
from dotenv import load_dotenv

load_dotenv()

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    APP_TYPE = os.environ.get("MicrosoftAppType", "MultiTenant")
    APP_TENANTID = os.environ.get("MicrosoftAppTenantId", "")
    
    # Azure SQL Database Configuration
    SQL_SERVER = os.environ.get("SQL_SERVER", "your-server.database.windows.net")
    SQL_DATABASE = os.environ.get("SQL_DATABASE", "your-database")
    SQL_USERNAME = os.environ.get("SQL_USERNAME", "your-username")
    SQL_PASSWORD = os.environ.get("SQL_PASSWORD", "your-password")
    
    @property
    def SQL_CONNECTION_STRING(self):
        return (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{self.SQL_SERVER},1433;"
            f"Database={self.SQL_DATABASE};"
            f"Uid={self.SQL_USERNAME};"
            f"Pwd={self.SQL_PASSWORD};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )