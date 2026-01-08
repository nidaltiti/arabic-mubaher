import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import urllib.parse
import json
import xbmcvfs
from  resources.lib.settings import KodiSettings
import threading
import time
import urllib.parse
import sys


_media_library = KodiSettings(
    addon_id="plugin.video.arabic-mubaher",
    filename="media_library.json"
)




class OptionsWindow(xbmcgui.WindowXML):

    Data_Loaded = ""
    data=_media_library.get("media", {})

    def onInit(self):
         args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
         raw_json = urllib.parse.unquote(args["file"])
         self.Data_Loaded = json.loads(raw_json)
     #    file_name = self.Data_Loaded.get("info")
     #    self.paramter(str (file_name))
         xbmcgui.Dialog().notification("Test", "Window loaded!", xbmcgui.NOTIFICATION_INFO, 3000)

    def onClick(self, controlId):


        if controlId == 200:
             #   xbmcgui.Dialog().ok("Test", self.keybord("next"))
             input = self.keybord("Enter Path/Url:")
             self.Data_Loaded["path"] = input if input else self.Data_Loaded.get("path")

             self.paramter(self.Data_Loaded)
                
        elif controlId == 201:
            input= self.keybord("Enter INFO:")
            input = input.replace("\n", " ").replace("\r", " ")
            self.Data_Loaded["info"] = input if input else self.Data_Loaded.get("info")
           
            self.paramter(self.Data_Loaded)
            
        elif controlId == 202:
           # xbmcgui.Dialog().notification("Trailer", "Playing trailer...", xbmcgui.NOTIFICATION_INFO, 3000)
            input= self.keybord("Enter Trailer URL:")
            old_key = self.Data_Loaded.get("file")
          
            if old_key in self.data:
             self. data[input] = self.data.pop(old_key)
            self.Data_Loaded["file"] = input if input else old_key
           
            self.paramter(self.Data_Loaded)
   
     #iconId actions
        elif controlId == 203:
            input= self.keybord("Enter Icon URL:")
            self.Data_Loaded["icon"] = input if input else self.Data_Loaded.get("icon")
           
            self.paramter(self.Data_Loaded)
      #Thumbnail
        elif controlId == 204:
            input= self.keybord("Enter Thumbnail URL:")
            self.Data_Loaded["thumb"] = input if input else self.Data_Loaded.get("thumb")
           
            self.paramter(self.Data_Loaded)
        elif controlId == 205:
            self.close()
    def keybord(self, string=""):
        keyboard = xbmc.Keyboard("", string)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return ""
  
    def  paramter(self, prameter):
       #    xbmcgui.Dialog().textviewer("Test", str (prameter)
          
        self.data[prameter["file"]]=prameter
        _media_library.set("media", self.data)

  
    def _pramter_(self, file_path):
           
           xbmcgui.Dialog().ok("Test", )
         
          