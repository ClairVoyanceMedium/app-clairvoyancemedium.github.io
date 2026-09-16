(()=>{
  'use strict';

  const OWNER='ClairVoyanceMedium';
  const REPO='app-clairvoyancemedium.github.io';
  const FULL=OWNER+'/'+REPO;
  const API='https://api.github.com';
  const RESET_KEY='cvm_section_resets_v1';
  const BASE_KEY='cvm_metrics_baseline_v1';
  const $=id=>document.getElementById(id);
  const dashboard=$('dashboard');
  if(!dashboard)return;

  function token(){return localStorage.getItem('cvm_admin_token')||sessionStorage.getItem('cvm_admin_token')||''}
  function headers(){return {'Authorization':'Bearer '+token(),'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}}
  async function gh(url,opts={}){const r=await fetch(url,{...opts,headers:{...headers(),...(opts.headers||{})}});if(!r.ok)throw new Error('GitHub '+r.status+' '+await r.text());return r}
  function status(msg,type='good'){const el=$('pushStatus');if(!el)return;el.className='status '+type;el.textContent=msg}
  function readResets(){try{return JSON.parse(localStorage.getItem(RESET_KEY)||'{}')||{}}catch{return{}}}
  function writeResets(value){localStorage.setItem(RESET_KEY,JSON.stringify(value))}
  function cutoff(name){const v=Number(readResets()[name]||0);return Number.isFinite(v)?v:0}
  function setCutoff(name,ts=Date.now()){const r=readResets();r[name]=ts;writeResets(r);applyAllSoon()}

  function parseDisplayedDate(text){
    const raw=String(text||'').replace(/\u202f/g,' ').trim();
    const m=raw.match(/(\d{1,2})\/(\d{1,2})\/(\d{2,4})[^\d]+(\d{1,2}):(\d{2})(?::(\d{2}))?/);
    if(!m)return NaN;
    let year=Number(m[3]);if(year<100)year+=2000;
    return new Date(year,Number(m[2])-1,Number(m[1]),Number(m[4]),Number(m[5]),Number(m[6]||0),0).getTime();
  }

  function resetHiddenRows(bodyId,label,resetName){
    const body=$(bodyId);if(!body)return{visible:0,dates:[]};
    const limit=cutoff(resetName);
    let visible=0;
    const dates=[];
    [...body.querySelectorAll('tr')].forEach(row=>{
      if(row.classList.contains('cvm-reset-placeholder'))return;
      const cell=row.querySelector(`[data-label="${label}"]`);
      if(!cell)return;
      const when=parseDisplayedDate(cell.textContent);
      const hidden=Boolean(limit&&Number.isFinite(when)&&when<=limit);
      row.style.display=hidden?'none':'';
      row.dataset.cvmResetHidden=hidden?'1':'0';
      if(!hidden){visible++;if(Number.isFinite(when))dates.push(when)}
    });
    return{visible,dates};
  }

  function addPlaceholder(bodyId,colspan,text){
    const body=$(bodyId);if(!body)return;
    const visible=[...body.querySelectorAll('tr')].some(row=>!row.classList.contains('cvm-reset-placeholder')&&row.style.display!=='none'&&row.querySelector('[data-label]'));
    let placeholder=body.querySelector('.cvm-reset-placeholder');
    if(!visible){
      if(!placeholder){
        placeholder=document.createElement('tr');placeholder.className='cvm-reset-placeholder';
        const td=document.createElement('td');td.colSpan=colspan;placeholder.appendChild(td);body.appendChild(placeholder);
      }
      placeholder.firstElementChild.textContent=text;
    }else if(placeholder){
      placeholder.remove();
    }
  }

  let applying=false;
  function applyFilters(){
    if(applying)return;applying=true;
    try{
      const msg=resetHiddenRows('messagesBody','Date','messages');
      if(cutoff('messages')){
        const c=$('msgCount');if(c)c.textContent=msg.visible+' notification'+(msg.visible>1?'s':'')+' depuis la remise à zéro';
        addPlaceholder('messagesBody',8,'Historique remis à zéro. Les prochaines notifications apparaîtront ici.');
      }

      const sub=resetHiddenRows('subscriptionsBody','Première détection','subscriptions');
      if(cutoff('subscriptions')){
        const c=$('subCount');if(c)c.textContent=sub.visible+' ligne'+(sub.visible>1?'s':'')+' depuis la remise à zéro';
        addPlaceholder('subscriptionsBody',12,'Liste remise à zéro. Les nouveaux abonnements et appareils apparaîtront ici.');
      }

      const installs=resetHiddenRows('installationsBody','Détection','installations');
      if(cutoff('installations')){
        const c=$('installFeedCount');if(c)c.textContent=installs.visible+' installation'+(installs.visible>1?'s':'')+' depuis la remise à zéro';
        if($('installTotal'))$('installTotal').textContent=String(installs.visible);
        if($('install24')){
          const now=Date.now();
          $('install24').textContent=String(installs.dates.filter(t=>now-t<=86400000).length);
        }
        addPlaceholder('installationsBody',12,'Installations remises à zéro. Les prochaines détections apparaîtront ici.');
      }
    }finally{applying=false}
  }

  let timer=null;
  function applyAllSoon(){clearTimeout(timer);timer=setTimeout(applyFilters,40)}

  function makeResetButton(id,label,onClick){
    const b=document.createElement('button');
    b.type='button';b.id=id;b.className='btn danger';b.textContent=label;b.addEventListener('click',onClick);return b;
  }

  function titleActions(section){
    const title=section?.querySelector('.section-title');if(!title)return null;
    let wrap=title.querySelector('.cvm-reset-actions');
    if(!wrap){
      wrap=document.createElement('div');wrap.className='cvm-reset-actions actions';wrap.style.marginLeft='auto';title.appendChild(wrap);
    }
    return wrap;
  }

  function installSectionButtons(){
    const sections=[...dashboard.querySelectorAll('section.panel')];
    const history=sections.find(x=>x.querySelector('h2')?.textContent.includes('Historique des notifications push'));
    const subs=sections.find(x=>x.querySelector('h2')?.textContent.includes('Abonnements et appareils'));
    const installs=$('installationsPanel');

    if(history&&!$('resetPushHistoryBtn')){
      titleActions(history)?.appendChild(makeResetButton('resetPushHistoryBtn','Remettre l’historique à zéro',()=>{
        if(!confirm('Masquer tout l’historique des notifications jusqu’à maintenant et repartir de zéro ?\n\nAucune donnée OneSignal ne sera supprimée.'))return;
        setCutoff('messages');status('Historique des notifications remis à zéro. Les prochains envois apparaîtront normalement.');
      }));
    }
    if(subs&&!$('resetSubscriptionsBtn')){
      titleActions(subs)?.appendChild(makeResetButton('resetSubscriptionsBtn','Remettre la liste à zéro',()=>{
        if(!confirm('Masquer les abonnements et appareils déjà connus et repartir de zéro ?\n\nLes abonnements OneSignal restent actifs et continueront de recevoir les notifications.'))return;
        setCutoff('subscriptions');status('Liste des abonnements et appareils remise à zéro sans désabonner personne.');
      }));
    }
    if(installs&&!$('resetInstallsBtn')){
      titleActions(installs)?.appendChild(makeResetButton('resetInstallsBtn','Remettre à zéro',()=>{
        if(!confirm('Masquer les installations déjà détectées et repartir de zéro ?\n\nLe suivi continuera automatiquement pour les prochaines installations.'))return;
        setCutoff('installations');status('Installations détectées remises à zéro. Les prochaines seront enregistrées normalement.');
      }));
    }

    const topActions=document.querySelector('.top>.actions');
    if(topActions&&!$('resetEverythingBtn')){
      const b=makeResetButton('resetEverythingBtn','Tout remettre à zéro',resetEverything);
      topActions.insertBefore(b,$('logoutBtn')||null);
    }
    const resetAll=$('resetEverythingBtn');
    if(resetAll)resetAll.classList.toggle('hidden',dashboard.classList.contains('hidden'));
  }

  async function latestMetrics(){
    const artifacts=await(await gh(API+'/repos/'+FULL+'/actions/artifacts?per_page=100')).json();
    const latest=(artifacts.artifacts||[]).filter(a=>a.name==='ClairVoyanceMedium-metrics'&&!a.expired).sort((a,b)=>new Date(b.created_at)-new Date(a.created_at))[0];
    if(!latest)throw new Error('Aucune métrique disponible');
    const blob=await(await gh(API+'/repos/'+FULL+'/actions/artifacts/'+latest.id+'/zip')).blob();
    const zip=await JSZip.loadAsync(blob);const file=zip.file('metrics-private.json');
    if(!file)throw new Error('metrics-private.json absent');
    return JSON.parse(await file.async('string'));
  }

  async function currentApkDownloads(){
    try{
      const release=await(await gh(API+'/repos/'+FULL+'/releases/tags/android-latest')).json();
      const asset=(release.assets||[]).find(x=>x.name==='ClairVoyanceMedium.apk');
      return Number(asset?.download_count||0);
    }catch{return 0}
  }

  async function resetEverything(){
    if(!confirm('Tout remettre à zéro dans le tableau de bord ?\n\nCela remettra les compteurs, l’historique push, les installations et les listes d’appareils à zéro. Aucune donnée OneSignal ne sera supprimée et aucun abonné ne sera désabonné.'))return;
    const b=$('resetEverythingBtn');if(b)b.disabled=true;
    try{
      const data=await latestMetrics();
      const s=data.summary||{};
      const apk=await currentApkDownloads();
      const keys=['subscribed','android_subscribed','ios_web_subscribed','unsubscribed','new_last_24h','active_7d','active_30d','apk_downloads','sessions_total','notifications_sent_recent','notifications_clicked_recent'];
      const base={reset_at:new Date().toISOString(),summary:{}};
      keys.forEach(k=>base.summary[k]=Number(k==='apk_downloads'?(s[k]??apk??0):(s[k]??0)));
      localStorage.setItem(BASE_KEY,JSON.stringify(base));
      const now=Date.now();writeResets({messages:now,subscriptions:now,installations:now});
      status('Tout le tableau de bord a été remis à zéro sans supprimer les données sources ni désabonner les utilisateurs.');
      applyAllSoon();
      setTimeout(()=>$('refreshBtn')?.click(),150);
    }catch(e){
      status('Remise à zéro impossible : '+e.message,'bad');
    }finally{if(b)b.disabled=false}
  }

  const observer=new MutationObserver(()=>{installSectionButtons();applyAllSoon()});
  observer.observe(dashboard,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});

  const style=document.createElement('style');
  style.textContent=`
    .cvm-reset-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}
    .cvm-reset-actions .btn{min-height:36px;padding:7px 10px;font-size:11px}
    @media(max-width:700px){
      .section-title{align-items:flex-start;flex-wrap:wrap}
      .cvm-reset-actions{width:100%;margin-left:0!important}
      .cvm-reset-actions .btn{width:100%}
    }
  `;
  document.head.appendChild(style);

  installSectionButtons();
  applyAllSoon();
})();
