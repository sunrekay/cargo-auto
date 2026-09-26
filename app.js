const cars=[
  {
    "id": "zeekr",
    "brand": "zeekr",
    "model": "001",
    "name": "Zeekr 001",
    "trim": "Long Range · Shooting brake",
    "type": "electric",
    "body": "wagon",
    "year": 2024,
    "km": "12 800 км",
    "power": "544 л.с.",
    "price": 3890000,
    "image": "assets/zeekr.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "zeekr-007",
    "brand": "zeekr",
    "model": "007",
    "name": "Zeekr 007",
    "trim": "Performance · Седан",
    "type": "electric",
    "body": "sedan",
    "year": 2024,
    "km": "9 200 км",
    "power": "646 л.с.",
    "price": 3650000,
    "image": "assets/zeekr-007.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "zeekr-x",
    "brand": "zeekr",
    "model": "x",
    "name": "Zeekr X",
    "trim": "Flagship · Кроссовер",
    "type": "electric",
    "body": "suv",
    "year": 2024,
    "km": "6 400 км",
    "power": "428 л.с.",
    "price": 2790000,
    "image": "assets/zeekr-x.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "zeekr-001-2",
    "brand": "zeekr",
    "model": "001",
    "name": "Zeekr 001",
    "trim": "Long Range · Другое предложение",
    "type": "electric",
    "body": "wagon",
    "year": 2024,
    "km": "24 000 км",
    "power": "544 л.с.",
    "price": 3690000,
    "image": "assets/zeekr.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "li",
    "brand": "li",
    "model": "l7",
    "name": "Li Auto L7",
    "trim": "Max · Семейный кроссовер",
    "type": "hybrid",
    "body": "suv",
    "year": 2024,
    "km": "8 400 км",
    "power": "449 л.с.",
    "price": 4590000,
    "image": "assets/li.jpg",
    "fuel": "Гибрид",
    "city": "Шанхай"
  },
  {
    "id": "li-l6",
    "brand": "li",
    "model": "l6",
    "name": "Li Auto L6",
    "trim": "Max · Кроссовер",
    "type": "hybrid",
    "body": "suv",
    "year": 2024,
    "km": "11 000 км",
    "power": "408 л.с.",
    "price": 3790000,
    "image": "assets/li-l6.jpg",
    "fuel": "Гибрид",
    "city": "Шанхай"
  },
  {
    "id": "li-l9",
    "brand": "li",
    "model": "l9",
    "name": "Li Auto L9",
    "trim": "Max · Шесть мест",
    "type": "hybrid",
    "body": "suv",
    "year": 2024,
    "km": "17 500 км",
    "power": "449 л.с.",
    "price": 5290000,
    "image": "assets/li-l9.jpg",
    "fuel": "Гибрид",
    "city": "Шанхай"
  },
  {
    "id": "xiaomi",
    "brand": "xiaomi",
    "model": "su7",
    "name": "Xiaomi SU7",
    "trim": "Max · Спортивный седан",
    "type": "electric",
    "body": "sedan",
    "year": 2024,
    "km": "6 200 км",
    "power": "673 л.с.",
    "price": 4190000,
    "image": "assets/xiaomi.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "xiaomi-su7-pro",
    "brand": "xiaomi",
    "model": "su7",
    "name": "Xiaomi SU7",
    "trim": "Pro · Седан",
    "type": "electric",
    "body": "sedan",
    "year": 2024,
    "km": "14 500 км",
    "power": "299 л.с.",
    "price": 3490000,
    "image": "assets/xiaomi.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  },
  {
    "id": "xiaomi-yu7",
    "brand": "xiaomi",
    "model": "yu7",
    "name": "Xiaomi YU7",
    "trim": "Max · Кроссовер",
    "type": "electric",
    "body": "suv",
    "year": 2025,
    "km": "3 000 км",
    "power": "690 л.с.",
    "price": 4990000,
    "image": "assets/xiaomi-yu7.jpg",
    "fuel": "Электро",
    "city": "Шанхай"
  }
];
let saved;try{saved=new Set(JSON.parse(localStorage.getItem('potok-saved')||'[]'))}catch{saved=new Set()}
let filter='all',view='all';let criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};function matches(c,q){return(q.brand==='all'||c.brand===q.brand)&&(q.model==='all'||c.model===q.model)&&(q.budget==='all'||c.price<=Number(q.budget))&&(q.fuel==='all'||c.type===q.fuel)&&(q.body==='all'||c.body===q.body)}const feed=document.querySelector('#feed');const money=n=>new Intl.NumberFormat('ru-RU').format(n)+' ₽';
function notify(t){const el=document.querySelector('#toast');el.textContent=t;el.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.classList.remove('show'),2200)}
function render(){document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.filter===filter)));document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.view===view)));const list=cars.filter(c=>(view==='all'||saved.has(c.id))&&matches(c,criteria));document.querySelector('#saved-count').textContent=saved.size;
feed.innerHTML=list.length?list.map(c=>`<article class="car" data-id="${c.id}"><div class="visual" style="--car-image:url('${c.image}')"><img src="${c.image}" alt="${c.name}, внешний вид" draggable="false"><div class="badges"><span class="badge">${c.fuel}</span><span class="badge dark">CN · ${c.city}</span></div><span class="photo-label">Фото модели</span><button class="expand-photo" data-photo="${c.id}" aria-label="Открыть фото ${c.name} целиком"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg></button></div><div class="car-body"><div class="title-row"><div><h3>${c.name}</h3><p class="sub">${c.trim}</p></div><button class="save ${saved.has(c.id)?'is-saved':''}" aria-label="${saved.has(c.id)?'Удалить из избранного':'Сохранить '+c.name}" aria-pressed="${saved.has(c.id)}" data-save="${c.id}">${saved.has(c.id)?'♥':'♡'}</button></div><ul class="specs"><li><b>${c.year}</b><span>Год</span></li><li><b>${c.km}</b><span>Пробег</span></li><li><b>${c.power}</b><span>Мощность</span></li><li><b>${c.fuel}</b><span>Двигатель</span></li></ul><div class="price-row"><div><div class="price">${money(c.price)}</div><div class="price-note">С доставкой в РФ · демо</div></div><button class="primary" data-detail="${c.id}">Подробнее</button></div></div></article>`).join(''):'<div class="empty"><h2>Пока ни одной машины</h2><p>Сохраните понравившийся автомобиль или выберите другой фильтр.</p><button class="primary" id="reset">Вернуться к ленте</button></div>';
feed.scrollTop=0;updateCount();updateFilters();}
function updateCount(){const items=[...feed.querySelectorAll('.car')];const i=items.length?Math.round(feed.scrollTop/(items[0].offsetHeight+16))+1:0;document.querySelector('#feed-count').textContent=String(Math.min(i,items.length)).padStart(2,'0')+' / '+String(items.length).padStart(2,'0')}
feed.addEventListener('scroll',updateCount,{passive:true});
document.addEventListener('click',e=>{const photo=e.target.closest('[data-photo]')|| (e.target.matches('.visual img')?e.target.closest('.car'):null);if(photo){const c=cars.find(c=>c.id===(photo.dataset.photo||photo.dataset.id));document.querySelector('#photo-image').src=c.image;document.querySelector('#photo-image').alt=c.name;document.querySelector('#photo-caption').textContent=c.name+' · Фото модели';document.querySelector('#photo-dialog').showModal();}const s=e.target.closest('[data-save]'),d=e.target.closest('[data-detail]'),f=e.target.closest('[data-filter]'),v=e.target.closest('[data-view]');if(s){const id=s.dataset.save;saved.has(id)?saved.delete(id):saved.add(id);try{localStorage.setItem('potok-saved',JSON.stringify([...saved]))}catch{}const y=feed.scrollTop;render();feed.scrollTop=y;feed.querySelector(`[data-save="${id}"]`)?.focus({preventScroll:true});notify(saved.has(id)?'Автомобиль в избранном':'Автомобиль удалён из избранного')}
if(f){filter=f.dataset.filter;document.querySelectorAll('.chip').forEach(x=>(x.classList.toggle('selected',x===f),x.setAttribute('aria-pressed',String(x===f))));render()}
if(v){view=v.dataset.view;document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x===v));render()}
if(d){const c=cars.find(x=>x.id===d.dataset.detail);document.querySelector('#detail-content').innerHTML=`<span class="eyebrow">ЗНАКОМЬТЕСЬ БЛИЖЕ</span><h2 id="detail-title">${c.name}</h2><p>${c.trim}. ${c.year} год, ${c.km}. ${c.fuel}, ${c.power}.</p><h3>Из чего складывается цена</h3><div class="cost-line"><span>Автомобиль в Китае</span><b>${money(c.price-990000)}</b></div><div class="cost-line"><span>Доставка и оформление</span><b>290 000 ₽</b></div><div class="cost-line"><span>Пошлины и сборы</span><b>700 000 ₽</b></div><div class="cost-line total"><span>Примерная стоимость</span><span>${money(c.price)}</span></div><p>Это демонстрационная карточка, а не предложение о продаже. Фото показывает модель; комплектация, пробег и расчёт приведены для примера. Реальная цена требует проверки автомобиля и актуального расчёта.</p>`;document.querySelector('dialog').showModal()}
if(e.target.closest('.close'))e.target.closest('dialog').close();if(e.target.id==='reset'){filter='all';view='all';criteria={brand:'all',model:'all',budget:'all',fuel:'all',body:'all'};document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('selected',x.dataset.filter==='all'));document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view==='all'));render()}});
document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]')||!['ArrowDown','ArrowUp'].includes(e.key))return;e.preventDefault();const card=feed.querySelector('.car');if(card)feed.scrollBy({top:(card.offsetHeight+16)*(e.key==='ArrowDown'?1:-1),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})});
const filterDialog=document.querySelector('#filters-dialog'),form=document.querySelector('#filter-form');
function draft(){return {...criteria,...Object.fromEntries(new FormData(form))}}
function updateFilters(){const count=Object.values(criteria).filter(v=>v!=='all').length;const badge=document.querySelector('#filter-count');badge.hidden=!count;badge.textContent=count;document.querySelector('#clear-filters').hidden=!count;document.querySelector('#brand-trigger').innerHTML=(criteria.brand==='all'?'Марка':{zeekr:'Zeekr',li:'Li Auto',xiaomi:'Xiaomi'}[criteria.brand])+' <span>⌄</span>';document.querySelector('#model-trigger').innerHTML=(criteria.model==='all'?'Модель':({ '001':'001','007':'007',x:'X',l7:'L7',l6:'L6',l9:'L9',su7:'SU7',yu7:'YU7' })[criteria.model])+' <span>⌄</span>';}

