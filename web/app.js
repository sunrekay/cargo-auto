// Catalogue and brands are loaded from the backend at boot (see boot() below).
let cars=[];

let saved;try{saved=new Set(JSON.parse(localStorage.getItem('potok-saved')||'[]'))}catch{saved=new Set()}
let filter='all',view='all';let criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};function matches(c,q){return(q.brand==='all'||c.brand===q.brand)&&(q.model==='all'||c.model===q.model)&&(q.budget==='all'||c.price<=Number(q.budget))&&(q.fuel==='all'||c.type===q.fuel)&&(q.body==='all'||c.body===q.body)}const feed=document.querySelector('#feed');let currency='USD';const priceNote=()=>currency==='RUB'
  ?'С доставкой в РФ · оценка по курсу':'Цена в Китае · источник Guazi';const money=n=>n==null?'—':(currency==='RUB'
  ?new Intl.NumberFormat('ru-RU').format(n)+' ₽'
  :'$'+new Intl.NumberFormat('en-US').format(n));
function notify(t){const el=document.querySelector('#toast');el.textContent=t;el.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.classList.remove('show'),2200)}
function render(){document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.filter===filter)));document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.view===view)));const list=cars.filter(c=>(view==='all'||saved.has(c.id))&&matches(c,criteria));document.querySelector('#saved-count').textContent=saved.size;
feed.innerHTML=list.length?list.map(c=>`<article class="car" data-id="${c.id}"><div class="visual" style="--car-image:url('${c.image}')"><img src="${c.image}" alt="${c.name}, внешний вид" draggable="false"><div class="badges"><span class="badge">${c.fuel}</span><span class="badge dark">CN${c.body_label?' · '+c.body_label:''}</span></div><span class="photo-label">Фото модели</span><button class="expand-photo" data-photo="${c.id}" aria-label="Открыть фото ${c.name} целиком"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg></button></div><div class="car-body"><div class="title-row"><div><h3>${c.name}</h3><p class="sub">${c.trim}</p></div><button class="save ${saved.has(c.id)?'is-saved':''}" aria-label="${saved.has(c.id)?'Удалить из избранного':'Сохранить '+c.name}" aria-pressed="${saved.has(c.id)}" data-save="${c.id}">${saved.has(c.id)?'♥':'♡'}</button></div><ul class="specs"><li><b>${c.year}</b><span>Год</span></li><li><b>${c.km}</b><span>Пробег</span></li><li><b>${c.power}</b><span>Мощность</span></li><li><b>${c.fuel}</b><span>Двигатель</span></li></ul><div class="price-row"><div><div class="price">${money(c.price)}</div><div class="price-note">${priceNote()}</div></div><button class="primary" data-detail="${c.id}">Подробнее</button></div></div></article>`).join(''):'<div class="empty"><h2>Пока ни одной машины</h2><p>Сохраните понравившийся автомобиль или выберите другой фильтр.</p><button class="primary" id="reset">Вернуться к ленте</button></div>';
feed.scrollTop=0;updateCount();updateFilters();}
function updateCount(){const items=[...feed.querySelectorAll('.car')];const i=items.length?Math.round(feed.scrollTop/(items[0].offsetHeight+16))+1:0;document.querySelector('#feed-count').textContent=String(Math.min(i,items.length)).padStart(2,'0')+' / '+String(items.length).padStart(2,'0')}
feed.addEventListener('scroll',updateCount,{passive:true});
document.addEventListener('click',e=>{const photo=e.target.closest('[data-photo]')|| (e.target.matches('.visual img')?e.target.closest('.car'):null);if(photo){const c=cars.find(c=>c.id===(photo.dataset.photo||photo.dataset.id));document.querySelector('#photo-image').src=c.image;document.querySelector('#photo-image').alt=c.name;document.querySelector('#photo-caption').textContent=c.name+' · Фото модели';document.querySelector('#photo-dialog').showModal();}const s=e.target.closest('[data-save]'),d=e.target.closest('[data-detail]'),f=e.target.closest('[data-filter]'),v=e.target.closest('[data-view]');if(s){const id=s.dataset.save;saved.has(id)?saved.delete(id):saved.add(id);try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}const y=feed.scrollTop;render();feed.scrollTop=y;feed.querySelector(`[data-save="${id}"]`)?.focus({preventScroll:true});notify(saved.has(id)?'Автомобиль в избранном':'Автомобиль удалён из избранного')}
if(f){filter=f.dataset.filter;document.querySelectorAll('.chip').forEach(x=>(x.classList.toggle('selected',x===f),x.setAttribute('aria-pressed',String(x===f))));render()}
if(v){view=v.dataset.view;document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x===v));render()}
if(d){openDetail(d.dataset.detail)}
if(e.target.closest('.close'))e.target.closest('dialog').close();if(e.target.id==='reset'){filter='all';view='all';criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('selected',x.dataset.filter==='all'));document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view==='all'));render()}});
document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]')||!['ArrowDown','ArrowUp'].includes(e.key))return;e.preventDefault();const card=feed.querySelector('.car');if(card)feed.scrollBy({top:(card.offsetHeight+16)*(e.key==='ArrowDown'?1:-1),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})});
const filterDialog=document.querySelector('#filters-dialog'),form=document.querySelector('#filter-form');
function draft(){return {...criteria,...Object.fromEntries(new FormData(form))}}
function updateFilters(){const count=Object.values(criteria).filter(v=>v!=='all').length;const badge=document.querySelector('#filter-count');badge.hidden=!count;badge.textContent=count;document.querySelector('#clear-filters').hidden=!count;document.querySelector('#brand-trigger').innerHTML=(criteria.brand==='all'?'Марка':(brandNames[criteria.brand]||criteria.brand))+' <span>⌄</span>';document.querySelector('#model-trigger').innerHTML=(criteria.model==='all'?'Модель':(modelNames[criteria.model]||criteria.model))+' <span>⌄</span>';}

