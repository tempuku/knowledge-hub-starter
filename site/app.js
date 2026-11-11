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
  let reminders = [];
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
        title.textContent = record.title;
        article.append(title);
        if (record.source_file) {
          const source = document.createElement('a');
          source.className = 'record-file-link';
          source.href = 'https://github.com/tempuku/knowledge-hub-starter/blob/main/' + record.source_file;
          source.target = '_blank';
          source.rel = 'noopener noreferrer';
          source.textContent = 'File: ' + record.source_file;
          article.append(source);
        }
        if (record.status === 'completed') article.append(span('Completed', 'record-status completed'));
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

              details.hidden = false;
              details.textContent = 'Loading entry…';
              try {
                full = await json(`./data/entries/${encodeURIComponent(record.id)}.json`);
              } catch (e) {
                details.textContent = 'Could not load entry. ' + e;
                return;
              } finally {
                buttons.forEach(item => { item.disabled = false; });

              }
            }
            activeView = activeView === view ? null : view;
            details.hidden = !activeView;
            buttons.forEach((item, i) => {
              const selected = activeView === views[i];
              item.textContent = selected ? views[i].close : views[i].label;
              item.setAttribute('aria-expanded', String(selected));
            });

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
    renderReminders();
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
  const renderReminders = () => {
    const host = document.getElementById('reminder-calendar');
    if (!host) return;
    host.textContent = '';
    const selectedMonth = (input.value || new Date().toISOString().slice(0, 10)).slice(0, 7);
    const [year, month] = selectedMonth.split('-').map(Number);
    const heading = document.createElement('h2');
    heading.textContent = 'Important dates · ' + new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString('en-US', {month:'long', year:'numeric', timeZone:'UTC'});
    host.append(heading);
    const grid = document.createElement('div'); grid.className = 'reminder-grid';
    const first = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
    const offset = (first + 6) % 7;
    const days = new Date(Date.UTC(year, month, 0)).getUTCDate();
    for (let i = 0; i < offset; i++) grid.append(document.createElement('span'));
    for (let d = 1; d <= days; d++) {
      const day = selectedMonth + '-' + String(d).padStart(2, '0');
      const hits = reminders.filter(item => item.start <= day && item.end >= day);
      const cell = document.createElement('button');
      cell.type = 'button'; cell.className = 'reminder-day' + (hits.length ? ' has-reminder' : '');
      cell.textContent = String(d);
      cell.title = hits.map(item => item.text).join('; ');
      cell.setAttribute('aria-label', day + (hits.length ? ': ' + cell.title : ''));
      cell.onclick = () => { input.value = day; mode = 'day'; render(); };
      grid.append(cell);
    }
    host.append(grid);
    const list = document.createElement('ul'); list.className = 'reminder-list';
    for (const event of reminders.filter(item => item.start.slice(0, 7) <= selectedMonth && item.end.slice(0, 7) >= selectedMonth)) {
      const item = document.createElement('li');
      const dates = document.createElement('strong');
      dates.textContent = event.start === event.end ? event.start : event.start + ' – ' + event.end;
      item.append(dates, document.createTextNode(' · ' + event.text));
      list.append(item);
    }
    host.append(list);
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
  json('./data/reminders.json').then(data => { reminders = data.events || []; renderReminders(); }).catch(() => {});
  json('./data/calendar.json').then(data => {
    calendar = data.days || [];
    renderSidebar();
    input.value = (calendar.length ? calendar[0].date : new Date().toISOString().slice(0, 10));
    render();
  }).catch(error => { timeline.textContent = 'Could not load diary catalog: ' + error; });
})();
