#!/usr/bin/env python3
"""Retrieve preview images from registered Original Print product pages.
Requires: pip install requests beautifulsoup4 pillow
Run from this directory: python import_merch_images.py
Only image URLs explicitly advertised by each product page are considered.
"""
from pathlib import Path
from urllib.parse import urljoin, urlparse
from io import BytesIO
import json, re, sys, time
try:
 import requests
 from bs4 import BeautifulSoup
 from PIL import Image
except ImportError:
 sys.exit('Install dependencies: pip install requests beautifulsoup4 pillow')
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'product-sources.json'
OUT=ROOT/'merch-images';OUT.mkdir(exist_ok=True)
manifest={};report=[]
session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; YABASUGI-MerchPreview/1.0)'})
for item in json.loads(SOURCE.read_text()):
 pid=str(item['id']);url=item['url'];entry={'id':pid,'color':item.get('color'),'url':url,'status':'not_found'}
 try:
  page=session.get(url,timeout=18);page.raise_for_status()
  if 'originalprint.jp' not in urlparse(page.url).netloc:raise ValueError('Unexpected redirect domain')
  soup=BeautifulSoup(page.text,'html.parser');candidates=[]
  for key,attr in [('og:image','property'),('twitter:image','name'),('twitter:image:src','name')]:
   for meta in soup.find_all('meta',attrs={attr:key}):
    if meta.get('content'):candidates.append(urljoin(page.url,meta['content']))
  # Only metadata-backed candidates; never mistake product stock photos for verified designs.
  candidates=list(dict.fromkeys(candidates));entry['candidates']=len(candidates)
  for candidate in candidates:
   parsed=urlparse(candidate)
   if parsed.scheme not in ('https','http'):continue
   r=session.get(candidate,timeout=18);r.raise_for_status()
   if not r.headers.get('Content-Type','').lower().startswith('image/'):continue
   if len(r.content)>12_000_000:continue
   im=Image.open(BytesIO(r.content));im.load()
   if im.width<250 or im.height<250:continue
   # Do not use a generic store logo as a product image: report for review.
   im.thumbnail((1200,1200));dest=OUT/f'{pid}.webp';im.convert('RGB').save(dest,'WEBP',quality=85)
   manifest[pid]=f'merch-images/{pid}.webp';entry.update(status='downloaded_review_required',image=str(dest.relative_to(ROOT)),width=im.width,height=im.height)
   break
 except Exception as exc:entry['error']=str(exc)[:220]
 report.append(entry);print(pid,entry['status'],entry.get('error',''))
 time.sleep(.35)
(ROOT/'merch-images.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(ROOT/'merch-image-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f'Downloaded {len(manifest)} / {len(report)}. Check that each image is the correct design/color before publishing.')
