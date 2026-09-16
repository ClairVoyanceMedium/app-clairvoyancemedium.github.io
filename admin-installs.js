(()=>{
  const OWNER='ClairVoyanceMedium';
  const REPO='app-clairvoyancemedium.github.io';
  const FULL=OWNER+'/'+REPO;
  const API='https://api.github.com';
  const $=id=>document.getElementById(id);
  const dashboard=$('dashboard');
  if(!dashboard)return;

  const panel=document.createElement('section');
  panel.className='panel';
  panel.style.marginTop='13px';
  panel.id='installationsPanel';
  panel.innerHTML=`
    <div class="section-title">
      <h2>Installations détectées</h2>
      <span id="installFeedCount">0 installation</span>
    </div>
    <div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:12px">
      <div class="metric"><div class="k">Installations suivies</div><div class="v" id="installTotal">—</div><div class="s">Depuis l’activation du suivi</div></div>
      <div class="metric"><div class="k">Nouvelles 24 h</div><div class="v" id="install24">—</div><div class="s">Premières détections</div></div>
      <div class="metric"><div class="k">Téléchargements APK</div><div class="v" id="installApkDownloads">—</div><div class="s">Compteur GitHub cumulatif</div></div>
    </div>
    <div class="history-filters">
      <input id="installSearch" placeholder="Rechercher appareil, pays, plateforme, identifiant…">
      <select id="installPlatform"><option value="">Toutes plateformes</option><option value="Android">Android</option><option value="iOS natif">iPhone / iPad</option><option value="iOS / iPadOS Web Push">iOS Web Push</option><option value="Web Chrome">Web Chrome</option><option value="Safari Web Push">Safari Web Push</option></select>
    </div>
    <div class="table-wrap"><table style="min-width:1180px">
      <thead><tr><th>Détection</th><th>ID anonyme</th><th>Plateforme</th><th>Appareil</th><th>OS</th><th>Version</th><th>Pays</th><th>Fuseau</th><th>Langue</th><th>Push</th><th>Sessions</th><th>Dernière activité</th></tr></thead>
      <tbody id="installationsBody"><tr><td colspan="12">Chargement…</td></tr></tbody>
    </table></div>
    <p class="note" id="installPrivacy">Une « installation détectée » correspond à la première ouverture enregistrée par l’application/OneSignal, pas à l’identité civile de la personne. L’identifiant est technique et anonyme. Le pays est approximatif et issu du réseau. Aucune localisation GPS n’est ajoutée.</p>
  `;

  const subscriptionsPanel=[...dashboard.querySelectorAll('section.panel')].find(x=>x.textContent.includes('Abonnements et appareils'));
  if(subscriptionsPanel)dashboard.insertBefore(panel,subscriptionsPanel);
  else dashboard.appendChild(panel);

  let installData=[];
  let summary={};

  function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function token(){return localStorage.getItem('cvm_admin_token')||sessionStorage.getItem('cvm_admin_token')||''}
  function headers(){return {'Authorization':'Bearer '+token(),'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}}
  function fmt(v){if(!v)return'—';try{return new Intl.DateTimeFormat('fr-FR',{dateStyle:'short',timeStyle:'short'}).format(new Date(v))}catch{return String(v)}}
  async function gh(url,opts={}){const r=await fetch(url,{...opts,headers:{...headers(),...(opts.headers||{})}});if(!r.ok)throw new Error('GitHub '+r.status);return r}

  function render(){
    let rows=[...installData];
    const q=$('installSearch').value.trim().toLowerCase();
    const p=$('installPlatform').value;
    if(p)rows=rows.filter(x=>x.platform===p);
    if(q)rows=rows.filter(x=>JSON.stringify(x).toLowerCase().includes(q));

    $('installTotal').textContent=Number(summary.installations_detected||0).toLocaleString('fr-FR');
    $('install24').textContent=Number(summary.installations_last_24h||0).toLocaleString('fr-FR');
    $('installApkDownloads').textContent=Number(summary.apk_downloads||0).toLocaleString('fr-FR');
    $('installFeedCount').textContent=rows.length+(rows.length!==installData.length?' / '+installData.length:'')+' installation'+(installData.length>1?'s':'');

    $('installationsBody').innerHTML=rows.length?rows.map(x=>`<tr>
      <td data-label="Détection">${esc(fmt(x.detected_at))}</td>
      <td data-label="ID anonyme"><span class="pill">${esc(x.anonymous_id||'—')}</span></td>
      <td data-label="Plateforme">${esc(x.platform||'—')}</td>
      <td data-label="Appareil">${esc(x.device_model||'—')}</td>
      <td data-label="OS">${esc(x.device_os||'—')}</td>
      <td data-label="Version">${esc(x.app_version||'—')}</td>
      <td data-label="Pays">${esc(x.country||'—')}</td>
      <td data-label="Fuseau">${esc(x.timezone||'—')}</td>
      <td data-label="Langue">${esc(x.language||'—')}</td>
      <td data-label="Push"><span class="pill ${x.push_status==='activé'?'on':x.push_status==='non autorisé'?'pending':'off'}">${esc(x.push_status||'—')}</span></td>
      <td data-label="Sessions">${Number(x.session_count||0)}</td>
      <td data-label="Dernière activité">${esc(fmt(x.last_active))}</td>
    </tr>`).join(''):'<tr><td colspan="12">Aucune nouvelle installation détectée depuis l’activation du suivi.</td></tr>';
  }

  async function loadInstallations(){
    if(!token())return;
    try{
      const artifacts=await(await gh(API+'/repos/'+FULL+'/actions/artifacts?per_page=100')).json();
      const latest=(artifacts.artifacts||[])
        .filter(a=>a.name==='ClairVoyanceMedium-metrics'&&!a.expired)
        .sort((a,b)=>new Date(b.created_at)-new Date(a.created_at))[0];
      if(!latest)throw new Error('Aucune métrique disponible');
      const blob=await(await gh(API+'/repos/'+FULL+'/actions/artifacts/'+latest.id+'/zip')).blob();
      const zip=await JSZip.loadAsync(blob);
      const file=zip.file('metrics-private.json');
      if(!file)throw new Error('metrics-private.json absent');
      const data=JSON.parse(await file.async('string'));
      summary=data.summary||{};
      installData=Array.isArray(data.installations)?data.installations:[];
      render();
    }catch(e){
      $('installationsBody').innerHTML='<tr><td colspan="12">Journal des installations momentanément indisponible. Utilisez « Synchroniser les métriques » puis réessayez.</td></tr>';
    }
  }

  $('installSearch').addEventListener('input',render);
  $('installPlatform').addEventListener('input',render);
  $('refreshBtn')?.addEventListener('click',()=>setTimeout(loadInstallations,600));
  $('syncBtn')?.addEventListener('click',()=>setTimeout(loadInstallations,12000));
  $('loginBtn')?.addEventListener('click',()=>setTimeout(loadInstallations,1800));

  if(token())setTimeout(loadInstallations,700);
  const observer=new MutationObserver(()=>{
    if(!dashboard.classList.contains('hidden')&&token())loadInstallations();
  });
  observer.observe(dashboard,{attributes:true,attributeFilter:['class']});
})();
