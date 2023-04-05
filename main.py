import xbmcgui
import xbmcplugin
import sys
import urllib.parse
import json
import xbmc
import xbmcaddon
import get_category
import os
import xbmcvfs
import channels 
def x():
  pass
 

  

def add_category():
  list_Categories=get_category.categories
 # Create the Kodi window
  window=xbmcgui.Window(10000)
 # Clear the existing items in the window
  addon = xbmcaddon.Addon()
  xbmcplugin.setContent(int(sys.argv[1]), "videos")
  Categories=list_Categories._categories()
 
  #Categories = (data['categories'])
  for count,Category in enumerate(Categories):
   list_Category= xbmcgui.ListItem(label=Category["name"])
   list_Category.setArt({'fanart':Category["img"]})
   list_Category.setArt({'thumb':Category["img"]})
   list_Category.setProperty("IsFolder","true")
   xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sys.argv[0] + "?category=" + str(count), listitem=list_Category, isFolder=True)


# End the window
  xbmcplugin.endOfDirectory(int(sys.argv[1]))
  
  
def main():
 show_channels= channels.ChannelsTv
  #add_category()
  #Parse the command-line arguments
 args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
 
 if "category" not in args:

       add_category()
       pass
        # If no category was selected, add the categories to the Kodi window
 else:
    Category_index = int(args["category"])
    if Category_index== 0:
     channels.ChannelsTv.channel()

     pass
     
    elif  Category_index== 1:
 
     pass
    elif  Category_index== 2:
   
     pass

if __name__ == "__main__":
   main()