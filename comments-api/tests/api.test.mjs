import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/index.js';

const origin='https://raspos.github.io';
const base='https://databrew-now-comments.example.workers.dev';
function mkDb(){
  const items=[];
  return {
    items,
    prepare(query){
      return {
        bind(...args){
          return {
            async all(){
              if(query.includes("WHERE status = ?"))return {results:items.filter(i=>i.status===args[0])};
              return {results:items.filter(i=>i.post_key===args[0]&&i.status==='approved')};
            },
            async first(){
              if(query.includes('COUNT(*)')){
                if(query.includes('ip_hash'))return {n:items.filter(i=>i.ip_hash===args[0]).length};
                return {n:items.filter(i=>i.post_key===args[0]&&i.status==='approved').length};
              }
              if(query.includes('SELECT id'))return items.find(i=>i.post_key===args[0]&&i.ip_hash===args[1]&&i.content===args[2])||null;
              return null;
            },
            async run(){
              if(query.startsWith('INSERT')){
                const [id,post_key,nickname,content,ip_hash]=args;
                items.push({id,post_key,nickname,content,ip_hash,status:'pending',created_at:'2026-11-21 12:00:00'});
                return {meta:{changes:1}};
              }
              if(query.startsWith('UPDATE')){
                const row=items.find(i=>i.id===args[1]);
                if(row)row.status=args[0];
                return {meta:{changes:row?1:0}};
              }
              if(query.startsWith('DELETE')){
                const index=items.findIndex(i=>i.id===args[0]);
                if(index>=0)items.splice(index,1);
                return {meta:{changes:index>=0?1:0}};
              }
              return {meta:{changes:0}};
            }
          };
        },
      };
    }
  };
}
function env(db=mkDb()){
  return {DB:db,ALLOWED_ORIGIN:origin,TURNSTILE_HOSTNAME:'raspos.github.io',
    TURNSTILE_SECRET:'test-ts-secret',COMMENT_HASH_SALT:'test-long-random-salt',ADMIN_TOKEN:'test-admin-secret'};
}
async function call(path,init={},e=env()){
  const headers={'Origin':origin,...init.headers};
  const req=new Request(base+path,{...init,headers});
  const res=await worker.fetch(req,e);
  return {status:res.status,headers:res.headers,data:await res.json().catch(()=>null)};
}
test('health and CORS: only databrew origin is allowed to post',async()=>{
  const e=env();
  const ok=await call('/health',{},e);
  assert.equal(ok.status,200);
  assert.equal(ok.data.status,'ok');
  const preflight=await worker.fetch(new Request(base+'/api/comments',{method:'OPTIONS',headers:{Origin:origin}}),e);
  assert.equal(preflight.status,204);
  assert.equal(preflight.headers.get('Access-Control-Allow-Origin'),origin);
  const outsider=await worker.fetch(new Request(base+'/api/comments',{method:'OPTIONS',headers:{Origin:'https://evil.example'}}),e);
  assert.equal(outsider.status,403);
  assert.equal(outsider.headers.get('Access-Control-Allow-Origin'),null);
});
test('guest readers fetch approved comments without any login',async()=>{
  const db=mkDb(),e=env(db);
  db.items.push({id:'1',post_key:'watch:bok:2026-11-20',nickname:'독자',content:'검증된 댓글',status:'approved',created_at:'2026-11-21 12:00:00'});
  db.items.push({id:'2',post_key:'watch:bok:2026-11-20',nickname:'대기',content:'숨겨진 댓글',status:'pending',created_at:'2026-11-21 12:00:00'});
  const out=await call('/api/comments?post=watch%3Abok%3A2026-11-20',{},e);
  assert.equal(out.status,200);
  assert.equal(out.data.count,1);
  assert.equal(out.data.comments.length,1);
  assert.equal(out.data.comments[0].nickname,'독자');
});
test('invalid and off-site anonymous writes are rejected',async()=>{
  const e=env();
  const body=JSON.stringify({post_key:'watch:bok:2026-11-20',nickname:'독자',content:'좋아요',turnstile_token:'captcha-token-valid'});
  const off=await call('/api/comments',{method:'POST',headers:{Origin:'https://evil.example','Content-Type':'application/json'},body},e);
  assert.equal(off.status,403);
  const invalid=await call('/api/comments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    post_key:'../evil',nickname:'x',content:'hi',turnstile_token:'token-ten-chars'
  })},e);
  assert.equal(invalid.status,400);
});
test('guest submission requires server-side Turnstile and starts pending',async()=>{
  const savedFetch=globalThis.fetch;
  const db=mkDb(),e=env(db);
  globalThis.fetch=async()=>new Response(JSON.stringify({success:true,hostname:'raspos.github.io'}),{status:200});
  try{
    const out=await call('/api/comments',{method:'POST',headers:{
      'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.35'
    },body:JSON.stringify({post_key:'stories:story-1',nickname:'익명 독자',content:'자료 잘 읽었습니다',turnstile_token:'test-turnstile-token'})},e);
    assert.equal(out.status,202);
    assert.equal(db.items.length,1);
    assert.equal(db.items[0].status,'pending');
    assert.notEqual(db.items[0].ip_hash,'192.0.2.35');
    const listed=await call('/api/comments?post=stories%3Astory-1',{},e);
    assert.equal(listed.data.count,0);
  }finally{globalThis.fetch=savedFetch;}
});
test('token issued for another domain cannot submit',async()=>{
  const old=globalThis.fetch;const db=mkDb(),e=env(db);
  globalThis.fetch=async()=>new Response(JSON.stringify({success:true,hostname:'evil.example'}),{status:200});
  try{
    const result=await call('/api/comments',{method:'POST',headers:{
      'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.35'
    },body:JSON.stringify({post_key:'watch:apt:2026-11-21',nickname:'테스트',content:'확인한 정보입니다',turnstile_token:'test-turnstile-token'})},e);
    assert.equal(result.status,400);
    assert.equal(db.items.length,0);
  }finally{globalThis.fetch=old;}
});
test('moderation API requires admin token and updates comment status',async()=>{
  const db=mkDb(),e=env(db),id='a0d6e4c4-16e3-484c-b953-d0937ebc9fa8';
  db.items.push({id,post_key:'watch:fx:2026-11-20',nickname:'독자',content:'승인 기다림',status:'pending',created_at:'2026-11-21 12:00:00'});
  const no=await call('/api/admin/comments?status=pending',{},e);
  assert.equal(no.status,401);
  const yes=await call('/api/admin/comments?status=pending',{headers:{Authorization:'Bearer test-admin-secret'}},e);
  assert.equal(yes.status,200);assert.equal(yes.data.comments.length,1);
  const approved=await call('/api/admin/comments/'+id,{method:'POST',headers:{
    Authorization:'Bearer test-admin-secret','Content-Type':'application/json'
  },body:JSON.stringify({action:'approve'})},e);
  assert.equal(approved.status,200);
  assert.equal(db.items[0].status,'approved');
});
