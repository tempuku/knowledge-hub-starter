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
  let mode = 'day';
  const json = async (url) => {
    const response = await fetch(url);
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
        const title = document.createElement('h3'); title.textContent = record.title; article.append(title);
        if (record.description) {const p = document.createElement('p'); p.textContent = record.description; article.append(p);}
        if (record.project) article.append(span(record.project, 'chip'));
        for (const tag of record.tags || []) article.append(span('#' + tag, 'chip'));
        const details = document.createElement('div');
        const open = document.createElement('button'); open.className = 'open'; open.textContent = 'Open entry';
        open.onclick = async () => {
          if (!details.dataset.loaded) {
            open.disabled = true; open.textContent = 'Loading entry…';
            try { const full = await json(`./data/entries/${encodeURIComponent(record.id)}.json`);
              const body = document.createElement('pre'); body.className = 'body'; body.textContent = full.body; details.append(body);
              if (full.log_entry) {
                const entry = full.log_entry;
                const openRecord = document.createElement('button');
                openRecord.type = 'button'; openRecord.className = 'open';
                openRecord.textContent = 'Open original record';
                const recordView = document.createElement('pre');
                recordView.className = 'body'; recordView.hidden = true;
                recordView.textContent = entry.after || '(record deleted)';
                openRecord.onclick = () => {
                  recordView.hidden = !recordView.hidden;
                  openRecord.textContent = recordView.hidden ? 'Open original record' : 'Hide original record';
                };
                const changes = document.createElement('button');
                changes.type = 'button'; changes.className = 'open';
                changes.textContent = 'View complete change';
                const beforeAfter = document.createElement('div'); beforeAfter.hidden = true;
                const beforeTitle = document.createElement('h4'); beforeTitle.textContent = 'Before';
                const beforeBody = document.createElement('pre'); beforeBody.className = 'body';
                beforeBody.textContent = entry.before === null ? '(record did not exist)' : entry.before;
                const afterTitle = document.createElement('h4'); afterTitle.textContent = 'After';
                const afterBody = document.createElement('pre'); afterBody.className = 'body';
                afterBody.textContent = entry.after;
                beforeAfter.append(beforeTitle, beforeBody, afterTitle, afterBody);
                changes.onclick = () => {
                  beforeAfter.hidden = !beforeAfter.hidden;
                  changes.textContent = beforeAfter.hidden ? 'View complete change' : 'Hide complete change';
                };
                const actions = document.createElement('div'); actions.className = 'entry-actions';
                actions.append(openRecord, changes);
                details.append(actions, recordView, beforeAfter);
              } else if (full.change) {
                const source = document.createElement('a');
                source.textContent = 'Original record'; source.href = full.change.source_url;
                source.target = '_blank'; source.rel = 'noopener noreferrer';
                const actions = document.createElement('div'); actions.className = 'entry-actions';
                actions.append(source);
                const diffButton = document.createElement('button');
                diffButton.type = 'button'; diffButton.className = 'open'; diffButton.textContent = 'View full diff';
                const diff = document.createElement('pre'); diff.className = 'body'; diff.hidden = true;
                diff.textContent = full.change.diff;
                diffButton.onclick = () => { diff.hidden = !diff.hidden; diffButton.textContent = diff.hidden ? 'View full diff' : 'Hide full diff'; };
                actions.append(diffButton);
                details.append(actions, diff);
              }
              details.dataset.loaded = 'yes';
              open.textContent = 'Hide entry';
            } catch (e) { details.textContent = String(e); open.textContent = 'Retry'; }
            open.disabled = false;
          } else { const show = details.hidden; details.hidden = !show; open.textContent = show ? 'Hide entry' : 'Open entry'; }
        };
        article.append(open, details);
        if (record.links && record.links.length) { const links = document.createElement('div'); links.className = 'links';
          for (const item of record.links) { const a = document.createElement('a'); a.textContent = item.title; a.href = item.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; links.append(a); }
          article.append(links); }
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
    const selected = calendar.filter(x => period(date, mode)(x.date));
    timeline.textContent = '';
    total.textContent = selected.reduce((sum, d) => sum + d.count, 0) + ' changes';
    highlightSidebar();
    if (!selected.length) { const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'No records for this date range.'; timeline.append(p); return; }
    for (const [i, item] of selected.entries()) {
      const section = document.createElement('section'); section.className = 'day';
      const header = document.createElement('button'); header.className = 'day-header';
      const left = document.createElement('b'); left.textContent = new Date(item.date + 'T12:00:00Z').toLocaleDateString('en-US', {timeZone:'UTC', year:'numeric', month:'short', day:'numeric', weekday:'short'});
      const right = span(`${item.count} ${item.count === 1 ? 'change' : 'changes'}  ▾`);
      header.append(left, right);
      const slot = document.createElement('div'); slot.className = 'items'; slot.hidden = true;
      header.setAttribute('aria-expanded', 'false');
      header.onclick = () => {slot.hidden = !slot.hidden; header.setAttribute('aria-expanded', String(!slot.hidden)); if (!slot.hidden) notesForDay(item.date, slot);};
      section.append(header, slot); timeline.append(section);
      // One useful day opens initially; other dates remain lazy, especially for month view.
      if (i === 0) header.click();
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
