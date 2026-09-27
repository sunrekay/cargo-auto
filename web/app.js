// Catalogue and brands are loaded from the backend at boot (see boot() below).
let cars=[];

let saved;try{saved=new Set(JSON.parse(localStorage.getItem('potok-saved')||'[]'))}catch{saved=new Set()}
let filter='all',view='all';let criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};function matches(c,q){return(q.brand==='all'||c.brand===q.brand)&&(q.model==='all'||c.model===q.model)&&(q.budget==='all'||c.price<=Number(q.budget))&&(q.fuel==='all'||c.type===q.fuel)&&(q.body==='all'||c.body===q.body)}const feed=document.querySelector('#feed');let currency='USD';const priceNote=()=>currency==='RUB'
  ?'Цена в Китае · пересчёт по курсу':'Цена в Китае · источник Guazi';const money=n=>n==null?'—':(currency==='RUB'
  ?new Intl.NumberFormat('ru-RU').format(n)+' ₽'
  :'$'+new Intl.NumberFormat('en-US').format(n));
function notify(t){const el=document.querySelector('#toast');el.textContent=t;el.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.classList.remove('show'),2200)}
let activeIndex=0,suppressPhotoUntil=0;
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const iconHeart='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 5.5c-2.4-2.4-6-1.5-8.5 1-2.5-2.5-6.1-3.4-8.5-1C.1 8.9 3.5 13.8 12 20c8.5-6.2 11.9-11.1 8.5-14.5Z"/></svg>';
function eligible(){return cars.filter(c=>matches(c,criteria)&&(view!=='saved'||saved.has(c.id)));}
function persistSaved(){try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}}
function carTitle(c){
 const name=String(c.name||'');
 if(!/^Used /i.test(name)&&!name.includes('for Sale'))return name;
 return [c.brand_name,c.model_name].filter(Boolean).join(' ')||name.replace(/^Used /i,'').split(/ for Sale| \d{4}/)[0];
}
function openSavedCar(id){
 const car=cars.find(c=>c.id===id);if(!car)return;
 const dialog=document.querySelector('#saved-car-dialog');
 dialog.querySelector('.saved-car-content').innerHTML=cardMarkup(car);
 paintCardPhoto(dialog.querySelector('.car'));
 dialog.showModal();
 dialog.focus({preventScroll:true});
}
function garageMarkup(list){return `<section class="garage-collection" aria-label="Сохранённые автомобили"><div class="garage-heading"><h1>Мой гараж</h1><span>${list.length} авто</span></div><div class="garage-grid">${list.map(c=>`<article class="garage-card"><button class="garage-open" data-car-open="${c.id}" aria-label="Открыть ${escapeHTML(carTitle(c))}"><div class="garage-photo"><img src="${escapeHTML(c.image)}" alt="${escapeHTML(carTitle(c))}" loading="lazy"><span>${c.year||'—'}</span></div><div class="garage-info"><h2>${escapeHTML(carTitle(c))}</h2><p>${escapeHTML(c.km||'—')} · ${escapeHTML(c.fuel||'—')}</p><strong>${money(c.price)}</strong><small>Стоимость в Китае*</small></div></button><button class="garage-remove" data-save="${c.id}" aria-label="Убрать ${escapeHTML(carTitle(c))} из гаража">${iconHeart}</button></article>`).join('')}</div></section>`;}
const GRADES=['S','A','B','C','D'];
const numberFmt=new Intl.NumberFormat('ru-RU');

// Figures set as figures — a large value over a quiet label — instead of a row
// of pills. The same four facts, read at a glance rather than deciphered.
function specRow(c){
 const cells=[
  [c.year,'год'],
  [c.mileage_km!=null?numberFmt.format(c.mileage_km):null,'км'],
  [c.power_ps,'л.с.'],
  [c.drive||c.transmission,'привод'],
 ].filter(([v])=>v!=null&&v!=='');
 return `<div class="spec-row">${cells.map(([v,l])=>
  `<div><b>${escapeHTML(String(v))}</b><span>${l}</span></div>`).join('')}</div>`;
}

