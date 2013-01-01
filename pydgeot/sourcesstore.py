import os
import sqlite3
from . import abspath

class FileMap:
    def __init__(self, core, path):
        self.core = core
        self.connection = sqlite3.connect(path)
        self.cursor = self.connection.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified INTEGER NOT NULL,
                UNIQUE(path)
            )""")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            )""")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                dependency_id INTEGER NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                FOREIGN KEY(dependency_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            )""")

    def commit(self):
        self.connection.commit()

    def sources(self):
        results = self.cursor.execute('SELECT path FROM sources')
        for result in results:
            yield self.source(result[0])

    def remove(self, source):
        rel = self.relative(source)
        self.cursor.execute("""
            DELETE
            FROM sources
            WHERE path = ?
            """, (rel, ))

    def targets(self, source, values=None):
        rel = self.relative(source)
        if values is not None:
            self.cursor.execute("""
                DELETE
                FROM source_targets
                WHERE id IN (
                    SELECT st.id
                    FROM source_targets st
                        INNER JOIN sources s ON s.id = st.source_id
                    WHERE s.path = ?)
                """, (rel, ))
            id = self._add_source(source)
            self.cursor.executemany("""
                INSERT INTO source_targets
                    (source_id, path)
                    VALUES (?, ?)
                """, ([(id, value) for value in values]))
        results = self.cursor.execute("""
            SELECT st.path
            FROM source_targets AS st
                INNER JOIN sources s ON s.id = st.source_id
            WHERE s.path = ?
            """, (rel, ))
        return [self.source(result[0]) for result in results]

    def dependencies(self, source, values=None):
        rel = self.relative(source)
        if values is not None:
            self.cursor.execute("""
                DELETE
                FROM source_dependencies
                WHERE id IN (
                    SELECT sd.id
                    FROM source_dependencies sd
                        INNER JOIN sources s ON s.id = sd.source_id
                        INNER JOIN sources d ON d.id = sd.dependency_id
                    WHERE s.path = ?)
                """, (rel, ))
            id = self._add_source(source)
            value_ids = [self._add_source(value) for value in values]
            self.cursor.executemany("""
                INSERT INTO source_dependencies
                    (source_id, dependency_id)
                    VALUES (?, ?)
                """, [(id, value_id) for value_id in value_ids])
        results = self.cursor.execute("""
            SELECT d.path
            FROM source_dependencies AS sd
                INNER JOIN sources s ON s.id = sd.source_id
                INNER JOIN sources d ON d.id = sd.dependency_id
            WHERE s.path = ?
            """, (rel, ))
        return [self.source(result[0]) for result in results]

    def _add_source(self, source):
        rel = self.relative(source)
        try:
            stats = os.stat(source)
            size = stats.st_size
            mtime = stats.st_mtime
        except FileNotFoundError:
            size = 0
            mtime = 0
        result = self.cursor.execute("""
            INSERT OR REPLACE INTO sources
                (path, size, modified)
                VALUES (?, ?, ?)
                """, (rel, size, mtime))
        return self.cursor.lastrowid

    def source(self, relative):
        return abspath(os.path.join(self.core.source_root, relative))

    def relative(self, source):
        return os.path.relpath(source, self.core.source_root)
