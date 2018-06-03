import re
from django.conf import settings
from django import template
from django.template.base import TemplateSyntaxError
from django.template.base import kwarg_re
register = template.Library()

from img_cache.helpers import ImageResize
from img_cache import default

class ImageCacheNode(template.Node):
    def __init__(self, nodelist, src, kwargs, asvar=None):
        self.nodelist = nodelist
        self.src = src
        self.kwargs = kwargs
        self.asvar = asvar
    def render(self, context):
        for key,val in self.kwargs.items():
            self.kwargs[key] = val.resolve(context)

        self.src = self.src.resolve(context)
        img = ImageResize(self.src, **self.kwargs).resize()
        if self.asvar:
            context.push()
            context[self.asvar] = img
            output = self.nodelist.render(context)
            context.pop()
        else:
            output = img
        return output

@register.tag(name='imgcache')
def imgcache(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument,a src url of img" % bits[0])
    src = parser.compile_filter(bits[1])
    asvar = None
    bits = bits[2:]
    if len(bits) >= 2 and bits[-2] == "as":
        asvar = bits[-1]
        bits = bits[:-2]
    kwargs = {}
    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError("Malformed arguments to imgcache")
            name, value = match.groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
    nodelist = parser.parse(('endimgcache',))
    parser.delete_first_token()
    return ImageCacheNode(nodelist, src, kwargs, asvar)

@register.filter(name='imgcache_src')
def imgcache_src(src, q=10):
    try:
        q = int(q)
    except Exception:
        raise TemplateSyntaxError("resize percent should be a intger number enclosed with single quotes!")
    return ImageResize(src, q=int(q)).resize().base64

@register.filter(name='imgcache_content')
def imgcache_content(content, q=10):
    DEFAULT_CONTENT_CLASS = getattr(settings,'IMGCACHE_DEFAULT_CONTENT_CLASS', default.IMGCACHE_DEFAULT_CONTENT_CLASS )
    DEFAULT_CONTENT_STYLE = getattr(settings,'IMGCACHE_DEFAULT_CONTENT_STYLE', default.IMGCACHE_DEFAULT_CONTENT_STYLE )
    img_replacement = u"""
    <img src="{0}" data-src="{1}" class="{2}" style="{3}" alt="{4}">
    """
    img_pattern = r'(<img [^>]+>)'
    img_src_pattern = r'src="([^"]+)"'
    img_height_pattern = r'height="/d+'
    img_width_pattern = r'width="/d+"'
    img_alt_pattern = r'alt="([^"]+)"'
    img_tags = re.findall(img_pattern, content)
    for img in img_tags:
        try:
            img_src = re.findall(img_src_pattern, img)[0]
            try:
                img_alt = re.findall(img_alt_pattern, img)[0]
            except Exception as NoImgAlt:
                img_alt = 'image-preview'
            try:
                img_height = re.findall(img_height_pattern, img)[0]
                img_width = re.findall(img_width_pattern, img)[0]
            except Exception as NoWidthHeight:
                img_height = 377
                img_width = 727
        except Exception as NoImgSrc:
            img_src = None
        if img_src:
            img_data = imgcache_src(img_src, q)
            new_img_repl = img_replacement.format(img_data, img_src,DEFAULT_CONTENT_CLASS, DEFAULT_CONTENT_STYLE, img_alt)
            content = content.replace(img, new_img_repl)
    return content
