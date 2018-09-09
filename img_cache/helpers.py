from __future__ import print_function
import os
import tempfile
import json
import base64
from django.conf import settings
from django.core.cache import cache
from PIL import Image

from img_cache.compat import urlopen
from img_cache import default

SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000')
TMP_DIR = tempfile.gettempdir() + '/' + getattr(settings, 'IMGCACHE_TMP_DIR', default.IMGCACHE_TMP_DIR)
CACHE_KEY_PREFIX = getattr(settings,'IMGCACHE_KEY_PREFIX', default.IMGCACHE_KEY_PREFIX)
class ImageResize(object):
    """
    helper class to deal with image resizing
    """
    def __init__(self, url, **kwargs):
        self.width = kwargs.get('width', None)
        self.height = kwargs.get('height', None)
        self.q = kwargs.get('q', None)
        # if image is not in some bucket(s3 etc.) then fetch from http://localhost/img-src
        self.url = url if 'http' in url else SITE_URL + url
        self.name = url.split('/')[-1]
        self.format = self.name.split('.')[-1]
        self.base64 = None
        if self.q:
            self.cache_key = CACHE_KEY_PREFIX + '-' + self.url + "?q=" + str(self.q)
        else:
            self.cache_key = CACHE_KEY_PREFIX + '-' + self.url + "-" + str(self.width) + 'x' + str(self.height)

    def _encode(self):
        data = {'width':self.width, 'height': self.height, 'base64':self.base64, 'name':self.name,
                'url':self.url, 'format':self.format, 'q':self.q
            }
        return json.dumps(data)

    def _decode(self):
        if cache.get(self.cache_key):
            data = json.loads(cache.get(self.cache_key))
        else:
            data = {}
        self.width = data.get('width')
        self.height = data.get('height')
        self.base64 = data.get('base64')
        self.format = data.get('format')
        self.url = data.get('url')
        self.q = data.get('q')
        self.name = data.get('name')
        return self

    def resize_calculator(self, width, height, q):
        resized_width = round((width*q*1.0)/100.0)
        resized_height = round((height*q*1.0)/100.0)
        return int(resized_width),int(resized_height)

    def is_img_cached(self):
        if self.cache_key and cache.get(self.cache_key):
            return True
        return False

    def resize(self):
        if self.is_img_cached():
            return self._decode()
        if not os.path.exists(TMP_DIR):
            os.mkdir(TMP_DIR)
        img_tmp_file = '{0}/{1}'.format(TMP_DIR, self.name)
        with open(img_tmp_file, 'wb') as im:
            im.write(urlopen(self.url).read())
        large_image = Image.open(img_tmp_file)

        if self.q:
            if not (self.q > 1 and self.q < 100):
                raise Exception("resize percent should be b/w 1 and 100")
            self.width, self.height = self.resize_calculator(large_image.width, large_image.height, self.q)
        
        if not (self.width and self.height):
            raise Exception("please specify height and width or resize percent")
        
        resized_img = large_image.resize((self.width, self.height), Image.ANTIALIAS)
        resized_img_file = "{0}/tmp_{1}".format(TMP_DIR, self.name)
        resized_img.save(resized_img_file)
        with open(resized_img_file,"rb") as im:
            self.base64 = "data:image/{0};base64,{1}".format(self.format, base64.b64encode(im.read()))
        try:
            os.remove(img_tmp_file)
            os.remove(resized_img_file)
        except Exception as e:
            print(e)
            print("Unable to remove tmp imgs file in {0}".format(TMP_DIR))
        cache.set(self.cache_key, self._encode())
        return self

    def __str__(self):
        return """
        <img src="{0}" width="{1}" height="{2}" data-src="{3}">
        """.format(self.base64, self.width, self.height, self.url)
    
    def __repr__(self):
        return self.__str__()