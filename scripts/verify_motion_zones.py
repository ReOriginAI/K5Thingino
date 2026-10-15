import urllib.request,urllib.error,ssl,http.cookiejar,json,time
base='https://192.168.1.54'; ctx=ssl._create_unverified_context()
url=base+'/x/motion-zones.cgi'
try:
 urllib.request.urlopen(url,context=ctx,timeout=10);raise AssertionError('unauth accepted')
except urllib.error.HTTPError as e:assert e.code==401,e.code
print('AUTH_REQUIRED_PASS',flush=True)
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),urllib.request.HTTPSHandler(context=ctx))
req=urllib.request.Request(base+'/x/login.cgi',data=json.dumps(dict(username='root',password='pass'),separators=(',',':')).encode(),headers={'Content-Type':'application/json'})
with opener.open(req,timeout=10) as r:assert json.load(r)['success']
def get():
 with opener.open(url,timeout=10) as r:return json.load(r)
j=get();assert j['enabled'] and j['sensitivity']==2 and j['mask']==65535 and j['live']['active'],j
print('DETECTOR_ACTIVE_PASS',j,flush=True)
with opener.open(url+'?snapshot&t=123',timeout=10) as r:
 jpeg=r.read();assert r.headers.get_content_type()=='image/jpeg' and jpeg.startswith(bytes.fromhex('ffd8')),jpeg[:100]
print('AUTHENTICATED_SNAPSHOT_PASS',len(jpeg),flush=True)
for body,headers in [(b'1 2 0',{'Content-Type':'application/x-thingino-motion-zones'}),(b'1 2 65535',{})]:
 req=urllib.request.Request(url,data=body,headers=headers)
 try:opener.open(req,timeout=10);raise AssertionError('invalid save accepted')
 except urllib.error.HTTPError as e:assert e.code in (400,403),e.code
print('INPUT_AND_CROSS_ORIGIN_HEADER_CHECK_PASS',flush=True)
req=urllib.request.Request(url,data=b'1 2 65535',headers={'Content-Type':'application/x-thingino-motion-zones'})
with opener.open(req,timeout=10) as r:assert json.load(r)['saved']
print('ZONE_SELECTION_SAVE_PASS',flush=True)
time.sleep(20)
j=get();assert j['live']['active'] and j['mask']==65535 and j['enabled'],j
print('DETECTOR_AFTER_RESTART_PASS',j,flush=True)
with opener.open(base+'/a/plugins.js',timeout=10) as r:assert 'Motion zones' in r.read().decode()
print('MENU_PASS',flush=True)
