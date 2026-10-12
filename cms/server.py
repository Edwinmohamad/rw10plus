#!/usr/bin/env python3
"""Small private CMS for public RW10+ content, no third-party dependencies."""
import os, json, sqlite3, secrets, hashlib, hmac, time, mimetypes, re, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from http import cookies

ROOT=Path(__file__).resolve().parent
STORE=Path(os.getenv('CMS_DATA_DIR','/data')); STORE.mkdir(parents=True,exist_ok=True)
MEDIA=STORE/'media'; MEDIA.mkdir(exist_ok=True)
DB=STORE/'cms.sqlite3'
ADMIN_PASS=os.getenv('CMS_ADMIN_PASSWORD','RW10Admin2026!')
PORT=int(os.getenv('CMS_PORT','8090'))
MAX_BODY=7*1024*1024
PUBLIC_KINDS=('news','events','officials','stats','gallery','umkm')
lock=threading.RLock()
failures={}

def conn():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; return c
with conn() as c:
 c.execute('CREATE TABLE IF NOT EXISTS content(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,rt TEXT NOT NULL DEFAULT "ALL",title TEXT NOT NULL,subtitle TEXT NOT NULL DEFAULT "",body TEXT NOT NULL DEFAULT "",image TEXT NOT NULL DEFAULT "",value TEXT NOT NULL DEFAULT "",published INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,csrf TEXT NOT NULL, expires_at INTEGER NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS idx_kind_pub ON content(kind,published,rt)')

