const CACHE='cicadas-digital-v12';
const ASSETS=['/','/styles.css?v=12.0.0','/desa-digital.css?v=12.0.0','/apk-apple.css?v=12.0.0','/app.js?v=12.0.0','/manifest.webmanifest?v=12.0.0','/icon.svg','/icon-192.png','/icon-512.png','/app-hero.webp','/app-rt04.webp','/app-news-1.webp','/app-news-2.webp','/app-news-3.webp','/kabupaten-bogor-fallback.svg'];
self.addEventListener('install',event=>event.waitUntil(
  caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())
));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET'||new URL(event.request.url).pathname.startsWith('/api/'))return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('/'))));
});
