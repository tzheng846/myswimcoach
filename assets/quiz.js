/* ==========================================================================
   Retrieval-practice quiz component.

   Usage in a lesson:

     <div class="quiz" data-quiz>
       <script type="application/json">
       [
         { "q": "Question text?",
           "options": ["Answer one here", "Answer two here"],
           "answer": 0,
           "why": "Explanation shown after committing." }
       ]
       </script>
     </div>
     <script src="../assets/quiz.js"></script>

   Design notes:
   - Answers commit on click and CANNOT be changed. Effortful retrieval builds storage
     strength; letting the learner fish for the green highlight destroys it.
   - Explanation appears only after committing, for both right and wrong answers.
   - Options are authored to equal word counts so formatting leaks no clues. The
     component warns in the console when a lesson violates this — keep it honest.
   ========================================================================== */

(function () {
  'use strict';

  var CSS = `
  .quiz { margin: 2rem 0; max-width: calc(var(--measure) + var(--gutter)); }
  .quiz-item {
    border: 1px solid var(--rule);
    border-radius: 7px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 1rem;
    background: var(--bg);
  }
  .quiz-q {
    font-family: var(--sans);
    font-size: 0.93rem;
    font-weight: 600;
    line-height: 1.45;
    margin: 0 0 0.9rem;
    display: flex; gap: 0.6rem;
  }
  .quiz-n {
    flex: 0 0 auto;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
  }
  .quiz-opts { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
  .quiz-opt {
    font-family: var(--sans);
    font-size: 0.855rem;
    line-height: 1.4;
    text-align: left;
    width: 100%;
    padding: 0.6rem 0.8rem;
    border: 1px solid var(--rule);
    border-radius: 5px;
    background: var(--bg-sunk);
    color: var(--ink);
    cursor: pointer;
    transition: border-color .12s ease, background .12s ease;
  }
  .quiz-opt:hover:not(:disabled) { border-color: var(--accent); }
  .quiz-opt:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .quiz-opt:disabled { cursor: default; }
  .quiz-opt.is-right {
    background: var(--good-bg);
    border-color: var(--good);
    color: var(--good);
    font-weight: 600;
  }
  .quiz-opt.is-wrong {
    background: var(--bad-bg);
    border-color: var(--bad);
    color: var(--bad);
    text-decoration: line-through;
  }
  .quiz-opt.is-muted { opacity: 0.5; }
  .quiz-why {
    font-family: var(--sans);
    font-size: 0.82rem;
    line-height: 1.55;
    margin-top: 0.85rem;
    padding-top: 0.8rem;
    border-top: 1px dashed var(--rule);
    color: var(--ink-soft);
  }
  .quiz-why[hidden] { display: none; }
  .quiz-why b { color: var(--ink); }
  .quiz-score {
    font-family: var(--sans);
    font-size: 0.82rem;
    color: var(--ink-faint);
    padding-top: 0.6rem;
  }
  @media print {
    .quiz-opt { background: #fff; }
    .quiz-why { display: block !important; }
  }`;

  function injectStyles() {
    if (document.getElementById('quiz-component-styles')) return;
    var el = document.createElement('style');
    el.id = 'quiz-component-styles';
    el.textContent = CSS;
    document.head.appendChild(el);
  }

  // Authoring guard: options should carry no length tell.
  function auditOptions(items) {
    items.forEach(function (item, i) {
      var counts = item.options.map(function (o) { return o.trim().split(/\s+/).length; });
      var min = Math.min.apply(null, counts), max = Math.max.apply(null, counts);
      if (max !== min) {
        console.warn(
          '[quiz] Q' + (i + 1) + ' options have unequal word counts (' + counts.join('/') +
          '). Length is a clue — even them out.'
        );
      }
    });
  }

  function render(root) {
    var src = root.querySelector('script[type="application/json"]');
    if (!src) return;

    var items;
    try {
      items = JSON.parse(src.textContent);
    } catch (e) {
      console.error('[quiz] Bad JSON in quiz block:', e);
      return;
    }

    auditOptions(items);

    var answered = 0, correct = 0;
    var frag = document.createDocumentFragment();

    items.forEach(function (item, i) {
      var card = document.createElement('div');
      card.className = 'quiz-item';

      var q = document.createElement('p');
      q.className = 'quiz-q';
      q.innerHTML = '<span class="quiz-n">' + (i + 1) + '.</span><span>' + item.q + '</span>';
      card.appendChild(q);

      var list = document.createElement('ul');
      list.className = 'quiz-opts';

      var why = document.createElement('div');
      why.className = 'quiz-why';
      why.hidden = true;

      item.options.forEach(function (text, j) {
        var li = document.createElement('li');
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'quiz-opt';
        btn.textContent = text;

        btn.addEventListener('click', function () {
          var right = j === item.answer;
          answered++;
          if (right) correct++;

          Array.prototype.forEach.call(list.querySelectorAll('.quiz-opt'), function (b, k) {
            b.disabled = true;
            if (k === item.answer) b.classList.add('is-right');
            else if (k === j) b.classList.add('is-wrong');
            else b.classList.add('is-muted');
          });

          why.innerHTML = '<b>' + (right ? 'Correct.' : 'Not quite.') + '</b> ' + item.why;
          why.hidden = false;
          updateScore();
        });

        li.appendChild(btn);
        list.appendChild(li);
      });

      card.appendChild(list);
      card.appendChild(why);
      frag.appendChild(card);
    });

    var score = document.createElement('p');
    score.className = 'quiz-score';

    function updateScore() {
      score.textContent = answered === 0
        ? ''
        : correct + ' / ' + answered + ' answered correctly' +
          (answered === items.length ? ' — all questions attempted.' : '');
    }

    root.appendChild(frag);
    root.appendChild(score);
    src.remove();
  }

  function init() {
    injectStyles();
    Array.prototype.forEach.call(document.querySelectorAll('[data-quiz]'), render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
