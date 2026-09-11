const CACHE_NAME='cvm-ios-v1';
const APP_SHELL=['./ios-app.html','./manifest-ios.webmanifest'];

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(APP_SHELL)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate',event=>{
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;
  event.respondWith(fetch(event.request).catch(()=>caches.match(event.request)));
});

self.addEventListener('push',event=>{
  let data={};
  try{data=event.data?event.data.json():{};}catch(e){data={body:event.data?event.data.text():''};}
  const title=data.title||'ClairVoyanceMedium.com';
  const options={
    body:data.body||'Vous avez une nouvelle notification.',
    icon:data.icon||'./assets/app_icon.png',
    badge:data.badge||'./assets/app_icon-192.png',
    data:{url:data.url||'https://www.clairvoyancemedium.com/'},
    tag:data.tag||'clairvoyancemedium',
    renotify:Boolean(data.renotify)
  };
  event.waitUntil(self.registration.showNotification(title,options));
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const url=(event.notification.data&&event.notification.data.url)||'https://www.clairvoyancemedium.com/';
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>{
    for(const client of list){
      if('focus' in client){client.navigate(url);return client.focus();}
    }
    return clients.openWindow?clients.openWindow(url):undefined;
  }));
});
