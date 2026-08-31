/* 성경연구노트 — 공통 스크립트 */
(function(){
  var KEY='bnote-theme';
  var order=['auto','light','dark'];
  var label={auto:'자동',light:'밝게',dark:'어둡게'};

  function apply(v, animate){
    var r=document.documentElement;
    if(animate!==false){                      // 전환 순간만 트랜지션 정지
      r.classList.add('theme-switching');     // var() 치환이 옛 색에 고착되는 것을 막는다
      void r.offsetWidth;
      setTimeout(function(){ r.classList.remove('theme-switching'); }, 60);
    }
    if(v==='auto'){ r.removeAttribute('data-theme'); }
    else { r.setAttribute('data-theme', v); }
    var b=document.getElementById('themeBtn');
    if(b){ b.textContent=label[v]; b.setAttribute('aria-label','화면 테마: '+label[v]+' (눌러서 변경)'); }
  }
  function current(){
    try{ return localStorage.getItem(KEY) || 'auto'; }catch(e){ return 'auto'; }
  }
  document.addEventListener('DOMContentLoaded', function(){
    apply(current(), false);
    var b=document.getElementById('themeBtn');
    if(b){
      b.addEventListener('click', function(){
        var next=order[(order.indexOf(current())+1) % order.length];
        try{ localStorage.setItem(KEY,next); }catch(e){}
        apply(next);
      });
    }

    /* 홈 화면 검색 */
    var q=document.getElementById('q');
    if(q){
      var cards=[].slice.call(document.querySelectorAll('.index-list .entry'));
      var count=document.getElementById('count');
      var empty=document.getElementById('empty');
      var total=cards.length;
      var run=function(){
        var t=q.value.trim().toLowerCase();
        var n=0;
        cards.forEach(function(c){
          var hit = !t || (c.dataset.search||'').indexOf(t)>-1;
          var row = c.closest('li') || c; row.style.display = hit ? '' : 'none';
          if(hit) n++;
        });
        if(count) count.textContent = t ? n+' / '+total+' 편' : total+' 편';
        if(empty) empty.hidden = n>0;
      };
      q.addEventListener('input', run);
      run();
    }
  });
})();
