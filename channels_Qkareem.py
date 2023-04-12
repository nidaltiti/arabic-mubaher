import xbmcgui
import xbmcplugin
import json
import xbmc
import xbmcaddon
import os
import xbmcvfs
import sys
import list_qkareemchannel as list_fill
class Qkareem: # quran kareem
   def  channel():
     fill=list_fill.list_Qkareem
     channels=fill.fill()

     window=xbmcgui.Window(10000)
     xbmcplugin.setContent(int(sys.argv[1]), "channelsQkareem")
     for conuter, channel in enumerate(channels):
           channel_list = xbmcgui.ListItem(label=channel["name"])
           channel_list.setInfo(type="video", infoLabels={"Title": channel["name"], "Genre":  channel["kind"]})
           channel_list.setArt({'fanart':channel["logo"]})
           channel_list.setArt({'thumb':channel["logo"]})
          # channel_list.setProperty("IsPlayable", "true")
           xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=channel["url"], listitem=channel_list, isFolder=False)
            
     xbmcplugin.endOfDirectory(int(sys.argv[1]))  

        
        
     
        
       
     
     
     
     

    
    
    
    
    
     pass #def  channel():