const brands=[{id:'zeekr',name:'Zeekr'},{id:'li',name:'Li Auto'},{id:'xiaomi',name:'Xiaomi'}];
let pickerStep='brands';
function setStep(step){if(step==='models'&&form.elements.brand.value==='all')step='brands';pickerStep=step;document.querySelector('#brand-panel').hidden=step!=='brands';document.querySelector('#model-panel').hidden=step!=='models';document.querySelectorAll('[data-step]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.step===step)));document.querySelector('#filters-title').textContent=step==='brands'?'С чего начнём?':'Найдите свою модель';}
function renderPicker(){
 const q=draft(),search=document.querySelector('#brand-search').value.trim().toLowerCase();
 const list=brands.filter(b=>b.name.toLowerCase().includes(search));
 document.querySelector('#brand-grid').innerHTML=list.length?list.map(b=>`<button type="button" class="brand-tile ${q.brand===b.id?'chosen':''}" data-brand="${b.id}" aria-pressed="${q.brand===b.id}"><img src="assets/${b.id}-logo.svg" alt=""><strong>${b.name}</strong><span>${cars.filter(c=>c.brand===b.id).length} авто</span><i aria-hidden="true">${q.brand===b.id?'✓':'↗'}</i></button>`).join(''):'<p class="picker-note">Такой марки нет в демоподборке. Попробуйте Zeekr, Li Auto или Xiaomi.</p>';
 const offers=cars.filter(c=>c.brand===q.brand);const models=[...new Set(offers.map(c=>c.model))].map(m=>offers.filter(c=>c.model===m).sort((a,b)=>a.price-b.price)[0]);
 document.querySelector('#models-heading').textContent=q.brand==='all'?'Все модели':brands.find(b=>b.id===q.brand).name;
 document.querySelector('#model-grid').innerHTML=models.map(c=>`<button type="button" class="model-tile ${q.model===c.model?'chosen':''}" data-model="${c.model}" aria-pressed="${q.model===c.model}"><div class="model-photo"><img src="${c.image}" alt="${c.name}"><span class="model-check" aria-hidden="true">${q.model===c.model?'✓':'+'}</span></div><div class="model-info"><strong>${c.name}</strong><span>${c.fuel} · ${c.year}</span><b>от ${money(c.price)}</b><small>С доставкой · демо</small></div></button>`).join('');
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
render();
