import { AppBridge } from '@modelcontextprotocol/ext-apps/app-bridge';
import { PostMessageTransport } from '@modelcontextprotocol/ext-apps';
const iframe=document.getElementById('app') as HTMLIFrameElement;
await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json','X-Canvas-Dashboard':'1'},body:JSON.stringify({secret:'synthetic-ui-session'})});
const bridge=new AppBridge(null,{name:'Synthetic verification host',version:'1'}, {serverTools:{}},
  {hostContext:{toolInfo:{tool:{name:'test__canvas_open_student_dashboard',inputSchema:{type:'object'}}}}});
bridge.oncalltool=async(params)=>{
  if(params.name!=='test__canvas_dashboard_data') throw new Error('Incorrect tool namespace');
  const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-Canvas-Dashboard':'1'},body:JSON.stringify(params.arguments?.request)});
  const data=await response.json();
  return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,isError:!response.ok};
};
await bridge.connect(new PostMessageTransport(iframe.contentWindow!,iframe.contentWindow!));
iframe.srcdoc=await (await fetch('/test-native')).text();
