import json
import xbmcaddon
import os
import xbmcaddon

class categories:
 def _categories():
  
  addon = xbmcaddon.Addon()
  addon_path = addon.getAddonInfo('path')

 
  Categories = [
    {"name": "قنوات مباشر المرئية", "url": "قنوات", "img": "https://tinyurl.com/26lvwexw"},
    {"name": "الإذاعة", "url": "الإذاعة", "img": "https://tinyurl.com/23c538ct"}, 
    {"name": "bookmark", "url": "bookmark", "img": os.path.join(addon_path, "resources", "art", "bookmark.png")}, 
    {"name": "Url", "url": "Url", "img": os.path.join(addon_path, "resources", "art", "link.png")},
]
  return Categories
 
 

   
  