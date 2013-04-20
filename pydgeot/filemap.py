import os
import sqlite3


def re_fn(expr, item):
    """
    REGEXP function for SQLite. Return true if a match is found.
    """
    import re
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None


class FileMap:
    """
    Stores file information for generated content in a persistent SQLite database. When content is being generated, this
    information is used to determine what files are new, updated, or deleted. It also stores what files are built from
    a source file, as well as what other source files it may depend on.

    All methods expect absolute paths, in either the Apps content or build directories.
    """
    def __init__(self, app, path):
        """
        Establish an SQLite database connection, and create tables if necessary.

        Args:
            app: Parent App instance.
            path: SQLite database path.
        """
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
        """
        Commit database changes.
        """
        self.connection.commit()

    def reset(self):
        """
        Delete all entries.
        """
        self.cursor.execute("DELETE FROM source_dependencies")
        self.cursor.execute("DELETE FROM source_targets")
        self.cursor.execute("DELETE FROM sources")
        self.cursor.execute("delete from sqlite_sequence where name='source_dependencies'")
        self.cursor.execute("delete from sqlite_sequence where name='source_targets'")
        self.cursor.execute("delete from sqlite_sequence where name='sources'")
        self.commit()

    def clean(self, paths):
        """
        Delete entries under the given source directories and their subdirectories.

        Args:
            paths: List of content directory paths to delete entries for.
        """
        for path in paths:
            regex = self._regex(path, subdirs=True)
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
        """
        Get a list of source paths.

        Args:
            prefix: Source directory to get files in. Not recursive.
            mtimes: Return modified times for files as well.

        Returns:
            A list of source file paths. If mtimes is True, a list of tuples containing the source file path and its
            modified time, will be returned.
        """
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
        """
        Remove a source entry, and any associated source dependencies and target files.

        Args:
            source: Source file path to remove.
        """
        rel = self._relative_path(source)
        self.cursor.execute("SELECT id FROM sources WHERE path = ?", (rel, ))
        result = self.cursor.fetchone()
        if result is not None:
            sid = result[0]
            self.cursor.execute("DELETE FROM source_targets WHERE source_id = ?", (sid, ))
            self.cursor.execute("DELETE FROM source_dependencies WHERE source_id = ? OR dependency_id = ?", (sid, sid))
            self.cursor.execute("DELETE FROM sources WHERE id = ?", (sid, ))

    def get_targets(self, source, reverse=False):
        """
        Get a list of target paths that a source path has generated.

        Args:
            source: Source path to get targets path for.
            reverse: Perform a reverse lookup instead. Returning source paths for a given target path. The source
                     argument should be given a target path.

        Returns:
            A list of target paths (or source paths, if reverse is True.)
        """
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
        """
        Set target paths for a source path.

        Args:
            source: Source path to set target paths for.
            values: List of target paths.
        """
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
        sid = self._add_source(source)
        self.cursor.executemany("""
            INSERT INTO source_targets
                (source_id, path)
                VALUES (?, ?)
            """, ([(sid, self._relative_path(value)) for value in values]))

    def get_dependencies(self, source, reverse=False, recursive=False):
        """
        Get a list of source paths that a source path depends on to generate.

        If 'fileA.html' and 'fileB.html' are both templates that depend on 'base.html', then:
         get_dependencies('fileA.html') => ['base.html']
         get_dependencies('base.html') => []
         get_dependencies('base.html', reverse=True) => ['fileA.html', 'fileB.html']

        Args:
            source: Source path to get dependency paths for.
            reverse: Perform a reverse lookup instead. Return source paths that depend on the given source path to
                     generate.
            recursive: Include dependencies of dependencies. It's turtles all the way down.

        Returns:
            A list of source paths.
        """
        if recursive:
            return self._get_dependencies_recursive(source, reverse)
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

    def _get_dependencies_recursive(self, path, reverse, _parent_deps=set()):
        """
        Get a list of all dependencies for a file, cascading in dependencies of dependencies.

        Args:
            source: Source path to get dependency paths for.
            reverse: Perform a reverse lookup instead. Return source paths that depend on the given source path to
                     generate.
            _parent_deps: Set used to track files that have already been looked at. Prevents infinite loops.

        Returns:
            A list of source paths.
        """
        dependencies = set(self.get_dependencies(path, reverse=reverse))
        for dependency in list(dependencies):
            if dependency not in _parent_deps:
                dependencies |= self._get_dependencies_recursive(dependency, reverse, _parent_deps=dependencies)
        return dependencies

    def set_dependencies(self, source, values):
        """
        Set source dependencies for a source path.

        Args:
            source: Source path to set dependency paths for.
            values: List of source dependency paths.
        """
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
        sid = self._add_source(source)
        value_ids = [self._add_source(value) for value in values]
        self.cursor.executemany("""
            INSERT INTO source_dependencies
                (source_id, dependency_id)
                VALUES (?, ?)
            """, [(sid, value_id) for value_id in value_ids])

    def _add_source(self, source):
        """
        Add a source entry to the database. Updates file information if the entry already exists.

        Args:
            source: Source path to add.

        Returns:
            The entries database id.
        """
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
        """
        Get a source path given a relative path.

        Args:
            relative: Relative path.

        Returns:
            A source path.
        """
        return os.path.join(self.app.source_root, relative)

    def _target_path(self, relative):
        """
        Get a target path given a relative path.

        Args:
            relative: Relative path.

        Returns:
            A target path.
        """
        return os.path.join(self.app.build_root, relative)

    def _relative_path(self, path):
        """
        Get a relative path from a source or target path.

        Args:
            path: Source or target path.

        Returns:
            A relative path.
        """
        if path.startswith(self.app.source_root):
            path = os.path.relpath(path, self.app.source_root)
        elif path.startswith(self.app.build_root):
            path = os.path.relpath(path, self.app.build_root)
        path = '' if path == '.' else path
        return path

    def _regex(self, path, subdirs=False):
        """
        Get a regex for the given directory path. Used for retrieving file paths in or under the given directory.

        Args:
            path: Directory path.
            subdirs: Retrieve files in all subdirectories.

        Returns:
            A regex string.
        """
        rel = self._relative_path(path)
        if subdirs:
            match = '.*'
        else:
            match = '[^{0}]*'.format(os.sep)
        if rel == '':
            regex = '^({0})$'.format(match)
        else:
            regex = '^{0}{1}({2})$'.format(rel, os.sep, match)
        return regex.replace('\\', '\\\\')
