from collections import namedtuple


ContextResult = namedtuple('ContextResult', ['name', 'value', 'source'])
"""Named Tuple containing a context vars name, value, and source path."""


class Contexts:
    """
    Context variable manager for App instances. Context variables are arbitrary data that can be set or retrieved in
    Processor instances.
    """
    def __init__(self, app):
        """
        Initialize a new Contexts instance for the given App.

        :param app: App to manage context variables for.
        :type app: pydgeot.app.App
        """
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
                value TEXT,
                value_globbed INTEGER DEFAULT 0,
                source_id INTEGER,
                dependency_id INTEGER NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                FOREIGN KEY(dependency_id) REFERENCES sources(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE)
            ''')

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
                    DELETE
                    FROM context_var_dependencies
                    WHERE
                        dependency_id IN {0}
                    '''.format(id_query), ids)
                self.cursor.execute('DELETE FROM context_vars WHERE source_id IN {0}'.format(id_query), ids)

    def get_context(self, name, value=None, source=None):
        """
        Get the first context var with a given name and optional source path.

        :param name: Name of the context var to retrieve.
        :type name: str
        :param value: Value of the context vars to retrieve.
        :type value: object | None
        :param source: Source path that set the context vars.
        :type source: str | None
        :return: ContextResult for the context var, or None if no context var could be found.
        :rtype: pydgeot.app.contexts.ContextResult | None
        """
        values = self.get_contexts(name, value, source)
        return list(values)[0] if len(values) > 0 else None

    def get_contexts(self, name=None, value=None, source=None):
        """
        Get all context vars that match name, value, and source parameters. Arguments that are None will not be used in
        the search, but at least one must be specified.

        :param name: Name of the context vars to retrieve.
        :type name: str | None
        :param value: Value of the context vars to retrieve.
        :type value: object | None
        :param source: Source path of context vars to retrieve.
        :type source: str | None
        :return: Set of ContextResults for found context vars.
        :rtype: set[pydgeot.app.contexts.ContextResult]
        """
        from pydgeot.filesystem import Glob

        if name is None and value is None and source is None:
            return set()
        query = '''
                SELECT c.name, c.value, s.path
                FROM context_vars AS c
                    INNER JOIN sources s ON s.id = c.source_id
                WHERE
                    1=1
            '''
        query_vars = []
        if name is not None:
            query += ' AND c.name = ?'
            query_vars.append(name)
        if value is not None:
            glob = Glob(str(value))
            if glob.is_glob:
                query += ' AND c.value REGEXP ?'
                query_vars.append(glob.regex)
            else:
                query += ' AND c.value = ?'
                query_vars.append(glob.value)
        if source is not None:
            rel = self.app.relative_path(source)
            query += ' AND s.path = ?'
            query_vars.append(rel)
        results = self.cursor.execute(query, query_vars)
        return set([ContextResult(result[0], result[1], self.app.source_path(result[2])) for result in results])

    def set_context(self, source, name, value):
        """
        Set a context var for the source path. Removes any other context vars with the same name and source path.

        :param name: Name of the context var to set.
        :type name: str
        :param value: Value of the context var.
        :type value: object
        :param source: Source path of the context var.
        :type source: str
        """
        self.remove_context(source, name)
        self.add_context(source, name, value)

    def add_context(self, source, name, value):
        """
        Add a context var for the source path. Allows multiple context vars with the same name and source path.

        :param name: Name of the context var to set.
        :type name: str
        :param value: Value of the context var.
        :type value: object
        :param source: Source path of the context var.
        :type source: str
        """
        sid = self.app.sources.add_source(source)
        self.cursor.execute('''
            INSERT INTO context_vars
                (name, value, source_id)
                VALUES (?, ?, ?)
                ''', (name, value, sid))

    def remove_context(self, source=None, name=None):
        """
        Remove context vars with a given name and/or source path. The name and source arguments are both optional, but
        at least one must be given.

        :param source: Source path of the context var to remove.
        :type source: str | None
        :param name: Name of the context var to remove.
        :type name: str | None
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

    def get_dependencies(self, dependency, reverse=False, recursive=False):
        """
        Get all context var dependencies a source path depends on.

        :param dependency: Source path to get dependencies for.
        :type dependency: str
        :param reverse: Get context vars that depend on the dependency source path.
        :type reverse: bool
        :param recursive: Return the entire dependency tree.
        :type recursive: bool
        :return: Set of ContextResults.
        :rtype: set[pydgeot.app.contexts.ContextResult]
        """
        if recursive:
            return self._get_dependencies_recursive(dependency, reverse)
        rel = self.app.relative_path(dependency)
        if reverse:
            # Get all the context vars source sets
            results = self.cursor.execute('''
                SELECT c.name, c.value
                FROM context_vars AS c
                    INNER JOIN sources s ON s.id = c.source_id
                WHERE
                    s.path = ?
                ''', (rel, ))

            query = '''
                SELECT c.name, c.value, d.path
                FROM context_var_dependencies AS c
                    LEFT JOIN sources s ON s.id = c.source_id
                    INNER JOIN sources d ON d.id = c.dependency_id
                WHERE
                    0 = 1'''
            query_vars = []
            for name, value in list(results):
                if name is None and value is None:
                    continue
                subqueries = []
                if name is not None:
                    subqueries.append('c.name = ?')
                    query_vars.append(name)
                if value is not None:
                    subqueries.append('''
                        ((c.value IS NULL) OR
                         (c.value_globbed = 1 AND ? REGEXP c.value) OR
                         (c.value_globbed <> 1 AND ? = c.value))''')
                    query_vars.append(value)
                    query_vars.append(value)
                subqueries.append('(c.source_id IS NULL OR s.path = ?)')
                query_vars.append(rel)
                query += ' OR ({0})'.format(' AND '.join(subqueries))
                results = self.cursor.execute(query, query_vars)
        else:
            results = self.cursor.execute('''
                SELECT c.name, c.value, c.value_globbed, s.path
                FROM context_var_dependencies AS c
                    LEFT JOIN sources s ON s.id = c.source_id
                    INNER JOIN sources d ON d.id = c.dependency_id
                WHERE
                    d.path = ?
                ''', (rel, ))
            query = '''
                SELECT c.name, c.value, s.path
                FROM context_vars AS c
                    INNER JOIN sources s ON s.id = c.source_id
                WHERE
                    0 = 1'''
            query_vars = []
            for name, value, globbed, path in list(results):
                if name is None and value is None and path is None:
                    continue
                subqueries = []
                if name is not None:
                    subqueries.append('c.name = ?')
                    query_vars.append(name)
                if value is not None:
                    if globbed == 1:
                        subqueries.append('c.value REGEXP ?')
                    else:
                        subqueries.append('c.value = ?')
                    query_vars.append(value)
                if path is not None:
                    subqueries.append('s.path = ?')
                    query_vars.append(path)
                query += ' OR ({0})'.format(' AND '.join(subqueries))
            results = self.cursor.execute(query, query_vars)

        return set([ContextResult(result[0], result[1], self.app.source_path(result[2])) for result in results])

    def _get_dependencies_recursive(self, dependency, reverse, _parent_deps=None):
        """
        Get all context var dependencies a source path depends on, including all subdependencies.

        :param dependency: Source path to get dependencies for.
        :type dependency: str
        :param reverse: Get context vars that depend on the dependency source path.
        :type reverse: bool
        :return: Set of ContextResults.
        :rtype: set[pydgeot.app.contexts.ContextResult]
        """
        if _parent_deps is None:
            _parent_deps = set()
        dependencies = self.get_dependencies(dependency, reverse=reverse)
        for dependency_ in list(dependencies):
            if dependency_ not in _parent_deps:
                dependencies |= self._get_dependencies_recursive(dependency_.source, reverse, _parent_deps=dependencies)
        return dependencies

    def clear_dependencies(self, dependency):
        """
        Removes all dependencies for a source path.

        :param dependency: Source path to remove dependencies from.
        :type dependency: str
        """
        did = self.app.sources.add_source(dependency)
        self.cursor.execute('DELETE FROM context_var_dependencies WHERE dependency_id = ?', (did, ))

    def add_dependency(self, dependency, name, value=None, source=None):
        """
        Add a context var dependency for a source path.

        :param dependency: Source path to set dependencies for.
        :type dependency: str
        :param name: Name of the context var the source path depends on.
        :type name: str
        :param value: Value of the named context var.
        :type value: object | None
        :param source: Source path of the named context var.
        :type source: str | None
        """
        from pydgeot.filesystem import Glob

        did = self.app.sources.add_source(dependency)
        sid = self.app.sources.add_source(source) if source is not None else None
        is_glob = False
        if value is not None:
            glob = Glob(value)
            is_glob = glob.is_glob
            value = glob.regex if is_glob else glob.value
        self.cursor.execute('''
            INSERT INTO context_var_dependencies
                (name, value, value_globbed, source_id, dependency_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, value, is_glob, sid, did))
