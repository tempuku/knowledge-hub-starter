/* Browser asks only for a tiny calendar and the selected days' metadata.
   Full record bodies are fetched one at a time on user interaction. */
(() => {
  'use strict';
  const modeButtons = [...document.querySelectorAll('[data-mode]')];
  const input = document.getElementById('date');
  const timeline = document.getElementById('timeline');
  const total = document.getElementById('total');
  const sidebarDays = document.getElementById('sidebar-days');
  let calendar = [];
  let mode = 'week';
  const json = async (url) => {
    const response = await fetch(url, {cache: 'no-cache'});
    if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
    return response.json();
  };
  const span = (text, className) => {
    const el = document.createElement('span');
    el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const period = (value, currentMode) => {
    if (currentMode === 'day') return d => d === value;
    if (currentMode === 'month') return d => d.slice(0, 7) === value.slice(0, 7);
    // ISO week, Monday through Sunday, using UTC midday to avoid local DST changes.
    const date = new Date(value + 'T12:00:00Z');
    const dow = (date.getUTCDay() + 6) % 7;
    const monday = new Date(date.getTime() - dow * 86400000);
    const start = monday.toISOString().slice(0, 10);
    const end = new Date(monday.getTime() + 6 * 86400000).toISOString().slice(0, 10);
    return d => d >= start && d <= end;
  };
  const notesForDay = async (day, slot) => {
    if (slot.dataset.loaded) return;
    slot.dataset.loaded = 'loading';
    slot.textContent = 'Loading titles…';
    try {
      const info = await json(`./data/days/${day}.json`);
      slot.textContent = '';
      let nextPage = 1;
      const more = document.createElement('button'); more.className = 'open';
      const addPage = async () => {
        more.disabled = true; more.textContent = 'Loading…';
        more.remove();
        try {
          const records = await json(`./data/days/${day}/${nextPage}.json`);
      for (const record of records) {
        const article = document.createElement('article'); article.className = 'note';
        const title = document.createElement('h3');
        const recordName = record.has_change ? document.createElement('button') : null;
        if (recordName) {
          recordName.type = 'button';
          recordName.className = 'record-name';
          recordName.textContent = record.title;
          recordName.setAttribute('aria-expanded', 'false');
          title.append(recordName);
        } else {
          title.textContent = record.title;
        }
        article.append(title);
        if (record.description) {const p = document.createElement('p'); p.textContent = record.description; article.append(p);}
        if (record.timestamp) article.append(span(record.timestamp.slice(11, 16) + ' UTC', 'chip'));
        if (record.project) article.append(span(record.project, 'chip'));
        for (const tag of record.tags || []) article.append(span('#' + tag, 'chip'));
        const details = document.createElement('div');
        details.id = 'entry-' + record.id;
        details.hidden = true;
        const controls = document.createElement('div');
        controls.className = 'entry-controls';
        const views = record.has_change ? [
          {label: 'Show diff', close: 'Hide diff', diff: true},
          {label: 'Open', close: 'Close'},
        ] : [{label: 'Open entry', close: 'Hide entry'}];
        let full;
        let activeView;
        const buttons = views.map(view => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'open';
          button.textContent = view.label;
          button.setAttribute('aria-expanded', 'false');
          button.setAttribute('aria-controls', details.id);
          button.onclick = async () => {
            if (!full) {
              buttons.forEach(item => { item.disabled = true; });
              if (recordName) recordName.disabled = true;
              details.hidden = false;
              details.textContent = 'Loading entry…';
              try {
                full = await json(`./data/entries/${encodeURIComponent(record.id)}.json`);
              } catch (e) {
                details.textContent = 'Could not load entry. ' + e;
                return;
              } finally {
                buttons.forEach(item => { item.disabled = false; });
                if (recordName) recordName.disabled = false;
              }
            }
            activeView = activeView === view ? null : view;
            details.hidden = !activeView;
            buttons.forEach((item, i) => {
              const selected = activeView === views[i];
              item.textContent = selected ? views[i].close : views[i].label;
              item.setAttribute('aria-expanded', String(selected));
            });
            if (recordName) recordName.setAttribute('aria-expanded', String(activeView === views[1]));
            if (!activeView) return;
            details.textContent = '';
            const body = document.createElement('pre');
            body.className = 'body';
            if (view.diff) {
              const legend = document.createElement('p');
              legend.textContent = 'Changes in this entry (+ added, − removed)';
              details.append(legend);
              const diff = full.change && full.change.diff || 'No changed lines in this revision.';
              for (const line of diff.split('\n')) {
                const style = line.startsWith('+') && !line.startsWith('+++ ') ? 'diff-added'
                  : line.startsWith('-') && !line.startsWith('--- ') ? 'diff-removed' : '';
                body.append(span(line + '\n', style));
              }
            } else {
              body.textContent = full.body;
            }
            details.append(body);
          };
          return button;
        });
        if (recordName) {
          recordName.setAttribute('aria-controls', details.id);
          recordName.onclick = () => buttons[1].click();
        }
        controls.append(...buttons);
        article.append(controls, details);
        const sourceLinks = (record.links || []).filter(item => !/^https?:\/\/(?:www\.)?github\.com(?:[/:?#]|$)/i.test(item.url));
        if (sourceLinks.length) {
          const links = document.createElement('div'); links.className = 'links';
          for (const item of sourceLinks) { const a = document.createElement('a'); a.textContent = item.title; a.href = item.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; links.append(a); }
          article.append(links);
        }
        slot.append(article);
      }
          nextPage += 1;
          if (nextPage <= info.pages) {
            more.textContent = 'Load more entries';
            more.disabled = false;
            slot.append(more);
          } else more.remove();
        } catch (e) { more.textContent = 'Retry loading records'; more.disabled = false; slot.append(more); }
      };
      more.onclick = addPage;
      await addPage();
      slot.dataset.loaded = 'yes';
    } catch (err) {slot.textContent = `Could not load records: ${err}`; delete slot.dataset.loaded;}
  };
  const highlightSidebar = () => {
    for (const button of sidebarDays.querySelectorAll('[data-day]')) {
      const active = mode === 'day' && button.dataset.day === input.value;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'date');
      else button.removeAttribute('aria-current');
    }
  };
  const renderSidebar = () => {
    sidebarDays.textContent = '';
    for (const item of calendar.slice(0, 90)) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sidebar-day';
      button.dataset.day = item.date;
      const dateText = new Date(item.date + 'T12:00:00Z').toLocaleDateString('en-US',
        {timeZone: 'UTC', month: 'short', day: 'numeric', year: 'numeric'});
      button.append(span(dateText, 'sidebar-date'), span(String(item.count), 'sidebar-count'));
      button.addEventListener('click', () => {
        input.value = item.date;
        mode = 'day';
        modeButtons.forEach(b => {
          const active = b.dataset.mode === 'day';
          b.classList.toggle('selected', active);
          b.setAttribute('aria-pressed', String(active));
        });
        render();
      });
      sidebarDays.append(button);
    }
    highlightSidebar();
  };
  const render = () => {
    const date = input.value;
    const inPeriod = date ? period(date, mode) : () => false;
    const selected = calendar.filter(x => inPeriod(x.date));
    timeline.textContent = '';
    const count = selected.reduce((sum, d) => sum + d.count, 0);
    total.textContent = `${count} ${count === 1 ? 'entry' : 'entries'}`;
    highlightSidebar();
    if (!selected.length) { const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'No records for this date range.'; timeline.append(p); return; }
    for (const [i, item] of selected.entries()) {
      const section = document.createElement('section'); section.className = 'day';
      const header = document.createElement('button'); header.className = 'day-header';
      const left = document.createElement('b'); left.textContent = new Date(item.date + 'T12:00:00Z').toLocaleDateString('en-US', {timeZone:'UTC', year:'numeric', month:'short', day:'numeric', weekday:'short'});
      const right = span(`${item.count} ${item.count === 1 ? 'entry' : 'entries'}  ▾`);
      header.append(left, right);
      const slot = document.createElement('div'); slot.className = 'items'; slot.hidden = true;
      header.setAttribute('aria-expanded', 'false');
      header.onclick = () => {slot.hidden = !slot.hidden; header.setAttribute('aria-expanded', String(!slot.hidden)); if (!slot.hidden) notesForDay(item.date, slot);};
      section.append(header, slot); timeline.append(section);
      // Show the week at a glance. In Month view, load only the first day.
      if (mode !== 'month' || i === 0) header.click();
    }
  };
  modeButtons.forEach(button => button.addEventListener('click', () => {
    mode = button.dataset.mode;
    modeButtons.forEach(b => { b.classList.toggle('selected', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    render();
  }));
  input.addEventListener('change', render);

  // iPad Air (1st generation) runs Safari 12: use classic Home Screen
  // capability meta tags plus feature-detected Service Worker registration.
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(() => {
        // The online app works without offline caching or service workers.
      });
    });
  }
  json('./data/calendar.json').then(data => {
    calendar = data.days || [];
    renderSidebar();
    input.value = (calendar.length ? calendar[0].date : new Date().toISOString().slice(0, 10));
    render();
  }).catch(error => { timeline.textContent = 'Could not load diary catalog: ' + error; });
})();