class Handler(BaseHTTPRequestHandler):
 server_version='RW10-CMS'
 def send(self,code,data=None,ctype='application/json',headers=None):
  payload=data if isinstance(data,bytes) else json.dumps(data if data is not None else {},ensure_ascii=False).encode()
  self.send_response(code); self.send_header('Content-Type',ctype+'; charset=utf-8' if ctype.startswith('text/') or ctype=='application/json' else ctype); self.send_header('Content-Length',str(len(payload))); self.send_header('Cache-Control','no-store' if ctype=='application/json' else 'public, max-age=86400'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','SAMEORIGIN'); self.send_header('Referrer-Policy','same-origin')
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers(); self.wfile.write(payload)
 def jsonbody(self):
  try: length=int(self.headers.get('Content-Length','0'))
  except ValueError:raise ValueError('Ukuran tidak valid')
  if length<1 or length>MAX_BODY:raise ValueError('Ukuran request tidak valid')
  return json.loads(self.rfile.read(length))
 def auth(self,write=False):
  jar=cookies.SimpleCookie()
  try:jar.load(self.headers.get('Cookie',''))
  except cookies.CookieError:return False
  token=jar.get('rw10cms'); token=token.value if token else ''
  if not token:return False
  digest=hashlib.sha256(token.encode()).hexdigest()
  with conn() as c: row=c.execute('SELECT csrf FROM sessions WHERE token_hash=? AND expires_at>?',(digest,int(time.time()))).fetchone()
  if not row:return False
  if write:
   csrf=self.headers.get('X-CSRF-Token','')
   if not csrf or not hmac.compare_digest(csrf,row['csrf']):return False
  return dict(row)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/public':
   args=parse_qs(urlsplit(self.path).query); kind=args.get('kind',[''])[0]; rt=args.get('rt',['ALL'])[0]
   if kind not in PUBLIC_KINDS:return self.send(400,{'error':'Kategori tidak valid'})
   if rt!='ALL' and rt not in ('01','02','03','04'):return self.send(400,{'error':'RT tidak valid'})
   with conn() as c:
    rows=c.execute('SELECT id,kind,rt,title,subtitle,body,image,value,updated_at FROM content WHERE kind=? AND published=1 AND (rt=? OR rt="ALL") ORDER BY updated_at DESC,id DESC LIMIT 100',(kind,rt)).fetchall()
   return self.send(200,{'items':[dict(x) for x in rows]})
  if path.startswith('/media/'):
   filename=path.removeprefix('/media/')
   if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)',filename):return self.send(404,{'error':'Tidak ditemukan'})
   f=MEDIA/filename
   if not f.is_file():return self.send(404,{'error':'Tidak ditemukan'})
   return self.send(200,f.read_bytes(),{'jpg':'image/jpeg','png':'image/png','webp':'image/webp'}[filename.split('.')[-1]])
  if path=='/api/admin/me':
   a=self.auth(); return self.send(200,{'authenticated':bool(a),'csrf':a['csrf'] if a else None})
  if path=='/api/admin/content':
   if not self.auth():return self.send(401,{'error':'Login diperlukan'})
   with conn() as c: rows=c.execute('SELECT * FROM content ORDER BY updated_at DESC,id DESC LIMIT 2000').fetchall()
   return self.send(200,{'items':[dict(x) for x in rows]})
  return self.send(404,{'error':'Tidak ditemukan'})
 def do_POST(self):
  path=urlsplit(self.path).path
  if path=='/api/admin/login':
   addr=self.client_address[0]; t=time.time()
   with lock:
    history=[x for x in failures.get(addr,[]) if x>t-900]; failures[addr]=history
    if len(history)>=5:return self.send(429,{'error':'Terlalu banyak percobaan. Coba lagi nanti.'})
   try:pw=str(self.jsonbody().get('password',''))
   except (ValueError,json.JSONDecodeError):return self.send(400,{'error':'Input tidak valid'})
   if not ADMIN_PASS or len(ADMIN_PASS)<12:return self.send(503,{'error':'Admin CMS belum dikonfigurasi dengan aman'})
   if not hmac.compare_digest(pw,ADMIN_PASS):
    with lock:failures[addr].append(t)
    return self.send(401,{'error':'Kredensial tidak sesuai'})
   with lock:failures.pop(addr,None)
   tok=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
   with conn() as c:c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(tok.encode()).hexdigest(),csrf,int(t)+8*3600))
   return self.send(200,{'ok':True,'csrf':csrf},headers={'Set-Cookie':f'rw10cms={tok}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if os.getenv('CMS_COOKIE_SECURE','false').lower()=='true' else '')})
  if path=='/api/admin/logout':
   jar=cookies.SimpleCookie();jar.load(self.headers.get('Cookie',''))
   tok=jar.get('rw10cms');tok=tok.value if tok else ''
   with conn() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(tok.encode()).hexdigest(),))
   return self.send(200,{'ok':True},headers={'Set-Cookie':'rw10cms=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
  if not self.auth(write=True):return self.send(403,{'error':'Akses tidak diizinkan / token CSRF tidak valid'})
  if path=='/api/admin/upload':
   size=int(self.headers.get('Content-Length','0'))
   if size<1 or size>5*1024*1024:return self.send(413,{'error':'Gambar maksimum 5 MB'})
   kind=self.headers.get('Content-Type','')
   if kind not in ('image/jpeg','image/png','image/webp'):return self.send(415,{'error':'Hanya JPG, PNG, dan WebP'})
   raw=self.rfile.read(size)
   valid=(kind=='image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (kind=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (kind=='image/webp' and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP')
   if not valid:return self.send(415,{'error':'Isi file bukan gambar yang sesuai'})
   ext={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[kind]
   name=secrets.token_hex(16)+'.'+ext
   (MEDIA/name).write_bytes(raw)
   return self.send(201,{'image':'/content-api/media/'+name})
  if path=='/api/admin/content':
   try:data=self.jsonbody()
   except (ValueError,json.JSONDecodeError):return self.send(400,{'error':'JSON tidak valid'})
   category=str(data.get('kind','')); rt=str(data.get('rt','ALL')); title=str(data.get('title','')).strip()
   if category not in PUBLIC_KINDS or rt not in ('ALL','01','02','03','04') or not title or len(title)>180:return self.send(400,{'error':'Kategori, RT, atau judul tidak valid'})
   fields={k:str(data.get(k,'')).strip() for k in ('subtitle','body','image','value')}
   if any(len(v)> (4000 if k=='body' else 300) for k,v in fields.items()):return self.send(400,{'error':'Teks terlalu panjang'})
   if fields['image'] and not re.fullmatch(r'/content-api/media/[a-f0-9]{32}\.(jpg|png|webp)',fields['image']):return self.send(400,{'error':'Gunakan foto yang diunggah lewat CMS'})
   # Only numeric aggregate stats can be published here; never individual citizen records.
   if category=='stats' and (not fields['value'].isdigit() or len(fields['value'])>9):return self.send(400,{'error':'Nilai statistik harus bilangan bulat'})
   item_id=data.get('id'); pub=1 if data.get('published') is True else 0
   with conn() as c:
    if item_id is not None:
     cur=c.execute('UPDATE content SET kind=?,rt=?,title=?,subtitle=?,body=?,image=?,value=?,published=?,updated_at=? WHERE id=?',(category,rt,title,fields['subtitle'],fields['body'],fields['image'],fields['value'],pub,int(time.time()),item_id))
     if cur.rowcount==0:return self.send(404,{'error':'Data tidak ditemukan'})
    else:
     cur=c.execute('INSERT INTO content(kind,rt,title,subtitle,body,image,value,published,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(category,rt,title,fields['subtitle'],fields['body'],fields['image'],fields['value'],pub,int(time.time())))
     item_id=cur.lastrowid
   return self.send(200,{'ok':True,'id':item_id})
  return self.send(404,{'error':'Tidak ditemukan'})
 def do_DELETE(self):
  path=urlsplit(self.path).path
  if not self.auth(write=True):return self.send(403,{'error':'Tidak diizinkan'})
  match=re.fullmatch(r'/api/admin/content/(\d+)',path)
  if not match:return self.send(404,{'error':'Tidak ditemukan'})
  with conn() as c:c.execute('DELETE FROM content WHERE id=?',(int(match.group(1)),))
  return self.send(200,{'ok':True})

if __name__=='__main__':
 print('RW10 CMS listening on',PORT,flush=True)
 ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
