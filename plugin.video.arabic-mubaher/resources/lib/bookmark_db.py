import os
import sqlite3
import xbmcvfs

class BookmarkManager:
    def __init__(self, addon_id="plugin.video.arabic-mubaher", filename="bookmarks.db"):
        self.ADDON_DATA = xbmcvfs.translatePath(f"special://profile/addon_data/{addon_id}/")
        self.FILE_PATH = os.path.join(self.ADDON_DATA, filename)

        if not xbmcvfs.exists(self.ADDON_DATA):
            xbmcvfs.mkdirs(self.ADDON_DATA)

        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.FILE_PATH)

    def _create_table(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )
            ''')
            conn.commit()

    def add(self, name):
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT INTO bookmarks (name) VALUES (?)", (name,))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, old_name, new_name):
        """تغيير اسم قناة مخزنة"""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE bookmarks SET name = ? WHERE name = ?", (new_name, old_name))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove(self, name):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM bookmarks WHERE name = ?", (name,))
            conn.commit()

    def remove_all(self):
        """تفريغ القائمة بالكامل"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM bookmarks")
            conn.commit()

    def read_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM bookmarks")
            return [row[0] for row in cursor.fetchall()]