// Catalogue and brands are loaded from the backend at boot (see boot() below).
let cars=[];

let saved;try{saved=new Set(JSON.parse(localStorage.getItem('potok-saved')||'[]'))}catch{saved=new Set()}
let filter='all',view='all';let criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};function matches(c,q){return(q.brand==='all'||c.brand===q.brand)&&(q.model==='all'||c.model===q.model)&&(q.budget==='all'||c.price<=Number(q.budget))&&(q.fuel==='all'||c.type===q.fuel)&&(q.body==='all'||c.body===q.body)}const feed=document.querySelector('#feed');let currency='USD';const priceNote=()=>currency==='RUB'
  ?'Цена в Китае · пересчёт по курсу':'Цена в Китае · источник Guazi';const money=n=>n==null?'—':(currency==='RUB'
  ?new Intl.NumberFormat('ru-RU').format(n)+' ₽'
  :'$'+new Intl.NumberFormat('en-US').format(n));
function notify(t){const el=document.querySelector('#toast');el.textContent=t;el.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.classList.remove('show'),2200)}
let activeIndex=0,history=[],suppressPhotoUntil=0;
const iconHeart='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 5.5c-2.4-2.4-6-1.5-8.5 1-2.5-2.5-6.1-3.4-8.5-1C.1 8.9 3.5 13.8 12 20c8.5-6.2 11.9-11.1 8.5-14.5Z"/></svg>';
function eligible(){return cars.filter(c=>view==='saved'?saved.has(c.id):matches(c,criteria));}
function persistSaved(){try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}}
function render(){
 const list=eligible();activeIndex=Math.max(0,Math.min(activeIndex,Math.max(0,list.length-1)));const c=list[activeIndex];
 document.querySelectorAll('[data-view]').forEach(x=>{const on=x.dataset.view===view;x.setAttribute('aria-pressed',String(on));x.classList.toggle('active',on)});
 document.querySelector('#saved-count').textContent=cars.filter(c=>saved.has(c.id)).length;
 document.querySelector('#view-title').textContent=view==='saved'?'Те самые.':'Найдите свою.';
 document.querySelector('#feed-count').textContent=list.length?`${String(activeIndex+1).padStart(2,'0')} / ${list.length}`:'0 / 0';
 document.querySelector('#undo-car').disabled=!history.length;
 document.querySelector('#skip-car').disabled=!c||list.length<2;
 const like=document.querySelector('#like-car');like.disabled=!c;like.classList.toggle('is-saved',!!c&&saved.has(c.id));like.setAttribute('aria-label',c&&saved.has(c.id)?'Убрать из сохранённых':'Сохранить автомобиль');like.setAttribute('aria-pressed',String(!!c&&saved.has(c.id)));
 feed.innerHTML=c?`<article class="car" data-id="${c.id}"><div class="visual" style="--car-image:url('${c.image}')"><img src="${c.image}" alt="${c.name}, внешний вид" draggable="false"><div class="badges"><span class="badge dark">ИЗ КИТАЯ</span><span class="badge">${c.fuel||'Автомобиль'}</span></div><span class="swipe-stamp stamp-save">В сохранённые</span><span class="swipe-stamp stamp-skip">Дальше</span><button class="expand-photo" data-photo="${c.id}" aria-label="Открыть фото ${c.name} целиком"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg></button><span class="photo-label">${c.body_label||'Автомобиль'} · ${c.year||'—'}</span></div><div class="car-body"><div class="title-row"><div><h3>${c.name}</h3><p class="sub">${c.trim||''}</p></div>${saved.has(c.id)?'<span class="saved-mark" aria-label="Сохранён">♥</span>':''}</div><div class="quick-specs"><span>${c.km||'Пробег не указан'}</span><span>${c.power||'Мощность не указана'}</span><span>${c.year||'—'} г.</span></div><div class="price-row"><div><div class="price">${money(c.price)}</div><div class="price-note">${priceNote()}</div></div><button class="details-orb" data-detail="${c.id}" aria-label="Подробнее о ${c.name}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></div></article>`:`<div class="empty"><span class="empty-heart">♡</span><h2>${view==='saved'?'Здесь будут ваши фавориты':'Нет подходящих машин'}</h2><p>${view==='saved'?'Нажмите на сердце или смахните машину вправо. Сохранённые авто останутся здесь.':'Попробуйте изменить параметры подбора.'}</p><button class="primary" id="reset">${view==='saved'?'К подбору':'Сбросить фильтры'}</button></div>`;
 updateFilters();
}
function decide(action){const list=eligible(),c=list[activeIndex];if(!c)return;
 history.push({id:c.id,index:activeIndex,view,wasSaved:saved.has(c.id)});if(history.length>50)history.shift();
 if(action==='like'){if(view==='saved'&&saved.has(c.id)){saved.delete(c.id);notify('Убрано из сохранённых')}else{saved.add(c.id);notify('Сохранено. Вернётесь к ней позже.')}persistSaved();}
 if(view==='all'||action==='skip')activeIndex=(activeIndex+1)%list.length;
 render();
}
document.querySelector('#skip-car').addEventListener('click',()=>decide('skip'));
document.querySelector('#like-car').addEventListener('click',()=>decide('like'));
document.querySelector('#undo-car').addEventListener('click',()=>{const previous=history.pop();if(!previous)return;view=previous.view;previous.wasSaved?saved.add(previous.id):saved.delete(previous.id);persistSaved();activeIndex=Math.max(0,eligible().findIndex(c=>c.id===previous.id));render();notify('Последнее действие отменено')});
let drag=null;
feed.addEventListener('pointerdown',e=>{if(!e.isPrimary||e.button!==0||!e.target.closest('.visual')||e.target.closest('button'))return;drag={x:e.clientX,y:e.clientY,id:e.pointerId,card:e.target.closest('.car'),dx:0};});
feed.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.id)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dy)>Math.abs(dx)&&Math.abs(dx)<15){drag=null;return;}drag.dx=dx;if(Math.abs(dx)>12){feed.setPointerCapture(e.pointerId);drag.card.style.transform=`translateX(${dx*.65}px) rotate(${dx/35}deg)`;drag.card.classList.toggle('swiping-save',dx>0);drag.card.classList.toggle('swiping-skip',dx<0);}});
function endDrag(e,cancelled=false){if(!drag||e.pointerId!==drag.id)return;const {card,dx}=drag;drag=null;card.style.transform='';card.classList.remove('swiping-save','swiping-skip');if(Math.abs(dx)>12)suppressPhotoUntil=Date.now()+400;if(!cancelled&&Math.abs(dx)>70)decide(dx>0?'like':'skip');}
feed.addEventListener('pointerup',e=>endDrag(e));feed.addEventListener('pointercancel',e=>endDrag(e,true));
document.addEventListener('click',e=>{const photo=e.target.closest('[data-photo]')|| (e.target.matches('.visual img')?e.target.closest('.car'):null);if(photo&&Date.now()>suppressPhotoUntil){const c=cars.find(c=>c.id===(photo.dataset.photo||photo.dataset.id));document.querySelector('#photo-image').src=c.image;document.querySelector('#photo-image').alt=c.name;document.querySelector('#photo-caption').textContent=c.name+' · Фото модели';document.querySelector('#photo-dialog').showModal();}const s=e.target.closest('[data-save]'),d=e.target.closest('[data-detail]'),f=e.target.closest('[data-filter]'),v=e.target.closest('[data-view]');if(s){const id=s.dataset.save;saved.has(id)?saved.delete(id):saved.add(id);try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}const y=feed.scrollTop;render();feed.querySelector(`[data-save="${id}"]`)?.focus({preventScroll:true});notify(saved.has(id)?'Автомобиль в избранном':'Автомобиль удалён из избранного')}
if(f){filter=f.dataset.filter;document.querySelectorAll('.chip').forEach(x=>(x.classList.toggle('selected',x===f),x.setAttribute('aria-pressed',String(x===f))));render()}
if(v){view=v.dataset.view;activeIndex=0;document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x===v));render()}
if(d){openDetail(d.dataset.detail)}
if(e.target.closest('.close'))e.target.closest('dialog').close();if(e.target.id==='reset'){filter='all';view='all';criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('selected',x.dataset.filter==='all'));document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view==='all'));render()}});
document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]')||e.target.matches('input,select,textarea')||!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();decide(e.key==='ArrowRight'?'like':'skip')});
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
form.addEventListener('change',draftCount);form.addEventListener('submit',e=>{e.preventDefault();criteria=draft();activeIndex=0;history=[];filterDialog.close();render()});
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
