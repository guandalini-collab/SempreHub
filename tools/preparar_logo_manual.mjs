import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
let chromium;
try { ({chromium}=require('playwright')); }
catch { ({chromium}=require(process.env.HOME+'/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')); }
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
 const page=await browser.newPage();
 await page.setContent('<html><head><style>@page{margin:0}html,body{margin:0;background:white}svg{display:block}</style></head><body>'+fs.readFileSync('docs/assets/semprehub-fundo-branco.svg','utf8').replace(/<\?xml[^>]*>|<!DOCTYPE[^>]*>/g,'')+'</body></html>');
 const size=await page.evaluate(()=>{
  const svg=document.querySelector('svg');
  const boxes=[...svg.querySelectorAll('path')].filter(p=>getComputedStyle(p).fill!=='rgb(255, 255, 255)').map(p=>p.getBBox());
  const left=Math.min(...boxes.map(b=>b.x)),top=Math.min(...boxes.map(b=>b.y));
  const right=Math.max(...boxes.map(b=>b.x+b.width)),bottom=Math.max(...boxes.map(b=>b.y+b.height));
  const padding=100,w=right-left+padding*2,h=bottom-top+padding*2;
  svg.setAttribute('viewBox',`${left-padding} ${top-padding} ${w} ${h}`);
  svg.setAttribute('width','600');svg.setAttribute('height',String(600*h/w));
  return {width:600,height:600*h/w};
 });
 await page.pdf({path:'docs/assets/semprehub-fundo-branco.pdf',width:size.width+'px',height:size.height+'px',printBackground:true,margin:{top:0,bottom:0,left:0,right:0}});
 console.log('Marca vetorial preparada a partir do SVG original:',size);
} finally {await browser.close();}
