"""
Static Content Generator
Copies content from a source directory, rendering files with available handlers (HTML templates, CSS helpers, etc.)
"""
import os
import shutil
import argparse
import csv
import re
from .handlers import get_handler

class _ChangeSet(object):
    """
    Holds lists of file paths to copy and delete
    """
    def __init__(self):
        """
        Initialise an empty change set.

        Args:
            None
        """
        self.copy = set()
        self.delete = set()

    def merge(self, other):
        """
        Merges another change set in.

        Args:
            other (_ChangeSet): change set to merge from
        Returns:
            None
        """
        self.copy |= other.copy
        self.delete |= other.delete

class GenStatic(object):
    """
    Creates and updates a copy of directory contents, rendering files where handlers are available. Tracks file
    changes so only necessary copying and deletion is done.
    """
    DEFAULT_DEPENDENCY_MAP_FILENAME = '.pydgeot_genstatic_data'
    DEFAULT_FORCE_GENERATE = False

    ## These regexes apply to paths relative to the source root path
    # Ignore completely            
    DEFAULT_IGNORE_PATHS = []                       
    # Collect change lists and scan for template changes, but otherwise ignore
    DEFAULT_COLLECT_ONLY_PATHS = ['^\.templates(/.*)?$']

    def __init__(self,
                 source_root=None,
                 target_root=None,
                 dependency_map_filename=DEFAULT_DEPENDENCY_MAP_FILENAME,
                 ignore_paths=DEFAULT_IGNORE_PATHS,
                 force_generate=DEFAULT_FORCE_GENERATE):
        """
        Initialises GenStatic

        Args:
            source_root (str): Directory root to copy from.
            target_root (str): Directory root to copy to.
            dependency_map_filename (str): Filename to keep track of file dependencies in. Stored in target_root.
            ignore_paths (list(str)): List of regexes to match file paths against for ignoring completely.
            force_generate (bool): Don't throw an error if target_root exists and does not contain data_filename.
        Raises:
            IOError: If source_root is not a directory, or data_filename does not exist in target_root (unless
                     force_generate is set.)
        """
        self.source_root = os.path.abspath(os.path.expanduser(source_root))
        self.target_root = os.path.abspath(os.path.expanduser(target_root))
        self.dependency_map_filename = dependency_map_filename
        self.ignore_paths = [re.compile(path) for path in ignore_paths]
        self.force_generate = force_generate

        self.dependency_map_path = os.path.join(self.target_root, self.dependency_map_filename)
        dependency_map_exists = os.path.isfile(self.dependency_map_path)
        
        if not os.path.isdir(self.source_root):
            raise IOError('Missing source directory', self.source_root)

        if not self.force_generate and (os.path.isdir(self.target_root) and not dependency_map_exists):
            raise IOError('Missing dependency map file', self.dependency_map_path)

        self.dependencies = {}

    def generate(self):
        """
        Start copying/rendering

        Args:
            None
        Returns:
            None
        """
        self._load_dependencies()
        change_set = self._collect_changes()
        self._process_changes(change_set)
        self._save_dependencies()

    def _load_dependencies(self):
        """
        Loads the dependency map in.

        Args:
            None
        Returns:
            None
        """
        self.dependencies = {}
        if os.path.isfile(self.dependency_map_path):
            data_file = open(self.dependency_map_path)
            for parent, *children in csv.reader(data_file):
                self.dependencies[parent] = set(children)

    def _save_dependencies(self):
        """
        Writes the dependency map file out.

        Args:
            None
        Returns None
        """
        data_file = open(self.dependency_map_path, 'w')
        writer = csv.writer(data_file)
        for parent, items in self.dependencies.items():
            items = list(items)
            items.insert(0, parent)
            writer.writerow(items)

    def _collect_changes(self, relative_dir=''):
        """
        Collects file operations needed to sync the relative_path in source_root and target_root.

        Args:
            relative_path (str): Relative path (from source_root) to get changes against in target_root.
        Returns:
            _ChangeSet: Operations needed to sync relative_path
        """
        source_dir = os.path.join(self.source_root, relative_dir)
        target_dir = os.path.join(self.target_root, relative_dir)

        change_set = _ChangeSet()

        # Get modified times for files in the target directory
        target_filenames = {}
        if os.path.isdir(target_dir):
            for filename in os.listdir(target_dir):
                path = os.path.join(target_dir, filename)
                mtime = os.stat(path).st_mtime
                target_filenames[filename] = round(mtime, 4)

        # Get modified times for files in the source directory
        source_filenames = {}
        if os.path.isdir(source_dir):
            for filename in os.listdir(source_dir):
                path = os.path.join(source_dir, filename)
                mtime = os.stat(path).st_mtime
                source_filenames[filename] = round(mtime, 4)

        # Any files in target_filenames but not in source_filenames is marked for deletion. Remove the dependency map
        # file if it has been marked.
        change_set.delete |= set([os.path.join(target_dir, filename) for filename in target_filenames.keys() - source_filenames.keys()])
        if self.dependency_map_path in change_set.delete:
            change_set.delete.remove(self.dependency_map_path)

        # Iterate over files in source_filenames but not in target_filenames
        changed_filenames = [filename for filename, mtime in source_filenames.items() - target_filenames.items()]
        for filename in changed_filenames:
            relative_path = os.path.join(relative_dir, filename)
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            
            is_ignored = any([regex.match(relative_path) for regex in self.ignore_paths])
            if not is_ignored:
                # If the path is a directory, collect changes for it and merge in with the current change set
                if os.path.isdir(source_path):
                    change_set.merge(self._collect_changes(relative_path))
                else:
                    self._add_render_dependencies(self.source_root, source_path, relative_path)
                    change_set.copy.add((source_path, target_path))
        return change_set

    def _add_render_dependencies(self, source_root, source_path, relative_path):
        """
        Adds rendering dependencies to the dependency map using the files associated handler.

        Args:
            path (str): File path to gather dependencies for.
        Returns:
            None
        """
        handler = get_handler(relative_path)
        if handler is not None and hasattr(handler, 'dependencies'):
            for dependency in handler.dependencies(source_root, source_path):
                if dependency not in self.dependencies:
                    self.dependencies[dependency] = set()
                    self._add_render_dependencies(source_root, dependency, self._relative_path(source_path))
                self.dependencies[dependency].add(source_path)

    def _process_changes(self, change_set):
        """
        Processes a change set, performing rendering, copying, and deletion necessary.

        Args:
            change_set (_ChangeSet): Change set to process.
        Returns:
            None
        """
        # Delete files, and remove empty directories
        for target_path in change_set.delete:
            print('DEL ' + target_path)
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
                if target_path in self.dependencies:
                    del self.dependencies[target_path]
                for items in self.dependencies.values():
                    if target_path in items:
                        items.remove(target_path)

        # Copy files if no handler is available, else add them to be rendered
        render = set()
        for source_path, target_path in change_set.copy:
            self._ensure_path(target_path)
            handler = get_handler(self._relative_path(source_path))
            if handler is not None:
                render.add((source_path, target_path))
            else:
                shutil.copyfile(source_path, target_path)
                self._copy_times(source_path, target_path)
                print('CPY ' + target_path)

        # Find dependencies for files in the render list, and add them to the list
        for source_path, target_path in list(render):
            if source_path in self.dependencies:
                for dependency_source_path in self.dependencies[source_path]:
                    dependency_relative_path = self._relative_path(dependency_source_path)
                    dependency_target_path = os.path.join(self.target_root, dependency_relative_path)
                    render.add((dependency_source_path, dependency_target_path))

        # Render files in with the appropriate handlers.
        for source_path, target_path in render:
            handler = get_handler(self._relative_path(source_path))
            content = handler.render(self.source_root, source_path)
            f = open(target_path, 'w')
            f.write(content)
            f.close()
            self._copy_times(source_path, target_path)
            print('RND ' + target_path)

    def _relative_path(self, path):
        """
        Get the relative path to source_root or target_root.

        Args:
            path: An absolute path.
        Returns:
            str: Path relative to the source or target root. If the absolute path is relative to neither, the absolute
                 path will be returned.
        """
        if path.startswith(self.source_root):
            return path[len(self.source_root) + 1:]
        elif path.startswith(self.target_root):
            return path[len(self.target_root) + 1:]
        return path

    def _ensure_path(self, path):
        """
        Creates the parent directory for a path if it does not yet exist.

        Args:
            path (str): Path to create parent directories for.
        Returns:
            None
        """
        path = os.path.split(path)[0]
        if not os.path.isdir(path):
            os.makedirs(path)

    def _copy_times(self, source_path, target_path):
        """
        Copies access and modified times from one file to another.

        Args:
            source_path (str): File path to copy times from.
            target_path (str): File path to copy times to.
        Returns:
            None
        """
        stat = os.stat(source_path)
        os.utime(target_path, (stat.st_atime, stat.st_mtime))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_root', metavar='SOURCE_PATH')
    parser.add_argument('target_root', metavar='TARGET_PATH')
    parser.add_argument('-f', '--force-generate', default=GenStatic.DEFAULT_FORCE_GENERATE, action='store_true', required=False)
    parser.add_argument('--ignore-matches', dest='ignore_paths', default=GenStatic.DEFAULT_IGNORE_PATHS, help='File regexes to ignore.')
    args = vars(parser.parse_args())

    if isinstance(args['ignore_paths'], str):
        args['ignore_paths'] = str(args['ignore_paths']).split(',')
    
    try:
        gen_static = GenStatic(**args)
        gen_static.generate()
    except IOError as e:
        print(str(e))