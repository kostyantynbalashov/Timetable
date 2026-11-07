(() => {
  'use strict';
  const D = window.TIMETABLE;
  const $ = (s) => document.querySelector(s);

  const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];
  const fmtDate = (iso) => {
    const d = new Date(iso + 'T00:00:00');
    return `${WEEKDAYS[d.getDay() === 0 ? 6 : d.getDay() - 1]} ${d.toLocaleDateString('uk-UA')}`;
  };

  const escapeHtml = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function linkCell(kind, value) {
    const safe = escapeHtml(value);
    return `<a href="#" class="link" data-kind="${kind}" data-value="${safe}">${safe}</a>`;
  }

  function renderTable(container, rows, columns) {
    if (!rows.length) {
      container.innerHTML = '<p class="empty">Немає занять.</p>';
      return;
    }
    const thead = columns.map((c) => `<th>${c.label}</th>`).join('');
    const tbody = rows
      .map((r) => `<tr>${columns.map((c) => `<td>${c.get(r)}</td>`).join('')}</tr>`)
      .join('');
    container.innerHTML = `<table><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table>`;
  }

  function fillSelect(select, options) {
    select.innerHTML = options.map((o) => `<option value="${escapeHtml(o)}">${escapeHtml(o)}</option>`).join('');
  }

  function showTab(name) {
    document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === `view-${name}`));
  }

  // ---- group view
  const groupSelect = $('#group-select');
  fillSelect(groupSelect, D.groups.map((g) => g.code));
  function renderGroup() {
    const code = groupSelect.value;
    const rows = D.occurrences.filter((o) => o.group === code);
    renderTable($('#group-table'), rows, [
      { label: 'Дата', get: (r) => fmtDate(r.date) },
      { label: 'Пара', get: (r) => r.period },
      { label: 'Дисципліна', get: (r) => linkCell('subject', r.subject) },
      { label: 'Тип', get: (r) => r.lesson_type },
      { label: 'Викладач', get: (r) => linkCell('teacher', r.teacher) },
      { label: 'Аудиторія', get: (r) => linkCell('room', r.room) },
    ]);
  }
  groupSelect.addEventListener('change', renderGroup);

  // ---- teacher view
  const teacherSelect = $('#teacher-select');
  fillSelect(teacherSelect, D.teachers.map((t) => t.name));
  function renderTeacher() {
    const name = teacherSelect.value;
    const rows = D.occurrences.filter((o) => o.teacher === name);
    renderTable($('#teacher-table'), rows, [
      { label: 'Дата', get: (r) => fmtDate(r.date) },
      { label: 'Пара', get: (r) => r.period },
      { label: 'Дисципліна', get: (r) => linkCell('subject', r.subject) },
      { label: 'Тип', get: (r) => r.lesson_type },
      { label: 'Група', get: (r) => linkCell('group', r.group) },
      { label: 'Аудиторія', get: (r) => linkCell('room', r.room) },
    ]);
  }
  teacherSelect.addEventListener('change', renderTeacher);

  // ---- room view
  const roomSelect = $('#room-select');
  fillSelect(roomSelect, D.rooms.map((r) => r.label));
  function renderRoom() {
    const label = roomSelect.value;
    const rows = D.occurrences.filter((o) => o.room === label);
    renderTable($('#room-table'), rows, [
      { label: 'Дата', get: (r) => fmtDate(r.date) },
      { label: 'Пара', get: (r) => r.period },
      { label: 'Дисципліна', get: (r) => linkCell('subject', r.subject) },
      { label: 'Викладач', get: (r) => linkCell('teacher', r.teacher) },
      { label: 'Група', get: (r) => linkCell('group', r.group) },
    ]);
  }
  roomSelect.addEventListener('change', renderRoom);

  // ---- subject info modal (hours are what's actually scheduled, not a
  // curriculum plan — see "Про збірку" for the caveat)
  const modal = $('#subject-modal');
  function showSubjectInfo(name) {
    const s = (D.subjects || []).find((x) => x.name === name);
    const typeRows = s
      ? Object.entries(s.by_type).map(([t, h]) => `<li>${escapeHtml(t)}: ${h} год.</li>`).join('')
      : '<li>Немає даних.</li>';
    $('#subject-modal-body').innerHTML = `
      <h3>${escapeHtml(name)}</h3>
      <p class="hint">Заплановано в поточному розкладі (не навчальний план):</p>
      <ul>${typeRows}</ul>
      ${s ? `<p><strong>Усього: ${s.total_hours} год.</strong></p>` : ''}
    `;
    modal.classList.add('open');
  }
  $('#subject-modal-close').addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });

  // ---- cross-link clicks (event delegation — tables are re-rendered often)
  document.addEventListener('click', (e) => {
    const link = e.target.closest('.link');
    if (!link) return;
    e.preventDefault();
    const { kind, value } = link.dataset;
    if (kind === 'teacher') {
      showTab('teacher');
      teacherSelect.value = value;
      renderTeacher();
    } else if (kind === 'room') {
      showTab('room');
      roomSelect.value = value;
      renderRoom();
    } else if (kind === 'group') {
      showTab('group');
      groupSelect.value = value;
      renderGroup();
    } else if (kind === 'subject') {
      showSubjectInfo(value);
    }
  });

  // ---- about / warnings
  $('#built-date').textContent = `Зібрано: ${D.built}. Семестр від ${D.settings.semester_start}, ${D.settings.weeks} тижнів.`;
  const warnList = $('#warnings-list');
  if (D.warnings.length === 0) {
    warnList.innerHTML = '<li class="ok">Зауважень немає.</li>';
  } else {
    warnList.innerHTML = D.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join('');
  }

  // ---- tabs
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
  });

  renderGroup();
  renderTeacher();
  renderRoom();
})();