let brands=[];let modelNames={};let brandNames={};
let pickerStep='brands';
function setStep(step){if(step==='models'&&form.elements.brand.value==='all')step='brands';pickerStep=step;document.querySelector('#brand-panel').hidden=step!=='brands';document.querySelector('#model-panel').hidden=step!=='models';document.querySelectorAll('[data-step]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.step===step)));document.querySelector('#filters-title').textContent=step==='brands'?'С чего начнём?':'Найдите свою модель';}
function renderPicker(){
 const q=draft(),search=document.querySelector('#brand-search').value.trim().toLowerCase();
 const list=brands.filter(b=>b.name.toLowerCase().includes(search));
 document.querySelector('#brand-grid').innerHTML=list.length?list.map(b=>{const b_initial=(b.name||'?')[0];return `<button type="button" class="brand-tile ${q.brand===b.id?'chosen':''}" data-brand="${b.id}" aria-pressed="${q.brand===b.id}"><img src="assets/${b.id}-logo.svg" alt="" data-initial="${b_initial}"><strong>${b.name}</strong><span>${cars.filter(c=>c.brand===b.id).length} авто</span><i aria-hidden="true">${q.brand===b.id?'✓':'↗'}</i></button>`}).join(''):'<p class="picker-note">Такой марки нет в подборке.</p>';
// Only a few makes ship a logo file; the rest fall back to the make's initial.
document.querySelectorAll('#brand-grid img').forEach(img=>{
  const swap=()=>{const b=document.createElement('span');
    b.className='brand-initial';b.textContent=img.dataset.initial||'?';img.replaceWith(b);};
  img.addEventListener('error',swap,{once:true});
  if(img.complete&&img.naturalWidth===0)swap();
});
 const offers=cars.filter(c=>c.brand===q.brand);const models=[...new Set(offers.map(c=>c.model))].map(m=>offers.filter(c=>c.model===m).sort((a,b)=>a.price-b.price)[0]);
 document.querySelector('#models-heading').textContent=q.brand==='all'?'Все модели':brands.find(b=>b.id===q.brand).name;
 document.querySelector('#model-grid').innerHTML=models.map(c=>`<button type="button" class="model-tile ${q.model===c.model?'chosen':''}" data-model="${c.model}" aria-pressed="${q.model===c.model}"><div class="model-photo"><img src="${c.image}" alt="${c.name}"><span class="model-check" aria-hidden="true">${q.model===c.model?'✓':'+'}</span></div><div class="model-info"><strong>${c.name}</strong><span>${c.fuel} · ${c.year}</span><b>от ${money(c.price)}</b><small>${priceNote()}</small></div></button>`).join('');
 draftCount();
}
function draftCount(){const q=draft(),n=cars.filter(c=>(view==='all'||saved.has(c.id))&&matches(c,q)).length;document.querySelector('#apply-filters').textContent='Показать · '+n;const preview=document.querySelector('#selected-preview'),c=cars.find(c=>c.model===q.model&&c.brand===q.brand);preview.hidden=!c;if(c)preview.innerHTML=`<img src="${c.image}" alt=""><div><strong>${c.name}</strong><span>${c.fuel} · ${c.year}</span></div><span class="selection-check">✓</span>`;}
document.querySelectorAll('[data-open-filter]').forEach(b=>b.addEventListener('click',()=>{for(const [k,v] of Object.entries(criteria))form.elements[k].value=v;document.querySelector('#brand-search').value='';document.querySelector('#technical-filters').open=b.dataset.openFilter==='fuel';setStep(b.dataset.openFilter==='brand'?'brands':'models');renderPicker();filterDialog.showModal();}));
form.addEventListener('click',e=>{const brand=e.target.closest('[data-brand]'),model=e.target.closest('[data-model]'),step=e.target.closest('[data-step]');if(brand){form.elements.brand.value=brand.dataset.brand;form.elements.model.value='all';setStep('models');renderPicker();document.querySelector('[data-step="models"]').focus();}if(model){form.elements.model.value=form.elements.model.value===model.dataset.model?'all':model.dataset.model;renderPicker();document.querySelector(`[data-model="${model.dataset.model}"]`).focus({preventScroll:true});}if(step)setStep(step.dataset.step);});
document.querySelector('#brand-search').addEventListener('input',renderPicker);
document.querySelector('#all-brands').addEventListener('click',()=>{form.elements.brand.value='all';form.elements.model.value='all';setStep('brands');renderPicker();});
document.querySelector('#all-models').addEventListener('click',()=>{form.elements.model.value='all';renderPicker();});
form.addEventListener('change',draftCount);form.addEventListener('submit',e=>{e.preventDefault();criteria=draft();filterDialog.close();render()});
document.querySelector('#reset-draft').addEventListener('click',()=>{form.reset();form.elements.brand.value='all';form.elements.model.value='all';document.querySelector('#brand-search').value='';setStep('brands');renderPicker()});
document.querySelector('#clear-filters').addEventListener('click',()=>{criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};render()});

// ---------------------------------------------------------------------------
// Catalogue loading
//
// The storefront is served by the same origin as the API, so a relative path
// works in production; API_BASE lets the page be opened against a remote API
// while developing.
const API=(window.API_BASE||'').replace(/\/$/,'');
const api=path=>fetch(API+path,{headers:{Accept:'application/json'}}).then(r=>{
  if(!r.ok)throw new Error(path+' -> '+r.status);return r.json();});

function fillSelect(name,options,anyLabel){
  const el=form.elements[name];if(!el)return;
  const keep=el.value;
  el.innerHTML=`<option value="all">${anyLabel}</option>`+
    options.map(o=>`<option value="${o.value}">${o.label}</option>`).join('');
  if([...el.options].some(o=>o.value===keep))el.value=keep;
}

// Budget steps are derived from the real price range rather than fixed rungs,
// so the options always bracket the catalogue actually on offer.
function budgetSteps(min,max){
  if(min==null||max==null||max<=min)return [];
  const steps=[];for(let i=1;i<=3;i++){
    const raw=min+(max-min)*i/3;
    const mag=Math.pow(10,Math.floor(Math.log10(raw)));
    steps.push(Math.ceil(raw/(mag/2))*(mag/2));
  }
  return [...new Set(steps)];
}

function setNote(sel,text){const el=document.querySelector(sel);if(el)el.textContent=text;}

// The detail dialog pulls the complete record: every characteristic the source
// page carried, which is far more than the feed card can show.
const SPEC_ORDER=['Mfg. Date','1st Reg. Date','Mileage (km)','Transmission','Engine',
  'Displacement (L)','Horsepower (ps)','Fuel Type','Drive Train','Body Style',
  'Number of Seats','Emission Standard','Grade','Inspection Status','VIN'];

async function openDetail(id){
  const box=document.querySelector('#detail-content');
  const c=cars.find(x=>x.id===id);
  box.innerHTML=`<span class="eyebrow">ЗНАКОМЬТЕСЬ БЛИЖЕ</span>
    <h2 id="detail-title">${c?c.name:''}</h2><p>Загружаем характеристики…</p>`;
  document.querySelector('#detail').showModal();
  try{
    const car=await api('/api/cars/'+encodeURIComponent(id));
    const byLabel=Object.fromEntries(car.specs.map(s=>[s.label,s.value]));
    const head=SPEC_ORDER.filter(l=>byLabel[l]).map(l=>
      `<div class="cost-line"><span>${l}</span><b>${byLabel[l]}</b></div>`).join('');
    const rest=car.specs.filter(s=>!SPEC_ORDER.includes(s.label));
    box.innerHTML=`<span class="eyebrow">ЗНАКОМЬТЕСЬ БЛИЖЕ</span>
      <h2 id="detail-title">${car.name}</h2>
      <p>${[car.trim,car.year&&car.year+' год',car.km,car.power,car.colour]
            .filter(Boolean).join(' · ')}</p>
      <div class="cost-line total"><span>Цена</span><span>${money(car.price??car.price_usd)}</span></div>
      <h3>Характеристики</h3>${head}
      <details><summary>Ещё ${rest.length} характеристик</summary>
        ${rest.map(s=>`<div class="cost-line"><span>${s.label}</span><b>${s.value}</b></div>`).join('')}
      </details>
      <h3>Фотографии · ${car.photos.length}</h3>
      <div class="detail-photos">${car.photos.slice(0,12).map(ph=>
        `<img src="${ph.url}" alt="${ph.alt||car.name}" loading="lazy">`).join('')}</div>
      <p><a href="${car.source_url}" target="_blank" rel="noopener">Исходное объявление на Guazi ↗</a></p>`;
  }catch(err){
    console.error(err);
    box.innerHTML+='<p>Не удалось загрузить характеристики.</p>';
  }
}

async function boot(){
  feed.innerHTML='<div class="empty"><h2>Загружаем подборку…</h2></div>';
  try{
    const [filters,brandList,page]=await Promise.all([
      api('/api/filters'),api('/api/brands'),api('/api/cars?limit=200&sort=newest')]);

    currency=filters.usd_rub_rate?'RUB':'USD';
    cars=page.items;
    if(currency==='USD')cars.forEach(c=>{c.price=c.price_usd;});
    brands=brandList.map(b=>({id:b.slug,name:b.name}));
    brandNames=Object.fromEntries(brandList.map(b=>[b.slug,b.name]));

    const models=await api('/api/models');
    modelNames=Object.fromEntries(models.map(m=>[m.slug,m.name]));

    const price=filters.usd_rub_rate
      ? {min:Math.round(filters.price_usd.min*filters.usd_rub_rate),
         max:Math.round(filters.price_usd.max*filters.usd_rub_rate)}
      : filters.price_usd;
    fillSelect('budget',budgetSteps(price.min,price.max)
      .map(v=>({value:v,label:'До '+money(v)})),'Без ограничений');
    fillSelect('fuel',filters.fuels.map(f=>({value:f.slug,label:`${f.name} · ${f.count}`})),'Любой');
    fillSelect('body',filters.bodies.map(b=>({value:b.slug,label:`${b.name} · ${b.count}`})),'Любой');

    setNote('#brand-panel .picker-note',
      `${filters.totals.cars} автомобилей · ${brandList.length} марок · данные Guazi`);
    setNote('#model-panel .picker-note','Фото и цены из каталога');

    render();
  }catch(err){
    console.error(err);
    feed.innerHTML='<div class="empty"><h2>Каталог недоступен</h2>'+
      '<p>Бэкенд не отвечает. Проверьте, что API запущен.</p></div>';
  }
}
boot();
