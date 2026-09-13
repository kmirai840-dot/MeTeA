export default function(){
 let current,selected,month;
 const media=window.matchMedia('(max-width:767px)');
 function init(){
 const root=document.querySelector('#metea-mobile-calendar'); if(!media.matches || !root || root===current)return; current=root;
 const today=root.dataset.today;
 const parse=s=>{const [y,m,d]=s.split('-').map(Number);return new Date(y,m-1,d)};
 const iso=d=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
 if(!selected){selected=today;month=parse(today);month.setDate(1);}
 const cards=Array.from(root.querySelectorAll('[data-event-day]'));
 const grid=root.querySelector('.mobile-calendar-grid');
 function draw(){
  root.querySelector('.mobile-calendar-month').textContent=`${month.getFullYear()}年${month.getMonth()+1}月`;
  grid.replaceChildren();
  ['月','火','水','木','金','土','日'].forEach(x=>{const h=document.createElement('div');h.className='mobile-calendar-weekday';h.textContent=x;grid.append(h)});
  const first=new Date(month);first.setDate(1-((first.getDay()+6)%7));
  for(let i=0;i<42;i++){
   const d=new Date(first);d.setDate(first.getDate()+i);const key=iso(d);
   const items=cards.filter(c=>c.dataset.eventDay===key);
   const button=document.createElement('button');button.type='button';button.className='mobile-calendar-day'+(d.getMonth()!==month.getMonth()?' outside':'')+(key===today?' today':'');
   button.setAttribute('aria-label',`${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日、予定${items.length}件`);
   button.setAttribute('aria-pressed',String(key===selected));
   const num=document.createElement('span');num.className='mobile-calendar-number';num.textContent=d.getDate();button.append(num);
   items.slice(0,2).forEach(c=>{const chip=document.createElement('span');chip.className='mobile-calendar-chip '+c.dataset.state;const company=document.createElement('span');company.textContent=c.dataset.companyShort;const title=document.createElement('span');title.textContent=c.dataset.eventTitle;chip.append(company,title);button.append(chip)});
   if(items.length>2){const more=document.createElement('span');more.className='mobile-calendar-more';more.textContent=`他${items.length-2}件`;button.append(more)}
   button.onclick=()=>{selected=key;draw()};grid.append(button);
  }
  const d=parse(selected);
  root.querySelector('.mobile-calendar-selected').textContent=`${d.getMonth()+1}月${d.getDate()}日（${'日月火水木金土'[d.getDay()]}）の予定`;
  let count=0;cards.forEach(c=>{if(c.dataset.eventDay){c.hidden=c.dataset.eventDay!==selected;if(!c.hidden)count++}});
  root.querySelector('.mobile-calendar-empty').hidden=count>0;
 }
 root.querySelectorAll('[data-month-step]').forEach(b=>b.onclick=()=>{month.setMonth(month.getMonth()+Number(b.dataset.monthStep));selected=iso(month);draw()});
 root.querySelector('[data-calendar-today]').onclick=()=>{selected=today;month=parse(today);month.setDate(1);draw()};
 root.querySelectorAll('[data-calendar-application]').forEach(card=>card.onclick=()=>{
 const label='予定登録::'+card.dataset.calendarApplication;
 const button=Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===label);
 if(button)button.click();
 });
 draw();

 }
 const observer=new MutationObserver(init);observer.observe(document.body,{childList:true,subtree:true});media.addEventListener('change',init);init();
 return ()=>{observer.disconnect();media.removeEventListener('change',init);};
}
