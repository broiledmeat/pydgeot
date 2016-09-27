import sys
import os
import time


class _ObserverBase:
    """
    Base class for file system observers. Queues file changes and signals change events.
    """
    observer = None
    changed_timeout = 10
    event_timeout = 2

    def __init__(self, path):
        """
        Initialize the observer.

        :param path: Directory path to observe.
        :type path: str
        """
        self.path = path
        self.changed = {}
        self.on_changed_handlers = set()
        """:type: set[callable[str]]"""

    def start(self):
        """
        Start file system observation loop.
        """
        raise NotImplementedError

    def queue_changed(self, path):
        """
        Place a file change event in to the change queue. Should be called from the observation loop when file changes
        are detected.

        :param path: File path to place in to the change queue.
        :type path: str
        """
        if not os.path.isdir(path):
            self.changed[path] = time.time()

    def signal_changed(self):
        """
        Iterate through the change queue, signaling changes for those that are not locked, and have passed the changed
        timeout.
        """
        stime = time.time()
        for path, mtime in list(self.changed.items()):
            if self.is_locked(path):
                continue
            if mtime + self.changed_timeout < stime:
                self.on_changed(path)
                del self.changed[path]

    def on_changed(self, path):
        """
        Called when a file change has been through the queue and timed out (when the file can be sure to have finished
        changing.) This should be overridden in the observer instance.

        :param path: File path to signal as having been changed.
        :type path: str
        """
        for handler in self.on_changed_handlers:
            handler(path)

    def is_locked(self, path):
        """
        Check if a file is locked (still being written to.)

        :param path: File path to check if is locked.
        :type path: str
        :return: If the file path is being written to.
        :rtype: bool
        """
        return False

if sys.platform == 'linux':
    try:
        import pyinotify

        class Observer(_ObserverBase, pyinotify.ProcessEvent):
            """
            File system observer for Linux using inotify.
            """
            observer = 'inotify'

            def start(self):
                mask = pyinotify.IN_CREATE | \
                    pyinotify.IN_DELETE | \
                    pyinotify.IN_MODIFY | \
                    pyinotify.IN_MOVED_FROM | \
                    pyinotify.IN_MOVED_TO
                wm = pyinotify.WatchManager()
                notifier = pyinotify.Notifier(wm, self)
                wm.add_watch(self.path, mask, rec=True)
                while True:
                    notifier.process_events()
                    if notifier.check_events(self.event_timeout * 1000):
                        notifier.read_events()
                    self.signal_changed()

            def process_default(self, e):
                """
                Pyinotify catch-all change event.

                :param e: Pyinotify change event.
                :type e: pyinotify.ProcessEvent
                """
                self.queue_changed(e.pathname)
    except ImportError:
        pass

elif sys.platform == 'win32':
    try:
        import win32file
        import win32con
        import win32event
        import pywintypes

        class Observer(_ObserverBase):
            """
            File system observer for Windows.
            """
            observer = 'win32'

            def start(self):
                handle = win32file.CreateFile(
                    self.path,
                    1,
                    win32con.FILE_SHARE_READ |
                    win32con.FILE_SHARE_WRITE |
                    win32con.FILE_SHARE_DELETE,
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_FLAG_BACKUP_SEMANTICS |
                    win32file.FILE_FLAG_OVERLAPPED,
                    None)
                mask = win32con.FILE_NOTIFY_CHANGE_FILE_NAME | \
                    win32con.FILE_NOTIFY_CHANGE_DIR_NAME | \
                    win32con.FILE_NOTIFY_CHANGE_SIZE | \
                    win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
                buf = win32file.AllocateReadBuffer(8192)
                overlapped = pywintypes.OVERLAPPED()
                overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
                while True:
                    win32file.ReadDirectoryChangesW(
                        handle,
                        buf,
                        True,
                        mask,
                        overlapped)
                    rc = win32event.WaitForSingleObject(overlapped.hEvent, self.event_timeout * 1000)
                    if rc == win32event.WAIT_OBJECT_0:
                        nbytes = win32file.GetOverlappedResult(handle, overlapped, True)
                        if nbytes:
                            paths = win32file.FILE_NOTIFY_INFORMATION(buf, nbytes)
                            for action, path in paths:
                                path = os.path.abspath(os.path.join(self.path, path))
                                self.queue_changed(path)
                    self.signal_changed()

            def is_locked(self, path):
                if not os.path.exists(path):
                    return False
                try:
                    # When copying files, Windows will only report one change event. On large files this can cause the
                    # change queue to timeout and signal a change prematurely. Luckily, the file won't be open for read
                    # until the copy operation is done, so check for readability.
                    with open(path, 'r'):
                        pass
                    return False
                except IOError:
                    return True
    except ImportError:
        pass

elif sys.platform == 'darwin':
    try:
        from fsevents import Observer as fseObserver
        from fsevents import Stream as fseStream

        class Observer(_ObserverBase):
            """
            File system observer for OSX using fsevents.
            """
            observer = 'fsevents'

            def start(self):
                def process_event(e):
                    self.queue_changed(e.name)
                observer = fseObserver()
                stream = fseStream(process_event, self.path, file_events=True)
                observer.schedule(stream)
                observer.start()
                while True:
                    time.sleep(self.event_timeout)
                    self.signal_changed()
    except ImportError:
        pass

if 'Observer' not in globals():
    class Observer(_ObserverBase):
        """
        Platform independent fallback file system observer.
        """
        observer = 'fallback'
        changed_timeout = 25
        event_timeout = 10

        def start(self):
            before = self.get_files_list()
            while True:
                time.sleep(self.event_timeout)
                after = self.get_files_list()
                added = [f for f in after if f not in before]
                removed = [f for f in before if f not in after]
                updated = [f for f in after if f in before and after[f] != before[f]]
                for path in added + removed + updated:
                    path = os.path.abspath(os.path.join(self.path, path))
                    self.queue_changed(path)
                before = after
                self.signal_changed()

        def get_files_list(self):
            """
            Get a flat list of file paths with modified times.

            :return: Dict of file paths and modified times.
            :rtype: dict[str, int]
            """
            walk = os.walk(self.path)
            files = [os.path.join(path, filename) for path, dirs, files in walk for filename in files]
            return dict([(path, os.stat(path).st_mtime) for path in files])