// What sets these listings apart is that every car has been through Guazi's
// inspection: a grade on the S-D scale and a report running to well over a
// hundred measured characteristics. Worth showing, where the card has room.
function inspection(c){
 if(!c.grade&&!c.spec_count)return '';
 const scale=c.grade?`<div class="grade-scale" role="img"
   aria-label="Оценка состояния ${escapeHTML(c.grade)} по шкале ${GRADES.join(' ')}">`
   +GRADES.map(g=>`<span class="${g===c.grade?'on':''}">${g}</span>`).join('')+`</div>`:'';
 const count=c.spec_count
  ? `<b>${c.spec_count}</b> ${plural(c.spec_count,'характеристика','характеристики','характеристик')} в отчёте`
  : 'отчёт об осмотре';
 return `<div class="inspection">${scale}
  <p><span>Осмотр Guazi</span>${count}</p></div>`;
}

const plural=(n,one,few,many)=>{const a=Math.abs(n)%100,b=a%10;
 return a>10&&a<20?many:b>1&&b<5?few:b===1?one:many;};

function cardMarkup(c){return `<article class="car" data-id="${c.id}"><div class="visual" style="--car-image:url('${escapeHTML(c.image)}')"><img src="${c.image}" alt="${c.name}, внешний вид" draggable="false"><button class="photo-zone photo-zone-left" data-photo-step="-1" aria-label="Предыдущее фото"></button><button class="photo-zone photo-zone-center" data-photo-open aria-label="Увеличить фотографию"></button><button class="photo-zone photo-zone-right" data-photo-step="1" aria-label="Следующее фото"></button></div><div class="car-body"><div class="price-row"><div><div class="price-inline"><div class="price">${money(c.price)}</div><span class="price-origin">Стоимость в Китае*</span></div></div><button class="details-orb" data-detail="${c.id}" aria-label="Подробнее о ${c.name}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div><div class="title-row"><div><span class="car-eyebrow">${escapeHTML(c.body_label||'АВТОМОБИЛЬ')} / ${escapeHTML(c.fuel||'—')} / КИТАЙ</span><h3>${escapeHTML(carTitle(c))}</h3><p class="sub">${escapeHTML(c.trim||'')}</p></div>${saved.has(c.id)?'<span class="saved-mark" aria-label="Сохранён">♥</span>':''}</div>${specRow(c)}${inspection(c)}</div></article>`;}
function render(){
 const list=eligible();activeIndex=Math.max(0,Math.min(activeIndex,Math.max(0,list.length-1)));const c=list[activeIndex];
 document.querySelectorAll('[data-view]').forEach(x=>{const on=x.dataset.view===view;x.setAttribute('aria-pressed',String(on));x.classList.toggle('active',on)});
 document.querySelector('#saved-count').textContent=cars.filter(c=>saved.has(c.id)).length;
 document.body.classList.toggle('garage-view',view==='saved');
 if(view==='saved'&&list.length){feed.innerHTML=garageMarkup(list);updateFilters();return;}
 feed.innerHTML=c?cardMarkup(c):`<div class="empty"><span class="empty-heart">♡</span><h2>${view==='saved'?'Гараж начинается с симпатии':'Нет подходящих машин'}</h2><p>${view==='saved'?'Смахните вправо то, что зацепило. Мы сохраним ваши находки здесь.':'Попробуйте изменить параметры подбора.'}</p><button class="primary" id="reset">${view==='saved'?'К подбору':'Сбросить фильтры'}</button></div>`;
 warmCatalogue(list,activeIndex);
 restoreCardPhoto();
 updateFilters();
 requestAnimationFrame(seatDescription);
}
const warmedImages=new Map();
function warmImage(url){
 if(!url||warmedImages.has(url))return;
 const img=new Image();img.decoding='async';img.src=url;
 warmedImages.set(url,img);img.decode().catch(()=>{});
 // Keep a bounded window of decoded images, not the whole catalogue.
 if(warmedImages.size>30)warmedImages.delete(warmedImages.keys().next().value);
}
function warmCatalogue(list,index){
 for(const offset of [-1,0,1,2,3,4]){
  const car=list[(index+offset+list.length)%list.length];if(!car)continue;
  warmImage(car.image);
 }
}
// The card leaving the stack is decoration: saved, activeIndex and render()
// have all committed before it starts moving, and nothing awaits it. It owns
// its own lifetime, which is why no input path consults animation state — a
// gesture can never be swallowed by an animation still in progress.
let departing=null;
function flyOut(card,action,from){
 departing?.remove();                       // at most one card in flight
 departing=card;
 card.classList.add('departing');card.setAttribute('aria-hidden','true');card.inert=true;
 card.classList.toggle('swiping-save',action==='like');card.classList.toggle('swiping-skip',action==='skip');
 card.style.setProperty('--swipe-tint','1');feed.append(card);
 const to={like:'translateX(115%) rotate(8deg)',skip:'translateX(-115%) rotate(-8deg)',next:'translateY(-105%)',previous:'translateY(105%)'}[action];
 const out=card.animate([{transform:from,opacity:1},{transform:to,opacity:0}],
  {duration:390,easing:'cubic-bezier(.32,.05,.22,1)',fill:'forwards'});
 // The next card is already underneath before the outgoing one moves away.
 feed.querySelector('.car:not(.departing)')?.animate(
  [{transform:'scale(.975)',opacity:.6},{transform:'scale(1)',opacity:1}],
  {duration:440,easing:'cubic-bezier(.2,.75,.2,1)'});
 out.finished.catch(()=>{}).then(()=>{if(departing===card){card.remove();departing=null;}});
}
function decide(action){
 if(view==='saved')return;
 const list=eligible(),c=list[activeIndex];if(!c)return;
 const card=feed.querySelector('.car:not(.departing)');
 const from=card?.style.transform||'none';
 if(action==='like'){
  if(view==='saved')saved.delete(c.id);else saved.add(c.id);
  persistSaved();
 }
 if(!(view==='saved'&&action==='like'))activeIndex=(activeIndex+(action==='previous'?-1:1)+list.length)%list.length;
 render();
 if(!card||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 flyOut(card,action,from);
}
function showUnderCard(direction=1){
 const list=eligible();
 if(list.length<2)return;
 const next=list[(activeIndex+direction+list.length)%list.length];
 const existing=feed.querySelector('.under-card');
 if(existing?.dataset.id===next.id)return;
 existing?.remove();
 const template=document.createElement('template');template.innerHTML=cardMarkup(next);
 const under=template.content.firstElementChild;
 under.classList.add('under-card');under.inert=true;under.setAttribute('aria-hidden','true');
 feed.append(under);
}
// The edge fade is a mask on the element box, so the box has to be the picture.
// Its real ratio is only known once the file has loaded; load does not bubble,
// hence the capture-phase listener.
feed.addEventListener('load',e=>{
 const img=e.target;
 if(img.tagName==='IMG'&&img.naturalWidth&&img.naturalHeight)
  img.style.aspectRatio=`${img.naturalWidth}/${img.naturalHeight}`;
 requestAnimationFrame(seatDescription);
},true);
// Seat the description just under the photo. The picture is 4:3 in a portrait
// card, so the leftover height shows up as a blurred gap between them; this
// measures that gap and lifts the block into it, leaving the surplus at the
// foot of the card where it reads as padding rather than a hole.
const DESCRIPTION_GAP=22;
function seatDescription(){
 const card=feed.querySelector('.car:not(.departing)');
 if(!card)return;
 const img=card.querySelector('.visual img'),body=card.querySelector('.car-body');
 if(!img||!body)return;
 body.style.setProperty('--body-lift','0px');
 const gap=body.getBoundingClientRect().top-img.getBoundingClientRect().bottom;
 const lift=Math.max(0,Math.round(gap-DESCRIPTION_GAP));
 body.style.setProperty('--body-lift',lift+'px');
}
addEventListener('resize',seatDescription);
let drag=null;
feed.addEventListener('pointerdown',e=>{
 if(!e.isPrimary||e.button!==0||!e.target.closest('.car')||(e.target.closest('button')&&!e.target.closest('.photo-zone')))return;
 showUnderCard();
 drag={x:e.clientX,y:e.clientY,id:e.pointerId,card:e.target.closest('.car'),dx:0,dy:0,axis:null};
});
feed.addEventListener('pointermove',e=>{
 if(!drag||e.pointerId!==drag.id)return;
 const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
 if(!drag.axis&&Math.max(Math.abs(dx),Math.abs(dy))>10){drag.axis=Math.abs(dx)>Math.abs(dy)?'x':'y';feed.setPointerCapture(e.pointerId);}
 drag.dx=dx;drag.dy=dy;
 if(!drag.axis)return;
 showUnderCard(drag.axis==='y'&&dy>0?-1:1);
 drag.card.style.setProperty('--swipe-tint',String(Math.min(1,Math.abs(dx)/130)));
 drag.card.classList.add('is-dragging');
 drag.card.style.transform=drag.axis==='x'?`translateX(${dx*.65}px) rotate(${dx/35}deg)`:`translateY(${dy*.65}px)`;
 drag.card.classList.toggle('swiping-save',drag.axis==='x'&&dx>0);
 drag.card.classList.toggle('swiping-skip',drag.axis==='x'&&dx<0);
});
function endDrag(e,cancelled=false){
 if(!drag||e.pointerId!==drag.id)return;
 const {card,dx,dy,axis}=drag;drag=null;
 if(Math.max(Math.abs(dx),Math.abs(dy))>10)suppressPhotoUntil=Date.now()+450;
 const distance=axis==='x'?dx:dy;
 if(!cancelled&&axis&&Math.abs(distance)>55){decide(axis==='x'?(dx>0?'like':'skip'):(dy<0?'next':'previous'));}
 else {feed.querySelector('.under-card')?.remove();card.style.transform='';card.style.setProperty('--swipe-tint','0');card.classList.remove('swiping-save','swiping-skip');}
 card.classList.remove('is-dragging');
}
feed.addEventListener('pointerup',e=>endDrag(e));
feed.addEventListener('pointercancel',e=>endDrag(e,true));
// Require a fresh wheel gesture after momentum stops, so trackpads don't skip several cars.
let wheelTotal=0,wheelLocked=false,wheelTimer;
feed.addEventListener('wheel',e=>{
 if(view==='saved'||e.ctrlKey||document.querySelector('dialog[open]'))return;
 e.preventDefault();clearTimeout(wheelTimer);
 wheelTimer=setTimeout(()=>{wheelTotal=0;wheelLocked=false;},180);
 if(wheelLocked)return;
 wheelTotal+=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?feed.clientHeight:1);
 if(Math.abs(wheelTotal)>45){wheelLocked=true;decide(wheelTotal>0?'next':'previous');}
},{passive:false});
document.addEventListener('click',e=>{const opened=e.target.closest('[data-car-open]');if(opened)openSavedCar(opened.dataset.carOpen);const zone=e.target.closest('.photo-zone');if(zone&&Date.now()>suppressPhotoUntil){const card=zone.closest('.car');if(zone.hasAttribute('data-photo-step'))stepCardPhoto(card,Number(zone.dataset.photoStep));else openGallery(card.dataset.id,cardPhotoIndices.get(card.dataset.id)||0);}const s=e.target.closest('[data-save]'),d=e.target.closest('[data-detail]'),f=e.target.closest('[data-filter]'),v=e.target.closest('[data-view]');if(s){const id=s.dataset.save;saved.has(id)?saved.delete(id):saved.add(id);try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}const y=feed.scrollTop;render();feed.scrollTop=y;feed.querySelector(`[data-save="${id}"]`)?.focus({preventScroll:true});notify(saved.has(id)?'Автомобиль в избранном':'Автомобиль удалён из избранного')}
if(f){filter=f.dataset.filter;document.querySelectorAll('.chip').forEach(x=>(x.classList.toggle('selected',x===f),x.setAttribute('aria-pressed',String(x===f))));render()}
if(v){view=v.dataset.view;activeIndex=0;feed.scrollTop=0;document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x===v));render()}
if(d){openDetail(d.dataset.detail)}
if(e.target.closest('.close'))e.target.closest('dialog').close();if(e.target.id==='reset'){filter='all';view='all';criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('selected',x.dataset.filter==='all'));document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view==='all'));render()}});
document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]')||e.target?.matches?.('input,select,textarea')||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();decide({ArrowRight:'like',ArrowLeft:'skip',ArrowUp:'previous',ArrowDown:'next'}[e.key])});
const filterDialog=document.querySelector('#filters-dialog'),form=document.querySelector('#filter-form');
function draft(){return {...criteria,...Object.fromEntries(new FormData(form))}}
function updateFilters(){const count=Object.values(criteria).filter(v=>v!=='all').length;const badge=document.querySelector('#filter-count');badge.hidden=!count;badge.textContent=count;document.querySelector('#clear-filters').hidden=!count;document.querySelector('#brand-trigger').innerHTML=(criteria.brand==='all'?'Марка':(brandNames[criteria.brand]||criteria.brand))+' <span>⌄</span>';document.querySelector('#model-trigger').innerHTML=(criteria.model==='all'?'Модель':(modelNames[criteria.model]||criteria.model))+' <span>⌄</span>';}

