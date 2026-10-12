(() => {
  'use strict';
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const rtData = {
    '01': {name:'Wilayah RT 01', description:'Informasi publik RT01 RW10 Pabuaran. Dokumentasi wilayah akan ditampilkan setelah dikonfirmasi pengurus.', photo:'./assets/rt-public-placeholder.svg', alt:'Ilustrasi sementara untuk RT01'},
    '02': {name:'Wilayah RT 02', description:'Informasi publik RT02 RW10 Pabuaran. Dokumentasi wilayah akan ditampilkan setelah dikonfirmasi pengurus.', photo:'./assets/rt-public-placeholder.svg', alt:'Ilustrasi sementara untuk RT02'},
    '03': {name:'Wilayah RT 03', description:'Informasi publik RT03 RW10 Pabuaran. Dokumentasi wilayah akan ditampilkan setelah dikonfirmasi pengurus.', photo:'./assets/rt-public-placeholder.svg', alt:'Ilustrasi sementara untuk RT03'},
    '04': {name:'GG H Kape', description:'RT04 RW10 Pabuaran. Kenali profil lingkungan, pengurus, dan kegiatan yang sudah dipublikasikan.', photo:'./assets/rt04-gg-h-kape.webp', alt:'Ilustrasi gerbang GG H Kape RT04'}
  };
  const tabs = [...document.querySelectorAll('[data-choose-rt]')];
  const photo = document.querySelector('#preview-rt-photo');
  const name = document.querySelector('#preview-rt-name');
  const description = document.querySelector('#preview-rt-description');
  const kicker = document.querySelector('#preview-rt-kicker');
  const link = document.querySelector('#preview-rt-link');
  function choose(rt, focus = false) {
    const current = rtData[rt];
    if (!current || !photo || !name || !description || !kicker || !link) return;
    photo.src = current.photo; photo.alt = current.alt;
    name.textContent = current.name; description.textContent = current.description;
    kicker.textContent = `PROFIL WILAYAH RT ${rt}`;
    link.href = `./rt.html?rt=${rt}`; link.textContent = `Lihat Profil RT${rt} →`;
    tabs.forEach(tab => { const active = tab.dataset.chooseRt === rt; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; });
    if (focus) tabs.find(tab => tab.dataset.chooseRt === rt)?.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => choose(tab.dataset.chooseRt));
    tab.addEventListener('keydown', event => {
      const delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (!delta) return; event.preventDefault(); choose(tabs[(index + delta + tabs.length) % tabs.length].dataset.chooseRt, true);
    });
  });
  if (tabs.length) choose('04');
  const counter = document.querySelector('[data-count]');
  if (counter) {
    const run = () => {const n = Number(counter.dataset.count); if(!Number.isFinite(n) || n < 0)return;
      if (reduced) {counter.textContent = n.toLocaleString('id-ID');return;}
      const start = performance.now();const duration = 900;
      const tick = time => {const progress = Math.min((time-start)/duration,1);counter.textContent = Math.round(n*(1-Math.pow(1-progress,3))).toLocaleString('id-ID');if(progress<1)requestAnimationFrame(tick);}; requestAnimationFrame(tick);
    };
    if (!('IntersectionObserver' in window)) run(); else {
      const ob = new IntersectionObserver(entries => {if(entries.some(e => e.isIntersecting)){run();ob.disconnect();}}, {threshold:.35});ob.observe(counter);
    }
  }
  const gallery = document.querySelector('#galeri .photo-grid');
  if (gallery) {
    const dialog = document.createElement('dialog'); dialog.className = 'gallery-lightbox';
    dialog.innerHTML = '<button class="gallery-close" type="button" aria-label="Tutup gambar">✕</button><img alt=""><p></p>';
    document.body.appendChild(dialog);
    const display = dialog.querySelector('img'); const caption = dialog.querySelector('p');
    gallery.querySelectorAll('figure').forEach(figure => {
      const img = figure.querySelector('img'); if(!img)return;
      const button = document.createElement('button'); button.type='button'; button.className='gallery-open';button.setAttribute('aria-label', `Perbesar: ${img.alt}`);
      button.textContent='Lihat foto';figure.appendChild(button);
      button.addEventListener('click', () => {display.src=img.currentSrc || img.src;display.alt=img.alt;caption.textContent=figure.querySelector('figcaption')?.textContent || '';dialog.showModal();});
    });
    dialog.querySelector('.gallery-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {if(event.target === dialog) dialog.close();});
  }
})();
