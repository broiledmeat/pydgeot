class Contexts:
    def __init__(self, app):
        self.app = app
        self.cursor = self.app.db_cursor

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_vars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value TEXT,
                source_id INTEGER NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE)
            ''')
        # Use 'name' here rather than id in case the var isn't set yet.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_var_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dependency_id INTEGER NOT NULL,
                FOREIGN KEY(dependency_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE)
            ''')

    def clean(self, paths):
        """
        Delete entries under the given source directories and their subdirectories.

        Args:
            paths: List of content directory paths to delete entries for.
        """
        for path in paths:
            regex = self.app.path_regex(path, subdirs=True)
            self.cursor.execute('SELECT id FROM sources WHERE path REGEXP ?', (regex, ))
            ids = [result[0] for result in self.cursor.fetchall()]
            if len(ids) > 0:
                id_query = '(' + ','.join('?' * len(ids)) + ')'
                self.cursor.execute('''
                    DELETE
                    FROM context_var_dependencies
                    WHERE
                        dependency_id IN {0}
                    '''.format(id_query), (ids + ids))
                self.cursor.execute('DELETE FROM context_vars WHERE source_id IN {0}'.format(id_query), ids)

    def get_first(self, name, source=None):
        """
        Get the first context var with a given name and optional source path.

        Args:
            name: Name of the context var to retrieve.
            source: Source path that set the context var.
        Returns:
            String value of the context var, or None if no context var could be found.
        """
        values = self.get(name, source)
        return values[0] if len(values) > 0 else None

    def get(self, name, source=None):
        """
        Get all context vars with a given name and optional source path.

        Args:
            name: Name of the context vars to retrieve.
            source: Source path that set the context vars.
        Returns:
            A list of string values of the context vars, or an empty list if no context vars could be found.
        """
        results = []
        if source is None and name is not None:
            results = self.cursor.execute('SELECT c.value FROM context_vars AS c WHERE c.name = ?', (name, ))
        elif source is not None:
            rel = self.app.relative_path(source)
            results = self.cursor.execute('''
                SELECT c.value
                FROM context_vars AS c
                    INNER JOIN sources s ON s.id = c.source_id
                WHERE
                    c.name = ? AND
                    s.path = ?
                ''', (name, rel))
        return [result[0] for result in results]

    def set(self, source, name, value):
        """
        Set a context var for the source path. Removes any other context vars with the same name and source path.

        Args:
            name: Name of the context var to set.
            value: Value of the context var.
            source: Source path of the context var.
        """
        self.remove(source, name)
        self.add(source, name, value)

    def add(self, source, name, value):
        """
        Add a context var for the source path. Allows multiple context vars with the same name and source path.

        Args:
            name: Name of the context var to set.
            value: Value of the context var.
            source: Source path of the context var.
        """
        sid = self.app.sources.add(source)
        self.cursor.execute('''
            INSERT INTO context_vars
                (name, value, source_id)
                VALUES (?, ?, ?)
                ''', (name, value, sid))

    def remove(self, source=None, name=None):
        """
        Remove context vars with a given name and/or source path. The name and source arguments are both optional, but
        at least one must be given.

        Args:
            name: Name of the context var to remove.
            source: Source path of the context var to remove.
        """
        if source is not None:
            rel = self.app.relative_path(source)
            self.cursor.execute('SELECT id FROM sources WHERE path = ?', (rel, ))
            result = self.cursor.fetchone()
            if result is not None:
                sid = result[0]
                if name is None:
                    self.cursor.execute('DELETE FROM context_vars WHERE source_id = ?', (sid, ))
                else:
                    self.cursor.execute('DELETE FROM context_vars WHERE name = ? AND source_id = ?', (name, sid))
        elif name is not None:
            self.cursor.execute('DELETE FROM context_vars WHERE name = ?', (name, ))

    def get_dependencies(self, source, reverse=False, sources=False, recursive=False):
        rel = self.app.relative_path(source)
        if sources:
            if recursive:
                return self._get_dependencies_recursive(source, reverse)
            if reverse:
                results = self.cursor.execute('''
                    SELECT ds.path
                    FROM context_vars AS dc
                        INNER JOIN sources ds ON ds.id = dc.source_id
                    WHERE
                        dc.name IN (
                            SELECT c.name
                                FROM context_vars AS c
                                    INNER JOIN sources s ON s.id = c.source_id
                                WHERE
                                    s.path = ?)
                    ''', (rel, ))
            else:
                results = self.cursor.execute('''
                    SELECT ds.path
                    FROM context_vars AS dc
                        INNER JOIN sources ds ON ds.id = dc.source_id
                    WHERE
                        dc.name IN (
                            SELECT c.name
                            FROM context_var_dependencies AS c
                                INNER JOIN sources s ON s.id = c.source_id
                            WHERE
                                s.path = ?)
                    ''', (rel, ))
            return [self.app.source_path(result[0]) for result in results]
        else:
            if reverse:
                results = self.cursor.execute('''
                    SELECT c.name
                    FROM context_vars AS c
                        INNER JOIN sources s ON s.id = c.source_id
                    WHERE
                        s.path = ?
                    ''', (rel, ))
                return [(result[0], result[1]) for result in results]
            else:
                results = self.cursor.execute('''
                    SELECT cd.name
                    FROM context_var_dependencies AS cd
                        INNER JOIN sources s ON s.id = cd.dependency_id
                    WHERE
                        s.path = ?
                    ''', (rel, ))
            return [result[0] for result in results]

    def _get_dependencies_recursive(self, source, reverse, _parent_deps=None):
        if _parent_deps is None:
            _parent_deps = set()
        dependencies = set(self.get_dependencies(source, reverse=reverse, sources=True))
        for dependency in list(dependencies):
            if dependency not in _parent_deps:
                dependencies |= self._get_dependencies_recursive(dependency, reverse, _parent_deps=dependencies)
        return dependencies

    def set_dependencies(self, source, values):
        """
        Set context var dependencies for a source path.

        Args:
            source: Source path to set dependencies for.
            values: List of context var names the source path depends on.
        """
        sid = self.app.sources.add(source)
        self.cursor.execute('DELETE FROM context_var_dependencies WHERE dependency_id = ?', (sid, ))
        self.cursor.executemany('''
            INSERT INTO context_var_dependencies
                (name, dependency_id)
                VALUES (?, ?)
            ''', [(value, sid) for value in values])
