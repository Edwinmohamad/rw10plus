#!/usr/bin/env python3
"""Regression test: authenticated RT04 cannot read RT01 resources."""
import http.cookiejar
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PORT = 18189
BASE = f'http://127.0.0.1:{PORT}'
def req(client, path, method='GET', data=None):
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(BASE+path,body,method=method,headers={'Content-Type':'application/json'})
    try:
        with client.open(request,timeout=5) as response:
            return response.status,json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code,json.load(exc)
def login(phone,pin):
    c=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status,_=req(c,'/api/login','POST',{'phone':phone,'pin':pin});assert status==200
    return c
with tempfile.TemporaryDirectory() as folder:
    database=f'{folder}/rw10.db'
    env=dict(os.environ,RW10_DB_PATH=database,RW10_PORT=str(PORT))
    proc=subprocess.Popen(['python3',str(ROOT/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    try:
        for _ in range(180):
            try:
                with urllib.request.urlopen(BASE+'/api/health',timeout=.3):break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Server tidak siap')
        # Add RT04 resident, Ketua RT04 and a second resident in RT01.
        # No user-supplied RT is trusted by the API; all scopes use stored user.rt.
        import sys
        sys.path.insert(0,str(ROOT))
        from server import password_hash
        with sqlite3.connect(database) as db:
            for phone,name,rt,role in [('081299990004','Warga RT04','04','warga'),('081299998804','Ketua RT04','04','ketua_rt'),('081299990011','Warga Lain RT01','01','warga')]:
                db.execute('INSERT INTO users(phone,name,rt,house,role,pin_hash) VALUES(?,?,?,?,?,?)',(phone,name,rt,'Rumah Contoh',role,password_hash('9999')))
        warga04=login('081299990004','9999'); ketua04=login('081299998804','9999');warga01=login('081200000001','0101');rw=login('081200000010','1010')
        _,b04=req(warga04,'/api/bootstrap');_,k04=req(ketua04,'/api/bootstrap');_,rwdata=req(rw,'/api/bootstrap')
        assert b04['user']['rt']=='04' and k04['user']['rt']=='04'
        for payload in (b04,k04):
            for key in ('complaints','invoices','letters','guest_passes','market','cameras'):
                for item in payload[key]:
                    assert item.get('rt',item.get('reporter_rt','04'))=='04',(key,item)
        assert rwdata['market'] and any(c['rt']=='01' for c in rwdata['cameras'])
        _,guest=req(warga01,'/api/guest-passes','POST',{'guest_name':'Keluarga Tamu','purpose':'Berkunjung','duration_hours':2})
        assert req(ketua04,'/api/guest-passes/scan','POST',{'token':guest['token']})[0]==403
        assert req(rw,'/api/guest-passes/scan','POST',{'token':guest['token']})[0]==200
        _,comp=req(warga01,'/api/complaints','POST',{'title':'Masalah RT01','description':'Laporan wilayah berbeda','category':'Umum','location':'RT01'})
        assert req(ketua04,f"/api/complaints/{comp['id']}/transition",'POST',{'status':'Ditinjau'})[0]==403
        _,letter=req(warga01,'/api/letters','POST',{'letter_type':'Surat Domisili','purpose':'Keperluan kantor'})
        assert req(ketua04,f"/api/letters/{letter['id']}/decision",'POST',{'decision':'approve'})[0]==403
        assert any(c['rt']=='01' for c in req(rw,'/api/bootstrap')[1]['cameras'])
        print('RT ISOLATION PASS: RT04 scoped, RT01 cross-access rejected, RW admin global')
    finally:
        proc.terminate();proc.wait(timeout=5)
