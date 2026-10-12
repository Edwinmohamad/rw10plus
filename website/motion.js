(() => {
  'use strict';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const targets = [...document.querySelectorAll('.content-section, .services-wrap, .wifi-feature, .rt-quick, .rt-data-section, .hero-copy, .rt-hero-copy')];
  const nav = document.getElementById('nav');
  const menu = document.querySelector('.menu-toggle');
  const close = () => {nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false');if(menu) menu.textContent='☰';};
  document.addEventListener('click', e => {if(nav?.classList.contains('open') && !nav.contains(e.target) && !menu?.contains(e.target))close();});
  addEventListener('resize', () => {if(innerWidth>800)close();});
  if(!reduced && 'IntersectionObserver' in window){
    targets.forEach(el=>el.setAttribute('data-motion-reveal',''));
    document.body.classList.add('motion-enabled');
    const observer = new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}}},{threshold:.04,rootMargin:'0px 0px 60px 0px'});
    targets.forEach(el=>observer.observe(el));
  }
  // Make active section visible in the navbar as users scroll the public homepage.
  if(location.pathname.endsWith('rt.html'))return;
  const links=[...document.querySelectorAll('#nav a[href^="#"]')];
  const sections=links.map(a=>({link:a,section:document.querySelector(a.getAttribute('href'))})).filter(item=>item.section);
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(!visible)return;for(const item of sections){const active=item.section===visible.target;item.link.classList.toggle('active',active);if(active)item.link.setAttribute('aria-current','location');else item.link.removeAttribute('aria-current');}},{rootMargin:'-15% 0px -68% 0px',threshold:0});
    sections.forEach(item=>observer.observe(item.section));
  }
})();
