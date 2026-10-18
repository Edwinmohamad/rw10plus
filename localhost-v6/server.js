'use strict';
/* RW10+ v6.0 — local-first management server, Node.js >=22.5, zero npm dependencies. */
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {DatabaseSync}=require('node:sqlite');
const ROOT=__dirname, DATA=path.resolve(process.env.DATA_DIR||path.join(ROOT,'data'));
const UPLOADS=path.join(DATA,'uploads'), PORT=Number(process.env.PORT||8097), HOST=process.env.HOST||'127.0.0.1';
const MAX_BODY=23*1024*1024;
fs.mkdirSync(UPLOADS,{recursive:true});
const db=new DatabaseSync(path.join(DATA,'rw10plus.sqlite'));
db.exec(`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','editor','warga')),display_name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,csrf TEXT NOT NULL,expires INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS content(kind TEXT NOT NULL,id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'published',updated_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_by TEXT,PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,kind TEXT NOT NULL,subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'baru',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,action TEXT NOT NULL,target TEXT,at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS requests_user ON requests(user_id);`);
if(!db.prepare(`PRAGMA table_info(users)`).all().some(c=>c.name==='active')) db.exec('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1');
const KINDS=new Set(['articles','events','programs','shops','gallery']);
const ID=()=>crypto.randomUUID();
const randomString=(size=32)=>crypto.randomBytes(size).toString('base64url');
function hashPass(pass,salt=randomString(16)){return salt+':'+crypto.scryptSync(pass,salt,64).toString('hex')}
function verifyPass(pass,stored){try{let [salt,expected]=stored.split(':'),result=crypto.scryptSync(pass,salt,64);return crypto.timingSafeEqual(result,Buffer.from(expected,'hex'))}catch{return false}}
function audit(u,action,target){db.prepare('INSERT INTO audit(user_id,action,target) VALUES(?,?,?)').run(u||null,action,target||'')}
if(!db.prepare('SELECT id FROM users LIMIT 1').get()){
 let password=process.env.ADMIN_PASSWORD||randomString(15),username=process.env.ADMIN_USER||'admin';
 if(password.length<12)throw Error('ADMIN_PASSWORD minimal 12 karakter');
 db.prepare('INSERT INTO users(id,username,password_hash,role,display_name) VALUES(?,?,?,?,?)').run(ID(),username,hashPass(password),'admin','Administrator RW10+');
 let cred=path.join(DATA,'AKUN-ADMIN-PERTAMA.txt');fs.writeFileSync(cred,`RW10+ - AKUN ADMIN AWAL\nURL: http://127.0.0.1:${PORT}/#/admin\nUsername: ${username}\nPassword: ${password}\n\nGANTI PASSWORD INI SETELAH LOGIN. Hapus file ini setelah disimpan dengan aman.\n`,{mode:0o600});
 console.log('\nAKUN PERTAMA DIBUAT. Lihat: '+cred+'\n');
}
const preparedGet=db.prepare('SELECT payload,status FROM content WHERE kind=? AND id=?');
if(!db.prepare('SELECT kind FROM content LIMIT 1').get()){
 const seed={
 articles:[{id:'profil-rw10',title:'RW10+ — Ruang Informasi untuk Warga',category:'Informasi',date:'',description:'Satu ruang untuk mengikuti kabar, agenda, program, dan layanan lingkungan.',body:'RW10+ hadir untuk memudahkan penyampaian informasi di lingkungan RW 10 Desa Cicadas. Pengembangan dimulai dari RT 04, Gg H Kape.\n\nInformasi kegiatan resmi hanya diterbitkan setelah diverifikasi pengurus.',image:'assets/gapura-gg-kape.webp',featured:true,demo:false},{id:'contoh-pengumuman',title:'Contoh Pengumuman Kerja Bakti',category:'Pengumuman',date:'',description:'Contoh format pengumuman. Jadwal kegiatan belum ditetapkan.',body:'Ini adalah contoh konten awal. Pengurus dapat mengedit atau menghapusnya melalui Control Center.',place:'RT 04 · menunggu konfirmasi',image:'assets/kerja-bakti-ilustrasi.svg',demo:true}],
 events:[{id:'contoh-agenda',title:'Contoh Agenda Lingkungan',category:'Lingkungan',date:'',time:'',place:'Belum ditentukan',description:'Contoh agenda; belum ada jadwal resmi.',body:'Buat kegiatan baru melalui Control Center untuk menampilkan agenda sebenarnya.',demo:true}],
 programs:[{id:'program-wifi',title:'WiFi Gratis Pelajar',category:'Pendidikan',status:'Persiapan integrasi',description:'Program dukungan koneksi internet bagi pelajar.',body:'Aktivasi jaringan melalui CasaOS/INKAMNET belum dihubungkan.',image:'assets/program-wifi.svg'},{id:'program-cctv',title:'CCTV Lingkungan',category:'Keamanan',status:'Persiapan integrasi',description:'Dukungan sistem pengawasan lingkungan dengan akses terbatas.',body:'Siaran kamera tidak tersedia untuk publik dan belum terhubung.',image:'assets/program-cctv.svg'},{id:'program-pokja',title:'POKJA 10 — Ruang Kolaborasi',category:'Komunitas',status:'Pengembangan',description:'Ruang kontribusi dan kegiatan pemuda RW 10.',body:'POKJA 10 dipimpin Dea Erlangga.',image:'assets/program-pokja.svg'}],
 shops:[{id:'contoh-usaha',title:'Contoh Profil UMKM',category:'Kuliner',description:'Listing contoh. Belum ada usaha yang diverifikasi.',address:'Wilayah RW 10 (contoh)',hours:'Belum tersedia',whatsapp:'',image:'assets/umkm-pasar-ilustrasi.svg',demo:true}],
 gallery:[{id:'gapura-gg-kape',title:'Gapura Gg H Kape',category:'Lingkungan',image:'assets/gapura-gg-kape.webp',demo:false}]
 };
 const insert=db.prepare('INSERT INTO content(kind,id,payload,status) VALUES(?,?,?,?)');
 for(const [kind,items] of Object.entries(seed))for(let obj of items)insert.run(kind,obj.id,JSON.stringify(obj),'published');
}
// Limit login brute force attempts per address.
const attempts=new Map();
function json(res,status,obj,extra={}){let output=JSON.stringify(obj);res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...extra});res.end(output)}
function cookieValue(req,key){return (req.headers.cookie||'').split(';').map(v=>v.trim()).find(v=>v.startsWith(key+'='))?.slice(key.length+1)||''}
function me(req){let tok=cookieValue(req,'rw10sid');if(!tok)return null;let r=db.prepare(`SELECT users.id,username,role,display_name,active,csrf,expires FROM sessions JOIN users ON sessions.user_id=users.id WHERE token_hash=?`).get(crypto.createHash('sha256').update(tok).digest('hex'));return r&&r.active&&r.expires>Date.now()?r:null}
const allow=(u,mode)=>mode==='edit'?Boolean(u&&['admin','editor'].includes(u.role)):mode==='admin'?u?.role==='admin':Boolean(u);
function secureMutation(req,u){let origin=req.headers.origin;let host=req.headers.host;if(origin){let originURL;try{originURL=new URL(origin)}catch{return false}if(originURL.host!==host)return false}return Boolean(u&&req.headers['x-csrf-token']===u.csrf)}
async function bytes(req,limit=MAX_BODY){return await new Promise((resolve,reject)=>{const chunks=[];let total=0;req.on('data',c=>{total+=c.length;if(total>limit){reject(Object.assign(new Error('Data melebihi batas unggahan'),{status:413}));req.destroy();return}chunks.push(c)});req.on('end',()=>resolve(Buffer.concat(chunks)));req.on('error',reject)})}
async function bodyJSON(req){let buf=await bytes(req,250*1024);try{return JSON.parse(buf.toString('utf8')||'{}')}catch{throw Object.assign(new Error('JSON tidak valid'),{status:400})}}
function string(s,max=255){return String(s??'').trim().slice(0,max)}
function validated(kind,input,existing){if(!input||typeof input!=='object'||Array.isArray(input))throw Object.assign(new Error('Format konten tidak valid'),{status:400});
 const fields={articles:['title','category','date','description','body','place','image','featured','demo'],events:['title','category','date','time','place','description','body','image','demo'],programs:['title','category','status','description','body','image','demo'],shops:['title','category','description','address','hours','whatsapp','image','demo'],gallery:['title','category','image','demo']};
 const lengths={title:140,category:60,date:12,time:10,description:800,body:15000,place:200,status:80,address:200,hours:100,whatsapp:25,image:300};
 let result={...existing};for(const key of fields[kind]){if(!(key in input))continue;if(['featured','demo'].includes(key)){result[key]=key==='featured'?Boolean(input[key]):Boolean(input[key])}else result[key]=string(input[key],lengths[key])}
 if(!result.title||result.title.length<3)throw Object.assign(new Error('Judul minimal 3 karakter'),{status:400});
 if(result.image&&!/^(assets\/[\w.\-]+\.(webp|svg|jpg|jpeg|png)|\/uploads\/[0-9a-f\-]+\.(webp|jpg|png))$/i.test(result.image))throw Object.assign(new Error('Format alamat gambar tidak diizinkan'),{status:400});
 if(result.whatsapp&&!/^\+?[0-9\s\-]{8,25}$/.test(result.whatsapp))throw Object.assign(new Error('Nomor WhatsApp tidak valid'),{status:400});
 return result}
