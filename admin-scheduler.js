(()=>{
  const $=id=>document.getElementById(id);
  const OWNER='ClairVoyanceMedium';
  const REPO='app-clairvoyancemedium.github.io';
  const FULL=OWNER+'/'+REPO;
  const API='https://api.github.com';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));

  const sendBtn=$('sendBtn');
  const targetField=$('pushTarget')?.closest('.field');
  const preview=document.querySelector('.preview');
  const status=$('pushStatus');
  if(!sendBtn||!targetField||!preview||!status)return;

  const wrap=document.createElement('div');
  wrap.innerHTML=`
    <div class="field" id="deliveryModeField">
      <label>Programmation de l’envoi</label>
      <select id="deliveryMode">
        <option value="now">Envoyer maintenant</option>
        <option value="scheduled">Programmer une date et une heure</option>
        <option value="smart_last_active">Moment intelligent selon l’activité de chaque abonné</option>
        <option value="local_time">Même heure locale pour chaque abonné</option>
      </select>
    </div>
    <div class="field hidden" id="scheduleDateField">
      <label>Date et heure</label>
      <input id="sendAfter" type="datetime-local" step="60">
      <div class="note" id="scheduleTimezone"></div>
    </div>
    <div class="field hidden" id="localTimeField">
      <label>Heure locale de chaque abonné</label>
      <input id="deliveryTime" type="time" value="19:00" step="60">
      <div class="note">Exemple : 19:00 enverra à 19 h dans le fuseau horaire propre à chaque abonné.</div>
    </div>
    <div class="status" id="deliveryHelp">Envoi immédiat dès validation.</div>
  `;
  preview.parentNode.insertBefore(wrap,preview);

  const deliveryMode=$('deliveryMode');
  const scheduleDateField=$('scheduleDateField');
  const localTimeField=$('localTimeField');
  const sendAfter=$('sendAfter');
  const deliveryTime=$('deliveryTime');
  const deliveryHelp=$('deliveryHelp');
  const scheduleTimezone=$('scheduleTimezone');

  function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function setStatus(msg,type=''){status.className='status'+(type?' '+type:'');status.innerHTML=msg}
  function token(){return localStorage.getItem('cvm_admin_token')||sessionStorage.getItem('cvm_admin_token')||''}
  function headers(){return {'Authorization':'Bearer '+token(),'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}}
  async function gh(url,opts={}){const r=await fetch(url,{...opts,headers:{...headers(),...(opts.headers||{})}});if(!r.ok)throw new Error('GitHub '+r.status+' '+await r.text());return r}
  async function dispatch(inputs){const r=await fetch(API+'/repos/'+FULL+'/actions/workflows/send-push.yml/dispatches',{method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify({ref:'main',inputs})});if(r.status!==204)throw new Error('GitHub '+r.status+' '+await r.text())}
  async function latestPushRun(){try{const j=await(await gh(API+'/repos/'+FULL+'/actions/workflows/send-push.yml/runs?per_page=5')).json();return(j.workflow_runs||[])[0]||null}catch{return null}}

  function localInputValue(date){
    const p=n=>String(n).padStart(2,'0');
    return date.getFullYear()+'-'+p(date.getMonth()+1)+'-'+p(date.getDate())+'T'+p(date.getHours())+':'+p(date.getMinutes());
  }
  function defaultFuture(){
    const d=new Date(Date.now()+60*60*1000);
    d.setSeconds(0,0);
    d.setMinutes(Math.ceil(d.getMinutes()/5)*5);
    sendAfter.value=localInputValue(d);
  }

  function updateMode(){
    const mode=deliveryMode.value;
    scheduleDateField.classList.toggle('hidden',mode!=='scheduled');
    localTimeField.classList.toggle('hidden',mode!=='local_time');
    if(mode==='scheduled'&&!sendAfter.value)defaultFuture();
    const tz=Intl.DateTimeFormat().resolvedOptions().timeZone||'fuseau de cet appareil';
    scheduleTimezone.textContent='Heure saisie dans votre fuseau : '+tz+'. Elle sera convertie automatiquement pour OneSignal.';
    if(mode==='now'){
      deliveryHelp.textContent='Envoi immédiat dès validation.';
      sendBtn.textContent='Envoyer maintenant';
    }else if(mode==='scheduled'){
      deliveryHelp.textContent='La notification sera créée maintenant puis envoyée automatiquement à la date et à l’heure choisies.';
      sendBtn.textContent='Programmer la notification';
    }else if(mode==='smart_last_active'){
      deliveryHelp.textContent='OneSignal choisira automatiquement le moment de livraison selon l’historique d’activité récent de chaque abonné.';
      sendBtn.textContent='Programmer intelligemment';
    }else{
      deliveryHelp.textContent='Chaque abonné recevra la notification à la même heure locale, même s’il se trouve dans un autre pays.';
      sendBtn.textContent='Programmer par heure locale';
    }
  }

  deliveryMode.addEventListener('change',updateMode);
  updateMode();

  const historyNote=[...document.querySelectorAll('.note')].find(x=>x.textContent.includes('Historique synchronisé depuis OneSignal'));
  if(historyNote)historyNote.textContent+=' Les notifications programmées apparaissent « En traitement » jusqu’à leur livraison.';

  async function sendScheduledAware(){
    const title=$('pushTitle').value.trim();
    const message=$('pushMessage').value.trim();
    if(!title||!message){setStatus('Titre et message obligatoires.','bad');return}

    const mode=deliveryMode.value;
    let sendAfterIso='';
    let deliveryTimeValue='';
    let confirmText='Envoyer cette notification maintenant ?';

    if(mode==='scheduled'){
      if(!sendAfter.value){setStatus('Choisissez une date et une heure pour programmer la notification.','bad');return}
      const d=new Date(sendAfter.value);
      if(Number.isNaN(d.getTime())){setStatus('Date ou heure invalide.','bad');return}
      if(d.getTime()<=Date.now()+30000){setStatus('La date programmée doit être dans le futur.','bad');return}
      sendAfterIso=d.toISOString();
      confirmText='Programmer cette notification pour le '+new Intl.DateTimeFormat('fr-FR',{dateStyle:'full',timeStyle:'short'}).format(d)+' ?';
    }else if(mode==='smart_last_active'){
      confirmText='Confirmer la programmation intelligente selon l’activité de chaque abonné ?';
    }else if(mode==='local_time'){
      deliveryTimeValue=deliveryTime.value;
      if(!deliveryTimeValue){setStatus('Choisissez l’heure locale d’envoi.','bad');return}
      confirmText='Programmer cette notification à '+deliveryTimeValue+' dans le fuseau local de chaque abonné ?';
    }

    if(!confirm(confirmText))return;
    sendBtn.disabled=true;
    try{
      const before=await latestPushRun();
      setStatus(mode==='now'?'Transmission à GitHub Actions puis vérification du résultat…':'Création de la programmation dans OneSignal…','warn');
      await dispatch({
        title,
        message,
        url:$('pushUrl').value.trim(),
        image_url:$('pushImage').value.trim(),
        target:$('pushTarget').value,
        delivery_mode:mode,
        send_after:sendAfterIso,
        delivery_time:deliveryTimeValue||'19:00'
      });

      let run=null;
      for(let i=0;i<24;i++){
        await sleep(2500);
        const candidate=await latestPushRun();
        if(candidate&&(!before||candidate.id!==before.id)){
          run=candidate;
          if(run.status==='completed')break;
        }
        setStatus((mode==='now'?'Envoi':'Programmation')+' en cours… vérification '+(i+1)+'/24.','warn');
      }

      if(!run||run.status!=='completed'){
        setStatus('La demande a bien été transmise, mais le résultat prend plus de temps que prévu. Appuyez sur Actualiser dans quelques instants.','warn');
        return;
      }

      if(run.conclusion==='success'){
        if(mode==='now')setStatus('Notification acceptée par OneSignal. Synchronisation de l’historique et des statistiques en cours…','good');
        else if(mode==='scheduled')setStatus('Notification programmée avec succès pour '+esc(new Intl.DateTimeFormat('fr-FR',{dateStyle:'short',timeStyle:'short'}).format(new Date(sendAfterIso)))+'.','good');
        else if(mode==='smart_last_active')setStatus('Programmation intelligente acceptée par OneSignal. Le moment de livraison sera adapté à l’activité de chaque abonné.','good');
        else setStatus('Programmation acceptée. Chaque abonné recevra la notification à '+esc(deliveryTimeValue)+' dans son heure locale.','good');
        setTimeout(()=>{$('syncBtn')?.click()},1200);
      }else{
        setStatus('Échec de '+(mode==='now'?'l’envoi':'la programmation')+' ('+esc(run.conclusion)+'). Le détail exact est enregistré dans GitHub Actions.','bad');
      }
    }catch(e){
      setStatus('Envoi impossible : '+esc(e.message),'bad');
    }finally{
      sendBtn.disabled=false;
    }
  }

  sendBtn.onclick=sendScheduledAware;
})();

(()=>{
  const script=document.createElement('script');
  script.src='admin-installs.js?v=20260916-1';
  script.defer=true;
  document.body.appendChild(script);
})();
