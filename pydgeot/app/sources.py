import os
import datetime
from collections import namedtuple


SourceResult = namedtuple('SourceResult', ['path', 'size', 'modified'])
"""Named Tuple containing a sources path, size, and modified time."""


class Sources:
    """
    File relationship manager for App instances. Source files must be registered, as well as what files they generate
    and what files they depend on to do so.
    """
    def __init__(self, app):
        """
        Initialize a new Source instance for the given App.

        :param app: App to manage source pathsfor.
        :type app: pydgeot.app.App
        """
        self.app = app
        self.cursor = self.app.db_cursor

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified INTEGER NOT NULL,
                UNIQUE(path))
            ''')

        # File map tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE)
            ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                dependency_id INTEGER NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                FOREIGN KEY(dependency_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE)
            ''')

    def _source_result(self, *row):
        """
        Get a SourceResult from a path, size, modified query from the sources table, with the path transformed in to a
        source path.

        :param row: Tuple or Sqlite Row object with at least three elements representing path, size, and modified time,
                    in that order.
        :type row: tuple[str, int, int] | sqlite3.Row
        :return: SourceResult with the path as a source path.
        :rtype: pydgeot.app.sources.SourceResult
        """
        return SourceResult(self.app.source_path(row[0]), row[1], datetime.datetime.fromtimestamp(row[2]))

    def _target_result(self, *row):
        """
        Get a SourceResult from a path query from the sources table, with the path transformed in to a target path.

        :param row: Tuple or Sqlite Row object with at least one element representing path as the first element.
        :type row: tuple[str] | sqlite3.Row
        :return: SourceResult with the path as a target path.
        :rtype: pydgeot.app.sources.SourceResult
        """
        return SourceResult(self.app.target_path(row[0]), None, None)

    def clean(self, paths):
        """
        Delete entries under the given source directories and their subdirectories.

        :param paths: List of content directory paths to delete entries for.
        :type paths: list[str]
        """
        for path in paths:
            regex = self.app.path_regex(path, recursive=True)
            self.cursor.execute('SELECT id FROM sources WHERE path REGEXP ?', (regex, ))
            ids = [result[0] for result in self.cursor.fetchall()]
            if len(ids) > 0:
                id_query = '(' + ','.join('?' * len(ids)) + ')'
                self.cursor.execute('''
                    DELETE FROM source_dependencies
                    WHERE
                        source_id IN {0} OR
                        dependency_id IN {0}
                    '''.format(id_query), (ids + ids))
                self.cursor.execute('DELETE FROM source_targets WHERE source_id IN {0}'.format(id_query), ids)
                self.cursor.execute('DELETE FROM sources WHERE id IN {0}'.format(id_query), ids)

    def add_source(self, source):
        """
        Add a source entry to the database. Updates file information if the entry already exists.

        :param source: Source path to add.
        :type source: str
        :return: Entries database id.
        :rtype: int
        """
        rel = self.app.relative_path(source)
        try:
            stats = os.stat(source)
            size = stats.st_size
            mtime = stats.st_mtime
        except FileNotFoundError:
            size = 0
            mtime = 0

        self.cursor.execute('SELECT id, size, modified FROM sources WHERE path = ?', (rel, ))
        result = self.cursor.fetchone()
        if result is not None:
            if size != result[1] or mtime != result[2]:
                self.cursor.execute('UPDATE sources SET size = ?, modified = ? WHERE id = ?', (size, mtime, result[0]))
            return result[0]

        self.cursor.execute('''
            INSERT INTO sources
                (path, size, modified)
                VALUES (?, ?, ?)
                ''', (rel, size, mtime))

        return self.cursor.lastrowid

    def get_source(self, source):
        """
        Get a SourceResult for the given path.

        :param source: Source file path.
        :type source: str
        :return: SourceResult for the given path, or None if the path does not exist.
        :rtype: pydgeot.app.sources.SourceResult | None
        """
        rel = self.app.relative_path(source)
        results = list(self.cursor.execute('SELECT path, size, modified FROM sources WHERE path = ?', (rel, )))
        return self._source_result(*results[0]) if len(results) > 0 else None

    def get_sources(self, source_dir='', recursive=True):
        """
        Get a list SourceResults for sources in the given directory.

        :param source_dir: Source directory to get files for.
        :type source_dir: str
        :param recursive: Return results in subdirectories of source_dir.
        :type recursive: bool
        :return: Set of SourceResults.
        :rtype: set[pydgeot.app.sources.SourceResult]
        """
        regex = self.app.path_regex(source_dir, recursive)
        results = self.cursor.execute('SELECT path, size, modified FROM sources WHERE path REGEXP ?', (regex, ))
        return set([self._source_result(*result) for result in results])

    def remove_source(self, source):
        """
        Remove a source entry, and any associated source dependencies and target files.

        :param source: Source file path to remove.
        :type source: str
        """
        rel = self.app.relative_path(source)
        self.cursor.execute('SELECT id FROM sources WHERE path = ?', (rel, ))
        result = self.cursor.fetchone()
        if result is not None:
            sid = result[0]
            self.cursor.execute('DELETE FROM source_targets WHERE source_id = ?', (sid, ))
            self.cursor.execute('DELETE FROM source_dependencies WHERE source_id = ? OR dependency_id = ?', (sid, sid))
            self.cursor.execute('DELETE FROM sources WHERE id = ?', (sid, ))

    def get_targets(self, source, reverse=False):
        """
        Get a list of target paths that a source path has generated.

        :param source: Source path to get targets path for.
        :type source: str
        :param reverse: Perform a reverse lookup instead. Returning source paths for a given target path. The source
                        argument should be given a target path.
        :type reverse: bool
        :return: Set of SourceResults for target paths (where size and modified time will be None.) If reverse is True,
                 a set of SourceResults for source paths.
        :rtype: set[pydgeot.app.sources.SourceResult]
        """
        rel = self.app.relative_path(source)
        if reverse:
            results = self.cursor.execute('''
                SELECT s.path, s.size, s.modified
                FROM source_targets AS st
                    INNER JOIN sources s ON s.id = st.source_id
                WHERE st.path = ?
                ''', (rel, ))
            return set([self._source_result(*result) for result in results])
        else:
            results = self.cursor.execute('''
                SELECT st.path
                FROM source_targets AS st
                    INNER JOIN sources s ON s.id = st.source_id
                WHERE s.path = ?
                ''', (rel, ))
            return set([self._target_result(*result) for result in results])

    def set_targets(self, source, values):
        """
        Set target paths for a source path.

        :param source: Source path to set target paths for.
        :type source: str
        :param values: List of target paths.
        :type values: list[str]
        """
        rel = self.app.relative_path(source)
        self.cursor.execute('''
            DELETE
            FROM source_targets
            WHERE id IN (
                SELECT st.id
                FROM source_targets st
                    INNER JOIN sources s ON s.id = st.source_id
                WHERE s.path = ?)
            ''', (rel, ))
        sid = self.add_source(source)
        self.cursor.executemany('''
            INSERT INTO source_targets
                (source_id, path)
                VALUES (?, ?)
            ''', ([(sid, self.app.relative_path(value)) for value in values]))

    def get_dependencies(self, source, reverse=False, recursive=False):
        """
        Get a list of source paths that a source path depends on to generate.

        If 'fileA.html' and 'fileB.html' are both templates that depend on 'base.html', then:
         get_dependencies('fileA.html') => ['base.html']
         get_dependencies('base.html') => []
         get_dependencies('base.html', reverse=True) => ['fileA.html', 'fileB.html']

        :param source: Source path to get dependency paths for.
        :type source: str
        :param reverse: Perform a reverse lookup instead. Return source paths that depend on the given source path to
                        generate.
        :type reverse: bool
        :param recursive: Include dependencies of dependencies. It's turtles all the way down.
        :type recursive: bool
        :return: Set of SourceResults.
        :rtype: set[pydgeot.app.sources.SourceResult]
        """
        if recursive:
            return self._get_dependencies_recursive(source, reverse)
        rel = self.app.relative_path(source)
        if reverse:
            results = self.cursor.execute('''
                SELECT s.path, s.size, s.modified
                FROM source_dependencies AS sd
                    INNER JOIN sources s ON s.id = sd.source_id
                    INNER JOIN sources d ON d.id = sd.dependency_id
                WHERE d.path = ?
                ''', (rel, ))
        else:
            results = self.cursor.execute('''
                SELECT d.path, d.size, d.modified
                FROM source_dependencies AS sd
                    INNER JOIN sources s ON s.id = sd.source_id
                    INNER JOIN sources d ON d.id = sd.dependency_id
                WHERE s.path = ?
                ''', (rel, ))
        return set([self._source_result(*result) for result in results])

    def _get_dependencies_recursive(self, source, reverse, _parent_deps=set()):
        """
        Get a list of all dependencies for a file, cascading in dependencies of dependencies.

        :param source: Source path to get dependency paths for.
        :type source: str
        :param reverse: Perform a reverse lookup instead. Return source paths that depend on the given source path to
                        generate.
        :type reverse: bool
        :return: Set of SourceResults.
        :rtype: set[pydgeot.app.sources.SourceResult]
        """
        dependencies = self.get_dependencies(source, reverse=reverse)
        for dependency in list(dependencies):
            if dependency not in _parent_deps:
                dependencies |= self._get_dependencies_recursive(dependency.path, reverse, _parent_deps=dependencies)
        return dependencies

    def set_dependencies(self, source, values):
        """
        Set source dependencies for a source path.

        :param source: Source path to set dependency paths for.
        :type source: str
        :param values: List of source dependency paths.
        :type values: list[str]
        """
        sid = self.add_source(source)
        self.cursor.execute('DELETE FROM source_dependencies WHERE source_id = ?', (sid, ))
        value_ids = [self.add_source(value) for value in values]
        self.cursor.executemany('''
            INSERT INTO source_dependencies
                (source_id, dependency_id)
                VALUES (?, ?)
            ''', [(sid, value_id) for value_id in value_ids])
