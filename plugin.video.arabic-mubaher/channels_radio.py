import xbmcgui
import xbmcplugin
import sys
import list_radiochannel as list_fill
class radio:
   def  channel():
     fill=list_fill.list_radio
     channels=fill.fill()

     window=xbmcgui.Window(10000)
     xbmcplugin.setContent(int(sys.argv[1]), "channelsRradi")
     for conuter, channel in enumerate(channels):
           channel_list = xbmcgui.ListItem(label=channel["name"])
           channel_list.setInfo(type="video", infoLabels={"Title": channel["name"], "Genre":  channel["kind"]})
           channel_list.setArt({'fanart':channel["logo"]})
           channel_list.setArt({'thumb':channel["logo"]})
          # channel_list.setProperty("IsPlayable", "true")
           xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=channel["url"], listitem=channel_list, isFolder=False)
            
     xbmcplugin.endOfDirectory(int(sys.argv[1]))  

        
        
     
        
       
     
     
     
     

    
    
    
    
    
     pass #def  channel():