import os
import json
import xbmcvfs
import xbmcgui
class KodiSettings:
    def __init__(self, addon_id="plugin.video.arabic-mubaher", filename="settings.json"):
        """تهيئة مسار الملف وإنشاءه إذا لم يكن موجود"""
        self.ADDON_DATA = xbmcvfs.translatePath(f"special://profile/addon_data/{addon_id}/")
        self.FILE_PATH = os.path.join(self.ADDON_DATA, filename)
        self.data = None

        # إنشاء المجلد إذا لم يكن موجود
        if not xbmcvfs.exists(self.ADDON_DATA):
            xbmcvfs.mkdirs(self.ADDON_DATA)

        # تحميل البيانات من الملف
        self._load()

    def _load(self):
        """تحميل بيانات JSON من الملف"""
        try:
            if xbmcvfs.exists(self.FILE_PATH):
                with xbmcvfs.File(self.FILE_PATH) as f:
                    data = f.read().decode("utf-8")
                    f.close()
                    self.settings = json.loads(data)
            else:
                self.settings = {}
                self._save()
        except Exception:
            self.settings = {}

    def _save(self):
        """حفظ البيانات إلى الملف"""
        data = json.dumps(self.settings, indent=4)
        with xbmcvfs.File(self.FILE_PATH, "w") as f:
            f.write(bytearray(data, "utf-8"))
            f.close()

    def get(self, key, default=None):
        """إرجاع قيمة مفتاح أو القيمة الافتراضية"""
        path = self.FILE_PATH
        with xbmcvfs.File(self.FILE_PATH, 'r') as f:
         self.data = f.read()
         f.close()
         self.settings=json.loads(self.data)
      
       # data = f.read().decode("utf‑8")
        
        return self.settings.get(key, default)

    def set(self, key, value):
        """تعيين أو تحديث قيمة مفتاح"""
        self._load()
        self.settings[key] = value
        self._save()

    def remove(self, key):
        """حذف مفتاح إذا كان موجود"""
        self._load()
        if key in self.settings:
            del self.settings[key]
            self._save()

    def all(self):
        """إرجاع كل البيانات"""
        self._load()
        return self.settings
