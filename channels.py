import xbmcgui
import xbmcplugin
import sys
import urllib.parse
import json
import xbmc
import xbmcaddon
import os
import xbmcvfs

class ChannelsTv :
    def channel():
          channels=[
              {"name":"channel ","kind":"p","country":"ps" ,"url":"url1","logo":"logo1"},
                       ]
          window=xbmcgui.Window(10000)
          xbmcplugin.setContent(int(sys.argv[1]), "channel")

    # Loop through the movies and add them to the window
          for i, movie in enumerate(channels):
           list_item = xbmcgui.ListItem(label=movie["name"])
           list_item.setInfo(type="video", infoLabels={"Title": movie["name"], "Genre": "Movies"})
          list_item.setProperty("IsPlayable", "true")
          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=movie["url"], listitem=list_item, isFolder=False)

    
         

    # End the window
          xbmcplugin.endOfDirectory(int(sys.argv[1]))

            # Create the Kodi window
        
          

  
  

    
    
    
    
    pass