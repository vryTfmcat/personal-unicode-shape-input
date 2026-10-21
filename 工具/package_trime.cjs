// Baseline installer, or package a validated editor backup. Never changes desktop codebooks.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),W=require('../原型/键位编辑器/touch/workspace-core.js'),C=require('../原型/键位编辑器/touch/core.js');
const editor=path.join(root,'原型/键位编辑器/touch'),catalog=JSON.parse(fs.readFileSync(path.join(editor,'catalog.json'),'utf8')),byId=new Map(catalog.characters.map(c=>[c[0],{char:c[1]}]));
const manifest=JSON.parse(fs.readFileSync(path.join(editor,'trime-base/manifest.json'),'utf8'));
const profile=process.argv[2]?W.validate(JSON.parse(fs.readFileSync(process.argv[2],'utf8')).profile,new Set(byId.keys())):{version:2,entries:catalog.personal||{},mobileKeys:{},recent:[]};
const layout=process.argv[2]?C.validate(JSON.parse(fs.readFileSync(process.argv[2],'utf8')).layout,new Set(byId.keys())):{format:C.FORMAT,tiles:[],bindings:{}};
const id='unicode-android-0.2.4-'+manifest.id,extras=W.extras(profile,byId,id,manifest.fonts||[]);extras['unicode-workspace-backup.json']=JSON.stringify({format:'unicode-touch-backup-v2',profile,layout});
const out=path.join(root,'工具/work/trime-install');fs.mkdirSync(out,{recursive:true});
for(const name of manifest.files){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(editor,'trime-base',name),target);}
for(const [name,text]of Object.entries(extras))fs.writeFileSync(path.join(out,name),text,'utf8');
console.log(JSON.stringify({id,files:[...manifest.files,...Object.keys(extras)],directory:out}));
