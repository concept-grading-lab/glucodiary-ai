self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('push',event=>{
  let data={title:'GlucoDiary reminder',body:'A scheduled reminder is due.',url:'/'};
  try{data={...data,...event.data.json()}}catch(e){}
  event.waitUntil(self.registration.showNotification(data.title,{body:data.body,icon:'/icon.svg',badge:'/icon.svg',tag:'glucodiary-reminder',data:{url:data.url||'/'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(clients=>{
    for(const c of clients){if(c.url.startsWith(self.location.origin)){c.focus();return}}
    return self.clients.openWindow(event.notification.data?.url||'/');
  }));
});