let brands=[];let modelNames={};let brandNames={};
let pickerStep='brands';
function setStep(step){if(step==='models'&&form.elements.brand.value==='all')step='brands';pickerStep=step;document.querySelector('#brand-panel').hidden=step!=='brands';document.querySelector('#model-panel').hidden=step!=='models';document.querySelectorAll('[data-step]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.step===step)));document.querySelector('#filters-title').textContent=step==='brands'?'С чего начнём?':'Найдите свою модель';}
function renderPicker(){
 const q=draft(),search=document.querySelector('#brand-search').value.trim().toLowerCase();
 const list=brands.filter(b=>b.name.toLowerCase().includes(search));
 document.querySelector('#brand-grid').innerHTML=list.length?list.map(b=>{const b_initial=(b.name||'?')[0];return `<button type="button" class="brand-tile ${q.brand===b.id?'chosen':''}" data-brand="${b.id}" aria-pressed="${q.brand===b.id}">${['zeekr','li','xiaomi'].includes(b.id)?`<img src="assets/${b.id}-logo.svg" alt="" data-initial="${b_initial}">`:`<span class="brand-initial">${b_initial}</span>`}<strong>${b.name}</strong><span>${cars.filter(c=>c.brand===b.id).length} авто</span><i aria-hidden="true">${q.brand===b.id?'✓':'↗'}</i></button>`}).join(''):'<p class="picker-note">Такой марки нет в подборке.</p>';
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
form.addEventListener('change',draftCount);form.addEventListener('submit',e=>{e.preventDefault();criteria=draft();activeIndex=0;filterDialog.close();render()});
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
      <h2 id="detail-title">${escapeHTML(carTitle(car))}</h2>
      <p>${[car.trim,car.year&&car.year+' год',car.km,car.power,car.colour]
            .filter(Boolean).join(' · ')}</p>
      <div class="cost-line total"><span>Цена</span><span>${money(car.price??car.price_usd)}</span></div>
      <h3>Характеристики</h3>${head}
      <details><summary>Ещё ${rest.length} характеристик</summary>
        ${rest.map(s=>`<div class="cost-line"><span>${s.label}</span><b>${s.value}</b></div>`).join('')}
      </details>
      <h3>Фотографии · ${car.photos.length}</h3>
      <div class="detail-photos">${car.photos.map((ph,index)=>
        `<button class="detail-photo" data-gallery="${car.id}" data-index="${index}" aria-label="Фото ${index+1}"><img src="${ph.url}" alt="${escapeHTML(ph.alt||car.name)}" loading="lazy"></button>`).join('')}</div>
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
      '<p>Не удалось загрузить автомобили. Попробуйте обновить страницу.</p></div>';
  }
}
// Gallery requests are cached; a request token prevents late responses replacing another car.
const galleryCache=new Map(),galleryRequests=new Map(),cardPhotoIndices=new Map();
async function loadGallery(id){
 if(galleryCache.has(id))return galleryCache.get(id);
 if(!galleryRequests.has(id))galleryRequests.set(id,api('/api/cars/'+encodeURIComponent(id)).then(car=>{galleryCache.set(id,car);return car;}).finally(()=>galleryRequests.delete(id)));
 return galleryRequests.get(id);
}
// Decode before swapping to keep the previous photograph visible on slow networks.
const photoTransitions=new WeakMap();
async function transitionPhoto(img,url,alt,direction=0,onReady=()=>{}){
 const previous=photoTransitions.get(img);
 if(previous){previous.animations?.forEach(a=>a.cancel());previous.ghost?.remove();}
 const state={url};photoTransitions.set(img,state);
 try{const preload=new Image();preload.src=url;await preload.decode();}catch{if(photoTransitions.get(img)===state)photoTransitions.delete(img);return;}
 if(photoTransitions.get(img)!==state||!img.isConnected)return;
 const animate=direction&&img.getAttribute('src')!==url&&!matchMedia('(prefers-reduced-motion: reduce)').matches;
 let ghost;
 if(animate){
  ghost=img.cloneNode();ghost.removeAttribute('id');ghost.alt='';ghost.setAttribute('aria-hidden','true');
  ghost.classList.add('photo-transition-ghost');
  Object.assign(ghost.style,{position:'absolute',left:img.offsetLeft+'px',top:img.offsetTop+'px',width:img.offsetWidth+'px',height:img.offsetHeight+'px',margin:'0',pointerEvents:'none',zIndex:'1'});
  img.after(ghost);state.ghost=ghost;
 }
 img.src=url;img.alt=alt;onReady();
 if(!animate)return;
 const timing={duration:440,easing:'cubic-bezier(.22,.75,.2,1)',fill:'none'};
 const incoming=img.animate([{opacity:.15,transform:`translateX(${direction*24}px) scale(1.025)`},{opacity:1,transform:'translateX(0) scale(1)'}],timing);
 const outgoing=ghost.animate([{opacity:1,transform:'translateX(0) scale(1)'},{opacity:0,transform:`translateX(${-direction*18}px) scale(.99)`}],timing);
 state.animations=[incoming,outgoing];
 await Promise.allSettled(state.animations.map(a=>a.finished));ghost.remove();
}
feed.addEventListener('pointerdown',e=>{const zone=e.target.closest('[data-photo-step]');if(!zone)return;
 zone.blur();zone.animate([{opacity:0},{opacity:1,offset:.2},{opacity:0}],{duration:460,easing:'ease-out',pseudoElement:'::after'});
});
function paintCardPhoto(card,direction=0){
 const id=card.dataset.id,photos=galleryCache.get(id)?.photos;
 if(!photos?.length)return;
 const index=((cardPhotoIndices.get(id)||0)%photos.length+photos.length)%photos.length;
 cardPhotoIndices.set(id,index);
 const visual=card.querySelector('.visual'),img=visual.querySelector('img');
 transitionPhoto(img,photos[index].url,photos[index].alt||cars.find(c=>c.id===id)?.name||'Автомобиль',direction,()=>{
 visual.style.setProperty('--car-image',`url("${photos[index].url.replace(/"/g,'%22')}")`);
 });
 for(const offset of [-1,1]){const preload=new Image();preload.src=photos[(index+offset+photos.length)%photos.length].url;}
}
function restoreCardPhoto(){const card=feed.querySelector('.car');if(card)paintCardPhoto(card);}
async function stepCardPhoto(card,delta){
 const id=card.dataset.id;
 // Record taps immediately so rapid taps retain their order while photos load.
 cardPhotoIndices.set(id,(cardPhotoIndices.get(id)||0)+delta);
 try{await loadGallery(id);if(card.isConnected)paintCardPhoto(card,Math.sign(delta));}
 catch{cardPhotoIndices.delete(id);if(card.isConnected)notify('Не удалось загрузить фото. Попробуйте ещё раз.');}
}
let galleryPhotos=[],galleryIndex=0,galleryName='',galleryRequest=0;
const photoDialog=document.querySelector('#photo-dialog');
function paintGallery(direction=0){
 const photo=galleryPhotos[galleryIndex];if(!photo)return;
 const image=document.querySelector('#photo-image');transitionPhoto(image,photo.url,photo.alt||galleryName,direction,()=>{
 document.querySelector('#photo-caption').textContent=`${galleryName} · ${galleryIndex+1} / ${galleryPhotos.length}`;
 });
}
async function openGallery(id,index=0){
 const token=++galleryRequest,c=cars.find(c=>c.id===id);if(!c)return;
 galleryName=c.name;galleryPhotos=[{url:c.image}];galleryIndex=0;paintGallery();
 if(!photoDialog.open)photoDialog.showModal();
 try{
  await loadGallery(id);
  if(token!==galleryRequest||!photoDialog.open)return;
  const photos=galleryCache.get(id).photos;
  if(photos.length){galleryPhotos=photos;galleryIndex=((index%photos.length)+photos.length)%photos.length;paintGallery();}
 }catch{document.querySelector('#photo-caption').textContent=c.name+' · Остальные фото не загрузились';}
}
function movePhoto(delta){galleryIndex=(galleryIndex+delta+galleryPhotos.length)%galleryPhotos.length;paintGallery(Math.sign(delta));}
document.addEventListener('click',e=>{const button=e.target.closest('[data-gallery]');if(button)openGallery(button.dataset.gallery,Number(button.dataset.index));});
photoDialog.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();movePhoto(e.key==='ArrowRight'?1:-1);}});
let photoStart=null;
photoDialog.addEventListener('pointerdown',e=>{
 if(!e.isPrimary||e.target.closest('button'))return;
 photoStart={x:e.clientX,y:e.clientY,id:e.pointerId};
 photoDialog.setPointerCapture(e.pointerId);
});
photoDialog.addEventListener('pointerup',e=>{
 if(!photoStart||e.pointerId!==photoStart.id)return;
 const dx=e.clientX-photoStart.x,dy=e.clientY-photoStart.y;
 photoStart=null;
 if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))movePhoto(dx<0?1:-1);
});
photoDialog.addEventListener('pointercancel',()=>photoStart=null);
photoDialog.addEventListener('close',()=>{photoStart=null;galleryRequest++;});
let galleryWheel=0,galleryWheelLocked=false,galleryWheelTimer;
photoDialog.addEventListener('wheel',e=>{
 if(e.ctrlKey)return;
 e.preventDefault();clearTimeout(galleryWheelTimer);
 galleryWheelTimer=setTimeout(()=>{galleryWheel=0;galleryWheelLocked=false;},180);
 if(galleryWheelLocked)return;
 const delta=Math.abs(e.deltaX)>Math.abs(e.deltaY)?e.deltaX:e.deltaY;
 galleryWheel+=delta*(e.deltaMode===1?16:e.deltaMode===2?innerHeight:1);
 if(Math.abs(galleryWheel)>45){movePhoto(galleryWheel>0?1:-1);galleryWheelLocked=true;}
},{passive:false});
boot();