function listContents(publicOnly){let rows=db.prepare(publicOnly?`SELECT kind,payload FROM content WHERE status='published' ORDER BY updated_at DESC,rowid DESC`:`SELECT kind,payload,status FROM content ORDER BY updated_at DESC,rowid DESC`).all(),items={articles:[],events:[],programs:[],shops:[],gallery:[]};for(let r of rows){let record=JSON.parse(r.payload);if(!publicOnly)record._status=r.status;items[r.kind]?.push(record)}return items}
function removeOrphanUpload(img){
 if(!/^\/uploads\/[0-9a-f\-]+\.(webp|jpg|png)$/i.test(img||''))return;
 const used=db.prepare('SELECT payload FROM content').all().some(r=>{try{return JSON.parse(r.payload).image===img}catch{return false}});
 if(!used){try{fs.unlinkSync(path.join(UPLOADS,path.basename(img)))}catch(e){if(e.code!=='ENOENT')console.warn('Upload belum dapat dibersihkan',e.message)}}
}
function fileType(buffer){if(buffer.length>=4&&buffer.subarray(0,3).toString('hex')==='ffd8ff')return 'jpg';if(buffer.length>=8&&buffer.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex')))return 'png';if(buffer.length>=12&&buffer.subarray(0,4).toString()==='RIFF'&&buffer.subarray(8,12).toString()==='WEBP')return 'webp';return null}
async function api(req,res,url){const route=url.pathname,u=me(req),method=req.method;
 if(method==='GET'&&route==='/api/public')return json(res,200,{items:listContents(true)});
 if(method==='GET'&&route==='/api/me')return json(res,200,{user:u?{id:u.id,username:u.username,role:u.role,display_name:u.display_name}:null,csrf:u?.csrf||null});
 if(method==='POST'&&route==='/api/login'){
  let addr=req.socket.remoteAddress||'unknown';let recent=(attempts.get(addr)||[]).filter(t=>Date.now()-t<15*60*1000);if(recent.length>=8)return json(res,429,{error:'Terlalu banyak percobaan. Coba lagi dalam 15 menit.'});
  let body=await bodyJSON(req),name=string(body.username,70),p=String(body.password||'');let user=db.prepare('SELECT * FROM users WHERE username=?').get(name);if(!user||!user.active||!verifyPass(p,user.password_hash)){recent.push(Date.now());attempts.set(addr,recent);return json(res,401,{error:'Nama pengguna atau kata sandi salah.'})}
  attempts.delete(addr);let tok=randomString(32),csrf=randomString(24),duration=8*60*60*1000;
  db.prepare('INSERT INTO sessions(token_hash,user_id,csrf,expires) VALUES(?,?,?,?)').run(crypto.createHash('sha256').update(tok).digest('hex'),user.id,csrf,Date.now()+duration);
  audit(user.id,'login','portal');return json(res,200,{user:{id:user.id,username:user.username,role:user.role,display_name:user.display_name},csrf},{'Set-Cookie':`rw10sid=${tok}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800${process.env.COOKIE_SECURE==='true'?'; Secure':''}`})
 }
 if(method==='POST'&&route==='/api/logout'){if(!secureMutation(req,u))return json(res,403,{error:'Sesi atau token tidak valid'});db.prepare('DELETE FROM sessions WHERE user_id=?').run(u.id);return json(res,200,{ok:true},{'Set-Cookie':'rw10sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})}
 if(method==='POST'&&route==='/api/change-password'){if(!secureMutation(req,u))return json(res,403,{error:'Tidak diizinkan'});const b=await bodyJSON(req),record=db.prepare('SELECT password_hash FROM users WHERE id=?').get(u.id);if(!verifyPass(String(b.old_password||''),record.password_hash))return json(res,403,{error:'Kata sandi lama salah'});if(String(b.new_password||'').length<12)return json(res,400,{error:'Kata sandi baru minimal 12 karakter'});db.prepare('UPDATE users SET password_hash=? WHERE id=?').run(hashPass(String(b.new_password)),u.id);db.prepare('DELETE FROM sessions WHERE user_id=?').run(u.id);audit(u.id,'change-password','account');return json(res,200,{ok:true},{'Set-Cookie':'rw10sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})}
 if(method==='GET'&&route==='/api/manage'){if(!allow(u,'edit'))return json(res,403,{error:'Akses pengelolaan hanya untuk pengurus'});return json(res,200,{items:listContents(false)})}
 if(route==='/api/upload'&&method==='POST'){
  if(!allow(u,'edit')||!secureMutation(req,u))return json(res,403,{error:'Akses tidak diizinkan'});
  let raw=await bytes(req,22*1024*1024), request=new Request('http://localhost/upload',{method:'POST',headers:{'content-type':req.headers['content-type']||''},body:raw}),form=await request.formData(),file=form.get('image');if(!file||typeof file.arrayBuffer!=='function')return json(res,400,{error:'File gambar tidak ditemukan'});let buf=Buffer.from(await file.arrayBuffer());if(buf.length>20*1024*1024)return json(res,413,{error:'Ukuran gambar maksimal 20 MB'});let ext=fileType(buf);if(!ext)return json(res,415,{error:'Hanya JPG, PNG, WEBP asli yang diperbolehkan'});let name=ID()+'.'+ext;fs.writeFileSync(path.join(UPLOADS,name),buf,{flag:'wx',mode:0o644});audit(u.id,'upload',name);return json(res,201,{url:'/uploads/'+name,size:buf.length})
 }
 const contentRoute=route.match(/^\/api\/manage\/(articles|events|programs|shops|gallery)(?:\/([a-zA-Z0-9\-]+))?$/);
 if(contentRoute&&['POST','PUT','DELETE'].includes(method)){
  if(!allow(u,'edit')||!secureMutation(req,u))return json(res,403,{error:'Tidak diizinkan'});let [,kind,id]=contentRoute;
  if(method==='DELETE'){if(!id)return json(res,400,{error:'ID diperlukan'});const old=preparedGet.get(kind,id);let r=db.prepare('DELETE FROM content WHERE kind=? AND id=?').run(kind,id);if(old)removeOrphanUpload(JSON.parse(old.payload).image);audit(u.id,'delete',kind+'/'+id);return json(res,r.changes?200:404,{ok:!!r.changes})}
  let previous=id?preparedGet.get(kind,id):null;if(method==='PUT'&&!previous)return json(res,404,{error:'Konten tidak ditemukan'});let input=await bodyJSON(req),payload=validated(kind,input,previous?JSON.parse(previous.payload):{});id=id||ID();payload.id=id;
  let status=input._status==='draft'?'draft':'published';if(input.demo===undefined&&!previous)payload.demo=false;
  if(method==='POST')db.prepare(`INSERT INTO content(kind,id,payload,status,updated_by,updated_at) VALUES(?,?,?,?,?,STRFTIME('%Y-%m-%d %H:%M:%f','now'))`).run(kind,id,JSON.stringify(payload),status,u.id);
  else db.prepare(`UPDATE content SET payload=?,status=?,updated_at=STRFTIME('%Y-%m-%d %H:%M:%f','now'),updated_by=? WHERE kind=? AND id=?`).run(JSON.stringify(payload),status,u.id,kind,id);
  if(method==='PUT'&&previous){let oldImage=JSON.parse(previous.payload).image;if(oldImage!==payload.image)removeOrphanUpload(oldImage)}
  audit(u.id,method==='POST'?'create':'update',kind+'/'+id);return json(res,200,{item:{...payload,_status:status}})
 }
 if(route==='/api/users'&&method==='GET'){if(!allow(u,'admin'))return json(res,403,{error:'Admin saja'});return json(res,200,{users:db.prepare('SELECT id,username,role,display_name,active,created_at FROM users ORDER BY created_at DESC').all()})}
 if(route==='/api/users'&&method==='POST'){
  if(!allow(u,'admin')||!secureMutation(req,u))return json(res,403,{error:'Admin saja'});let b=await bodyJSON(req),name=string(b.username,50),display=string(b.display_name,100),role=string(b.role,20);if(!/^[a-zA-Z0-9._-]{3,50}$/.test(name)||!['warga','editor'].includes(role))return json(res,400,{error:'Username atau role tidak valid'});if(db.prepare('SELECT id FROM users WHERE username=?').get(name))return json(res,409,{error:'Username sudah dipakai'});let pwd=String(b.password||randomString(12));if(pwd.length<12)return json(res,400,{error:'Password minimal 12 karakter'});let id=ID();db.prepare('INSERT INTO users(id,username,password_hash,role,display_name) VALUES(?,?,?,?,?)').run(id,name,hashPass(pwd),role,display||name);audit(u.id,'create-user',name);return json(res,201,{user:{id,username:name,role,display_name:display||name},initial_password:b.password?null:pwd})
 }
 const usersAction=route.match(/^\/api\/users\/([a-zA-Z0-9\-]+)\/(reset-password|toggle-active)$/);
 if(usersAction&&method==='POST'){
  if(!allow(u,'admin')||!secureMutation(req,u))return json(res,403,{error:'Hanya administrator'});
  const target=db.prepare('SELECT id,role,active,username FROM users WHERE id=?').get(usersAction[1]);if(!target)return json(res,404,{error:'Akun tidak ditemukan'});
  if(target.id===u.id)return json(res,400,{error:'Ubah password akun sendiri melalui menu Ubah Kata Sandi'});
  if(usersAction[2]==='reset-password'){const password=randomString(15);db.prepare('UPDATE users SET password_hash=? WHERE id=?').run(hashPass(password),target.id);db.prepare('DELETE FROM sessions WHERE user_id=?').run(target.id);audit(u.id,'reset-password',target.username);return json(res,200,{password})}
  db.prepare('UPDATE users SET active=? WHERE id=?').run(target.active?0:1,target.id);db.prepare('DELETE FROM sessions WHERE user_id=?').run(target.id);audit(u.id,target.active?'disable-user':'enable-user',target.username);return json(res,200,{active:!target.active})
 }
 if(route==='/api/requests'&&method==='GET'){
  if(!u)return json(res,401,{error:'Silakan masuk terlebih dahulu'});let rows=allow(u,'edit')?db.prepare('SELECT r.*,users.display_name,users.username FROM requests r JOIN users ON users.id=r.user_id ORDER BY r.created_at DESC').all():db.prepare('SELECT id,kind,subject,message,status,created_at,updated_at FROM requests WHERE user_id=? ORDER BY created_at DESC').all(u.id);return json(res,200,{requests:rows})
 }
 if(route==='/api/requests'&&method==='POST'){
  if(!secureMutation(req,u))return json(res,403,{error:'Masuk ke Ruang Warga terlebih dahulu'});let b=await bodyJSON(req),kind=string(b.kind,32),subject=string(b.subject,120),msg=string(b.message,3000);if(!['pengaduan','aspirasi','wifi','layanan'].includes(kind)||subject.length<4||msg.length<10)return json(res,400,{error:'Isi kategori, judul dan pesan minimal 10 karakter'});let id=ID();db.prepare('INSERT INTO requests(id,user_id,kind,subject,message) VALUES(?,?,?,?,?)').run(id,u.id,kind,subject,msg);audit(u.id,'request',kind+'/'+id);return json(res,201,{ok:true,id})
 }
 let statusRoute=route.match(/^\/api\/requests\/([a-z0-9\-]+)$/);
 if(statusRoute&&method==='PATCH'){
  if(!allow(u,'edit')||!secureMutation(req,u))return json(res,403,{error:'Pengurus saja'});let b=await bodyJSON(req);if(!['baru','diproses','selesai','ditolak'].includes(b.status))return json(res,400,{error:'Status tidak valid'});let upd=db.prepare('UPDATE requests SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?').run(b.status,statusRoute[1]);audit(u.id,'request-status',statusRoute[1]);return json(res,upd.changes?200:404,{ok:!!upd.changes})
 }
 return json(res,404,{error:'Endpoint tidak ditemukan'})
}
const MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.ico':'image/x-icon'};
function staticFile(req,res,url){let raw=decodeURIComponent(url.pathname);if(raw==='/'||raw==='')raw='/index.html';if(raw.includes('\0')||raw.split('/').includes('..')||raw.startsWith('/data/')||raw.startsWith('/server')||raw.endsWith('.db')||raw.endsWith('.sqlite')){res.writeHead(403);return res.end('Forbidden')}
 let base=raw.startsWith('/uploads/')?UPLOADS:ROOT,file=path.resolve(base,raw.startsWith('/uploads/')?'.'+raw.slice('/uploads'.length):'.'+raw);if(!file.startsWith(base+path.sep)&&file!==base){res.writeHead(403);return res.end('Forbidden')}let stat;try{stat=fs.statSync(file)}catch{res.writeHead(404);return res.end('Not found')}if(!stat.isFile()){res.writeHead(404);return res.end('Not found')}
 let ext=path.extname(file).toLowerCase();if(!MIME[ext]){res.writeHead(403);return res.end('Forbidden')}
 res.writeHead(200,{'Content-Type':MIME[ext],'X-Content-Type-Options':'nosniff','Cache-Control':raw.startsWith('/uploads/')?'public, max-age=3600':'no-cache','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",'Referrer-Policy':'strict-origin-when-cross-origin','X-Frame-Options':'DENY'});if(req.method==='HEAD')return res.end();fs.createReadStream(file).pipe(res)}
const server=http.createServer(async(req,res)=>{try{let url=new URL(req.url,`http://${req.headers.host||'127.0.0.1'}`);if(url.pathname.startsWith('/api/'))return await api(req,res,url);if(!['GET','HEAD'].includes(req.method))return json(res,405,{error:'Metode tidak tersedia'});return staticFile(req,res,url)}catch(e){console.error('[RW10+]',e.message);if(res.headersSent){res.end();return}return json(res,e.status||500,{error:e.status?e.message:'Terjadi kesalahan server'})}});
server.listen(PORT,HOST,()=>console.log(`RW10+ berjalan: http://${HOST}:${PORT}`));
