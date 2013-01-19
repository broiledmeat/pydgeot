import sys
import os
import time

class _FSObserverBase:
    observer = None
    changed_timeout = 10
    def __init__(self, path):
        self.path = path
        self.changed = {}
    def start(self):
        pass
    def queue_changed(self, path):
        if not os.path.isdir(path):
            self.changed[path] = time.time()
    def signal_changed(self):
        stime = time.time()
        for path, mtime in list(self.changed.items()):
            if self.is_locked(path):
                continue
            if mtime + self.changed_timeout < stime:
                self.on_changed(path)
                del self.changed[path]
    def on_changed(self, path):
        pass
    def is_locked(self, path):
        return False

if sys.platform == 'linux':
    try:
        import pyinotify

        class FSObserver(_FSObserverBase, pyinotify.ProcessEvent):
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
                    if notifier.check_events(2000):
                        notifier.read_events()
                    self.signal_changed()
            def process_default(self, e):
                self.queue_changed(e.pathname)
    except ImportError:
        pass

elif sys.platform == 'win32':
    try:
        import win32file
        import win32con
        import win32event
        import pywintypes

        class FSObserver(_FSObserverBase):
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
                    rc = win32event.WaitForSingleObject(overlapped.hEvent, 2000)
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
                    f = open(path, 'r')
                    f.close()
                    return False
                except IOError:
                    return True
    except ImportError:
        pass

if 'FSObserver' not in globals():
    import time

    class FSObserver(_FSObserverBase):
        observer = 'fallback'
        changed_timeout = 25
        def start(self):
            before = self.get_files_list()
            while True:
                time.sleep(10)
                after = self.get_files_list()
                added = [f for f in after if not f in before]
                removed = [f for f in before if not f in after]
                updated = [f for f in after if f in before and after[f] != before[f]]
                for path in added + removed + updated:
                    path = os.path.abspath(os.path.join(self.path, path))
                    self.queue_changed(path)
                before = after
                self.signal_changed()
        def get_files_list(self):
            walk = os.walk(self.path)
            files = [os.path.join(path, filename) for path, dirs, files in walk for filename in files]
            return dict([(path, os.stat(path).st_mtime) for path in files])
