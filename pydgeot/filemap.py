import os
import sqlite3

def re_fn(expr, item):
    import re
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None

class FileMap:
    def __init__(self, app, path):
        self.app = app
        self.connection = sqlite3.connect(path)
        self.cursor = self.connection.cursor()

        self.connection.create_function('REGEXP', 2, re_fn)

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

    def wipe(self):
        self.cursor.execute("DELETE FROM source_dependencies")
        self.cursor.execute("DELETE FROM source_targets")
        self.cursor.execute("DELETE FROM sources")
        self.commit()

    def sources(self, prefix=None, mtimes=False):
        if prefix is None:
            results = self.cursor.execute('SELECT path, modified FROM sources')
        else:
            rel = self._relative(prefix)
            if rel == '':
                regex = '^([^{0}]*)$'.format(os.sep)
            else:
                regex = '^{0}{1}([^{1}]*)$'.format(rel, os.sep)
            regex = regex.replace('\\', '\\\\')
            results = self.cursor.execute('SELECT path, modified FROM sources WHERE path REGEXP ?', (regex, ))
        if mtimes:
            return [(self._source(result[0]), result[1]) for result in results]
        else:
            return [self._source(result[0]) for result in results]

    def remove(self, source):
        rel = self._relative(source)
        self.cursor.execute("""
            DELETE
            FROM sources
            WHERE path = ?
            """, (rel, ))

    def targets(self, source, values=None):
        rel = self._relative(source)
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
                """, ([(id, self._relative(value)) for value in values]))
        results = self.cursor.execute("""
            SELECT st.path
            FROM source_targets AS st
                INNER JOIN sources s ON s.id = st.source_id
            WHERE s.path = ?
            """, (rel, ))
        return [self._source(result[0]) for result in results]

    def dependencies(self, source, values=None):
        rel = self._relative(source)
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
        return [self._target(result[0]) for result in results]

    def _add_source(self, source):
        rel = self._relative(source)
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

    def _source(self, relative):
        return os.path.join(self.app.content_root, relative)

    def _target(self, relative):
        return os.path.join(self.app.build_root, relative)

    def _relative(self, path):
        if path.startswith(self.app.content_root):
            path = os.path.relpath(path, self.app.content_root)
        elif path.startswith(self.app.build_root):
            path = os.path.relpath(path, self.app.build_root)
        path = '' if path == '.' else path
        return path