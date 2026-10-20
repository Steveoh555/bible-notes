/* 성경연구노트 — 공통 스크립트 */
(function(){
  var KEY='bnote-theme';
  var order=['auto','light','dark'];
  var label={auto:'자동',light:'밝게',dark:'어둡게'};

  function apply(v){
    var r=document.documentElement;
    if(v==='auto'){ r.removeAttribute('data-theme'); }
    else { r.setAttribute('data-theme', v); }
    var b=document.getElementById('themeBtn');
    if(b){ b.textContent=label[v]; b.setAttribute('aria-label','화면 테마: '+label[v]+' (눌러서 변경)'); }
  }
  function current(){
    try{ return localStorage.getItem(KEY) || 'auto'; }catch(e){ return 'auto'; }
  }
  document.addEventListener('DOMContentLoaded', function(){
    apply(current());
    var b=document.getElementById('themeBtn');
    if(b){
      b.addEventListener('click', function(){
        var next=order[(order.indexOf(current())+1) % order.length];
        try{ localStorage.setItem(KEY,next); }catch(e){}
        apply(next);
      });
    }

    /* 홈 자료 목록 — 검색 · 차례(최신순/성경순) · 「더 보기」 */
    var list=document.querySelector('.index-list');
    if(list){
      var PAGE=5;                         /* build.py 의 PAGE_SIZE 와 같아야 한다 */
      var SKEY='bnote-sort';
      var rows=[].slice.call(list.children);
      var q=document.getElementById('q');
      var count=document.getElementById('count');
      var empty=document.getElementById('empty');
      var moreRow=document.getElementById('moreRow');
      var moreBtn=document.getElementById('moreBtn');
      var moreRest=document.getElementById('moreRest');
      var tabs=[].slice.call(document.querySelectorAll('.sort-tab'));
      var total=rows.length, shown=PAGE, sort='new';

      rows.forEach(function(li,i){ li.dataset.i=i; });
      try{ if(localStorage.getItem(SKEY)==='bible') sort='bible'; }catch(e){}

      function term(){ return q ? q.value.trim().toLowerCase() : ''; }

      function render(){
        var t=term();
        var arr=rows.slice();
        arr.sort(sort==='bible'
          ? function(a,b){ var x=a.dataset.order||'', y=b.dataset.order||'';
                           return x<y?-1 : x>y?1 : (+a.dataset.i)-(+b.dataset.i); }
          : function(a,b){ return (+a.dataset.i)-(+b.dataset.i); });
        var frag=document.createDocumentFragment();
        arr.forEach(function(li){ frag.appendChild(li); });
        list.appendChild(frag);

        /* 검색 중에는 자르지 않는다 — 찾은 것을 모두 보여 준다 */
        var limit = t ? total : shown, hits=0;
        arr.forEach(function(li){
          var a=li.querySelector('.entry');
          var hit = !t || (((a && a.dataset.search) || '').indexOf(t) > -1);
          if(hit){ hits++; li.hidden = hits>limit; } else { li.hidden = true; }
        });

        if(count) count.textContent = t ? hits+' / '+total+' 편' : total+' 편';
        if(empty) empty.hidden = hits>0;
        var rest = Math.max(0, hits-limit);
        if(moreRow){
          moreRow.hidden = rest===0;
          if(moreRest) moreRest.textContent = rest ? '남은 '+rest+'편' : '';
        }
        tabs.forEach(function(b){ b.setAttribute('aria-pressed', String(b.dataset.sort===sort)); });
      }

      if(q) q.addEventListener('input', render);

      tabs.forEach(function(b){
        b.addEventListener('click', function(){
          sort = b.dataset.sort==='bible' ? 'bible' : 'new';
          try{ localStorage.setItem(SKEY, sort); }catch(e){}
          render();
        });
      });

      if(moreBtn) moreBtn.addEventListener('click', function(){
        var before=shown;
        shown += PAGE;
        render();
        /* 새로 나온 첫 자료로 초점을 옮겨, 자판만 쓰는 사람도 이어서 읽는다 */
        var open=[].slice.call(list.children).filter(function(li){ return !li.hidden; });
        var next=open[before];
        if(next){ var a=next.querySelector('.entry'); if(a){ a.setAttribute('tabindex','-1'); a.focus(); } }
      });

      render();
    }
  });
})();

/* 차트 말풍선 — 막대·점에 올리거나 초점을 주면 뜬다(Esc 로 닫힘). 모든 차트가 이것을 쓴다.
   BN.chartTip(요소, 말풍선 HTML, 요소 위쪽 중심 x, y)  — x·y 는 SVG 뷰박스 좌표, 요소는 이미 SVG 안에 붙어 있어야 한다. */
window.BN=window.BN||{};
BN.chartTip=function(node,html,x,y){
  var wrap=node.closest('.chart-wrap'), svg=node.ownerSVGElement;
  var tt=wrap&&wrap.querySelector('.tt');
  if(!tt||!svg) return;
  function show(){
    tt.innerHTML=html; tt.style.opacity='1';
    var box=svg.getBoundingClientRect(), w=wrap.getBoundingClientRect();
    var s=box.width/((svg.viewBox&&svg.viewBox.baseVal.width)||760);
    var left=x*s+box.left-w.left-tt.offsetWidth/2;
    tt.style.left=Math.min(Math.max(left,4),Math.max(4,w.width-tt.offsetWidth-4))+'px';
    tt.style.top=Math.max(2,y*s+box.top-w.top-tt.offsetHeight-8)+'px';
  }
  function hide(){ tt.style.opacity='0'; }
  node.addEventListener('mouseenter',show); node.addEventListener('focus',show);
  node.addEventListener('mouseleave',hide); node.addEventListener('blur',hide);
  node.addEventListener('keydown',function(e){ if(e.key==='Escape') hide(); });
};
