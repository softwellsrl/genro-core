# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""GenroMicroApplication - Base class for micro applications."""

from typing import Any

from ..micro_db import GenroMicroDb


class GenroMicroApplication:
    """
    Base class for simple Genro micro applications.

    Provides database management and common application infrastructure.

    Usage:
        class MyApp(GenroMicroApplication):
            def __init__(self):
                super().__init__()
                # Add databases
                self.add_db('maindb', implementation='sqlite', path='.data/main.db')

                # Register tables
                maindb = self.db('maindb')
                maindb.add_table(BookTable)
                maindb.add_table(ShelfTable)

                # Run migrations
                maindb.migrate()
    """

    def __init__(self):
        """Initialize the micro application."""
        self._databases = {}

    def add_db(
        self,
        name: str,
        connection_string: str | None = None,
        implementation: str | None = None,
        path: str | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        **kwargs
    ) -> GenroMicroDb:
        """
        Add a database to the application.

        Args:
            name: Database identifier
            connection_string: Full connection string (e.g., "sqlite:///path/to/db.sqlite")
            implementation: Database type ("sqlite", "postgresql", etc.)
            path: Database file path (for SQLite)
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            **kwargs: Additional connection parameters

        Returns:
            GenroMicroDb instance

        Example:
            app.add_db('maindb', implementation='sqlite', path='.data/main.db')
            app.add_db('logdb', connection_string='sqlite:///.data/logs.db')
        """
        db = GenroMicroDb(
            name=name,
            connection_string=connection_string,
            implementation=implementation,
            path=path,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            **kwargs
        )
        self._databases[name] = db

        # Also set as attribute for convenience
        setattr(self, name, db)

        return db

    def db(self, name: str) -> GenroMicroDb:
        """
        Get a database by name.

        Args:
            name: Database identifier

        Returns:
            GenroMicroDb instance

        Raises:
            KeyError: If database not found
        """
        if name not in self._databases:
            raise KeyError(f"Database '{name}' not found. Available: {list(self._databases.keys())}")
        return self._databases[name]

    def close_all(self) -> None:
        """Close all database connections."""
        for db in self._databases.values():
            db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close all connections."""
        self.close_all()
