(() => {
  'use strict';
  const $=id=>document.getElementById(id), config=window.PROPERTY, photos=window.PHOTOS, library=window.PhotoLibrary;
  let scene, currentTab='explore', selectedRoom='all', filter='all', slideIndex=0, photoIndex=0, photoSet=photos, planOpen=false;
  const room=id=>config.rooms.find(r=>r.id===id);
  const lines=(parent, values)=>{parent.replaceChildren(...values.map(value=>{const p=document.createElement('p');p.textContent=value;return p;}));};
  const contact=parent=>{
    parent.classList.add('contact');
    const first=document.createElement('p'),call=document.createElement('a');call.href='tel:0925635678';call.textContent=config.contact[0];first.append(call);
    const second=document.createElement('p');second.textContent=config.contact[1];parent.append(first,second);
  };
  contact($('footer-contact'));lines($('footer-disclosure'),config.disclosure);lines($('facts'),config.facts);
  contact($('slide-contact'));const legal=document.createElement('div');legal.className='disclosure';lines(legal,config.disclosure);$('slide-contact').append(legal);
  const slidePrice=document.createElement('div');slidePrice.id='slide-price';slidePrice.className='sale-price';slidePrice.setAttribute('aria-label','售價');slidePrice.hidden=true;
  const priceValue=document.createElement('strong');priceValue.setAttribute('data-price','');const priceNote=document.createElement('small');priceNote.textContent='售價以最新刊登資訊為準';slidePrice.append(priceValue,priceNote);$('slide-contact').before(slidePrice);
  window.ListingView.render(config,document);
  function tab(name, focus=false){
    currentTab=name;
    document.querySelectorAll('[data-tab]').forEach(b=>{const active=b.dataset.tab===name;b.setAttribute('aria-selected',active);b.tabIndex=active?0:-1;if(active&&focus)b.focus();$(b.dataset.tab).hidden=!active;});
    if(name==='explore')requestAnimationFrame(()=>scene?.resize());
    if(name==='report')showSlide(slideIndex);
    document.querySelector('.tabs').scrollIntoView({block:'start'});
  }
  const tabButtons=[...document.querySelectorAll('[data-tab]')];
  tabButtons.forEach((b,i)=>{b.onclick=()=>tab(b.dataset.tab);b.onkeydown=e=>{let n;if(e.key==='ArrowRight')n=(i+1)%4;if(e.key==='ArrowLeft')n=(i+3)%4;if(e.key==='Home')n=0;if(e.key==='End')n=3;if(n!==undefined){e.preventDefault();tab(tabButtons[n].dataset.tab,true);}};});
  document.querySelector('.brand').onclick=e=>{e.preventDefault();$('listing-hero').scrollIntoView({block:'start'});};
  $('start-report').onclick=()=>{slideIndex=0;tab('report');$('tab-report').focus();};
  $('show-plan').onclick=()=>tab('plan');
  for(const r of config.rooms){const b=document.createElement('button');b.textContent=r.name;b.dataset.room=r.id;b.onclick=()=>selectRoom(r.id);$('room-list').append(b);if(r.id!=='all'){const label=document.createElement('span');label.className='scene-label';label.textContent=r.name.replace(/（.*）/,'');label.dataset.label=r.id;$('scene-labels').append(label);}}
  function selectRoom(id){
    selectedRoom=id;const r=room(id);$('room-title').textContent=r.name;$('selected-name').textContent=r.name;$('room-description').textContent=r.description;
    document.querySelectorAll('[data-room]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.room===id));
    document.querySelectorAll('[data-label]').forEach(b=>b.classList.toggle('active',b.dataset.label===id));
    const count=library.forRoom(id).length;
    $('show-room-photos').hidden=!count;$('room-photo-note').textContent=count?'點照片可以放大看。':'可從「現場照片」查看室內空間。';
    scene?.setRoom(id==='all'?null:id);
  }
  try{scene=new window.SpaceScene($('scene'),{onSelect:selectRoom,onChange:state=>{
    for(const label of document.querySelectorAll('[data-label]')){const pos=state.positions[label.dataset.label];label.hidden=!pos?.visible;if(pos){label.style.left=pos.x+'px';label.style.top=pos.y+'px';}}
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.view===state.view));
  }});}catch(error){$('scene-error').hidden=false;console.error(error);}
  selectRoom('all');
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>scene?.setView(b.dataset.view));
  $('zoom-in').onclick=()=>scene?.setZoom(scene.state.zoom+.15);$('zoom-out').onclick=()=>scene?.setZoom(scene.state.zoom-.15);$('reset').onclick=()=>scene?.reset();
  $('walls').onchange=e=>scene?.setWalls(e.target.value);$('furniture').onchange=e=>scene?.setFurniture(e.target.checked);$('labels').onchange=e=>$('scene-labels').hidden=!e.target.checked;
  $('capture').onclick=()=>{
    if(!scene)return;scene.render(performance.now());const c=document.createElement('canvas'),source=$('scene');c.width=Math.max(1200,source.width);c.height=Math.round(source.height*c.width/source.width)+190;const ctx=c.getContext('2d');ctx.fillStyle='#f3f1eb';ctx.fillRect(0,0,c.width,c.height);ctx.drawImage(source,0,0,c.width,c.height-190);ctx.fillStyle='#263b35';ctx.font='26px Microsoft JhengHei, sans-serif';ctx.fillText(config.title+'｜'+config.subtitle,28,c.height-150);ctx.font='19px Microsoft JhengHei, sans-serif';ctx.fillText(config.notice,28,c.height-116);config.disclosure.forEach((line,i)=>ctx.fillText(line,28,c.height-85+i*23));const a=document.createElement('a');a.download='jingping-dayong-view.png';a.href=c.toDataURL('image/png');a.click();$('status').textContent='已產生目前視角圖片。';
  };
  const groups=library.groups;
  for(const[id,name]of groups){const b=document.createElement('button');b.textContent=name;b.dataset.filter=id;b.onclick=()=>renderPhotos(id);$('photo-filters').append(b);}
  function renderPhotos(id){filter=id;const filtered=library.filter(id);$('photo-grid').replaceChildren();document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.filter===id));for(const p of filtered){const f=document.createElement('figure'),b=document.createElement('button'),img=document.createElement('img'),cap=document.createElement('figcaption'),title=document.createElement('strong'),desc=document.createElement('p');f.className='photo-card';b.className='photo-frame';img.src='assets/photos/'+p.file;img.alt=p.title;img.width=1600;img.height=p.source.includes('去浮水印')?1104:1200;img.loading='lazy';b.setAttribute('aria-label','放大 '+p.title);b.append(img);b.onclick=()=>openPhoto(filtered.indexOf(p),filtered);title.textContent=p.title;desc.textContent=p.caption;cap.append(title,desc);f.append(b,cap);$('photo-grid').append(f);}}
  renderPhotos('all');
  for(const p of library.featured(config.featuredPhotos)){const b=document.createElement('button'),img=document.createElement('img'),frame=document.createElement('span'),title=document.createElement('span');frame.className='photo-frame';title.className='featured-caption';img.src='assets/photos/'+p.file;img.alt=p.title;img.width=1600;img.height=p.source.includes('去浮水印')?1104:1200;img.loading='lazy';title.textContent=p.title;b.setAttribute('aria-label','放大 '+p.title);frame.append(img);b.append(frame,title);b.onclick=()=>openPhoto(photos.indexOf(p),photos);$('featured-photos').append(b);}
  $('view-all-photos').onclick=()=>{renderPhotos('all');tab('photos');};
  $('show-room-photos').onclick=()=>{renderPhotos(library.categoryForRoom(selectedRoom));tab('photos');};
  function showPhoto(){const p=photoSet[photoIndex];$('photo-title').textContent=p.title;$('photo-large').src='assets/photos/'+p.file;$('photo-large').alt=p.title;$('photo-caption').textContent=p.caption;$('photo-counter').textContent=(photoIndex+1)+' / '+photoSet.length;}
  function openPhoto(index,collection=photos){photoSet=collection;photoIndex=index;planOpen=false;document.querySelector('.dialog-nav').hidden=false;showPhoto();$('photo-dialog').showModal();}
  $('photo-prev').onclick=()=>{photoIndex=(photoIndex+photoSet.length-1)%photoSet.length;showPhoto();};$('photo-next').onclick=()=>{photoIndex=(photoIndex+1)%photoSet.length;showPhoto();};
  $('close-dialog').onclick=()=>$('photo-dialog').close();
  $('enlarge-plan').onclick=()=>{planOpen=true;$('photo-title').textContent='原始格局圖';$('photo-large').src='assets/floorplan.jpg';$('photo-large').alt='原始概繪格局圖';$('photo-caption').textContent='原始概繪圖，非一定比例，實際以現場為準。';document.querySelector('.dialog-nav').hidden=true;$('photo-dialog').showModal();};
  for(let i=0;i<config.slides.length;i++){const b=document.createElement('button');b.textContent=i+1;b.setAttribute('aria-label','簡報第 '+(i+1)+' 頁');b.onclick=()=>showSlide(i);$('slide-dots').append(b);}
  function showSlide(i){slideIndex=Math.max(0,Math.min(config.slides.length-1,i));const s=config.slides[slideIndex];$('slide-counter').textContent=String(slideIndex+1).padStart(2,'0')+' / 05';$('slide-title').textContent=s.title;$('slide-eyebrow').textContent=s.eyebrow;$('slide-body').textContent=s.body;$('slide-points').replaceChildren(...s.points.map(t=>{const li=document.createElement('li');li.textContent=t;return li;}));$('slide-image').src=s.image;$('slide-image').alt=s.alt;$('slide-image').classList.toggle('plan-image',!!s.plan);$('slide-contact').hidden=!s.contact;slidePrice.hidden=!s.contact;$('slide-prev').disabled=slideIndex===0;$('slide-next').disabled=slideIndex===4;[...$('slide-dots').children].forEach((b,j)=>b.setAttribute('aria-current',j===slideIndex));}
  $('slide-prev').onclick=()=>showSlide(slideIndex-1);$('slide-next').onclick=()=>showSlide(slideIndex+1);showSlide(0);
  document.addEventListener('keydown',e=>{if(e.target.closest('[role=tablist]'))return;if($('photo-dialog').open&&!planOpen){if(e.key==='ArrowLeft')$('photo-prev').click();if(e.key==='ArrowRight')$('photo-next').click();}else if(currentTab==='report'&&!$('photo-dialog').open){if(e.key==='ArrowLeft')showSlide(slideIndex-1);if(e.key==='ArrowRight')showSlide(slideIndex+1);if(e.key==='Escape')tab('explore',true);}});
})();
