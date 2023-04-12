import xbmcgui
import xbmcplugin
import sys
import urllib.parse
import list_tvchannel as list_fill

class ChannelsTv :
    def channel():
          fill=list_fill.list_tv
          channels=fill.fill()
          window=xbmcgui.Window(10000)
          xbmcplugin.setContent(int(sys.argv[1]), "channel")

    # Loop through the movies and add them to the window
          for conuter, channel in enumerate(channels):
           channel_list = xbmcgui.ListItem(label=channel["name"])
           channel_list.setInfo(type="video", infoLabels={"Title": channel["name"], "Genre":  channel["kind"]})
           channel_list.setArt({'fanart':channel["logo"]})
           channel_list.setArt({'thumb':channel["logo"]})
          # channel_list.setProperty("IsPlayable", "False")
           xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=channel["url"], listitem=channel_list, isFolder=False)

    
         

    # End the window
          xbmcplugin.endOfDirectory(int(sys.argv[1]))

            # Create the Kodi window
        
          

  
  

    
    
    
    
    pass