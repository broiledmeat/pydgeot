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

    def reset(self):
        self.cursor.execute("DELETE FROM source_dependencies")
        self.cursor.execute("DELETE FROM source_targets")
        self.cursor.execute("DELETE FROM sources")
        self.cursor.execute("delete from sqlite_sequence where name='source_dependencies'")
        self.cursor.execute("delete from sqlite_sequence where name='source_targets'")
        self.cursor.execute("delete from sqlite_sequence where name='sources'")
        self.commit()

    def clean(self, paths):
        for path in paths:
            regex = self._regex(path)
            self.cursor.execute("SELECT id FROM sources WHERE path REGEXP ?", (regex, ))
            ids = [result[0] for result in self.cursor.fetchall()]
            if len(ids) > 0:
                id_query = '(' + ','.join('?' * len(ids)) + ')'
                self.cursor.execute("""
                    DELETE FROM source_dependencies
                    WHERE
                        source_id IN {0} OR
                        dependency_id IN {0}
                    """.format(id_query), (ids + ids))
                self.cursor.execute("DELETE FROM source_targets WHERE source_id IN {0}".format(id_query), ids)
                self.cursor.execute("DELETE FROM sources WHERE id IN {0}".format(id_query), ids)
        self.commit()

    def get_sources(self, prefix=None, mtimes=False):
        if prefix is None:
            results = self.cursor.execute('SELECT path, modified FROM sources')
        else:
            regex = self._regex(prefix)
            results = self.cursor.execute('SELECT path, modified FROM sources WHERE path REGEXP ?', (regex, ))
        if mtimes:
            return [(self._source_path(result[0]), result[1]) for result in results]
        else:
            return [self._source_path(result[0]) for result in results]

    def remove_source(self, source):
        rel = self._relative_path(source)
        self.cursor.execute("SELECT id FROM sources WHERE path = ?", (rel, ))
        result = self.cursor.fetchone()
        if result is not None:
            id = result[0]
            self.cursor.execute("DELETE FROM source_targets WHERE source_id = ?", (id, ))
            self.cursor.execute("DELETE FROM source_dependencies WHERE source_id = ? OR dependency_id = ?", (id, id))
            self.cursor.execute("DELETE FROM sources WHERE id = ?", (id, ))

    def get_targets(self, source, reverse=False):
        rel = self._relative_path(source)
        if reverse:
            results = self.cursor.execute("""
                SELECT s.path
                FROM source_targets AS st
                    INNER JOIN sources s ON s.id = st.source_id
                WHERE st.path = ?
                """, (rel, ))
            return [self._source_path(result[0]) for result in results]
        else:
            results = self.cursor.execute("""
                SELECT st.path
                FROM source_targets AS st
                    INNER JOIN sources s ON s.id = st.source_id
                WHERE s.path = ?
                """, (rel, ))
            return [self._target_path(result[0]) for result in results]

    def set_targets(self, source, values):
        rel = self._relative_path(source)
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
            """, ([(id, self._relative_path(value)) for value in values]))

    def get_dependencies(self, source, reverse=False):
        rel = self._relative_path(source)
        if reverse:
            results = self.cursor.execute("""
                SELECT s.path
                FROM source_dependencies AS sd
                    INNER JOIN sources s ON s.id = sd.source_id
                    INNER JOIN sources d ON d.id = sd.dependency_id
                WHERE d.path = ?
                """, (rel, ))
        else:
            results = self.cursor.execute("""
                SELECT d.path
                FROM source_dependencies AS sd
                    INNER JOIN sources s ON s.id = sd.source_id
                    INNER JOIN sources d ON d.id = sd.dependency_id
                WHERE s.path = ?
                """, (rel, ))
        return [self._source_path(result[0]) for result in results]

    def set_dependencies(self, source, values):
        rel = self._relative_path(source)
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

    def _add_source(self, source):
        rel = self._relative_path(source)
        try:
            stats = os.stat(source)
            size = stats.st_size
            mtime = stats.st_mtime
        except FileNotFoundError:
            size = 0
            mtime = 0

        self.cursor.execute("SELECT id, size, modified FROM sources WHERE path = ?", (rel, ))
        result = self.cursor.fetchone()
        if result is not None:
            if size != result[1] or mtime != result[2]:
                self.cursor.execute("UPDATE sources SET size = ?, modified = ? WHERE id = ?", (size, mtime, result[0]))
            return result[0]

        self.cursor.execute("""
            INSERT INTO sources
                (path, size, modified)
                VALUES (?, ?, ?)
                """, (rel, size, mtime))
        return self.cursor.lastrowid

    def _source_path(self, relative):
        return os.path.join(self.app.content_root, relative)

    def _target_path(self, relative):
        return os.path.join(self.app.build_root, relative)

    def _relative_path(self, path):
        if path.startswith(self.app.content_root):
            path = os.path.relpath(path, self.app.content_root)
        elif path.startswith(self.app.build_root):
            path = os.path.relpath(path, self.app.build_root)
        path = '' if path == '.' else path
        return path

    def _regex(self, path):
        rel = self._relative_path(path)
        if rel == '':
            regex = '^([^{0}]*)$'.format(os.sep)
        else:
            regex = '^{0}{1}([^{1}]*)$'.format(rel, os.sep)
        return regex.replace('\\', '\\\\')
