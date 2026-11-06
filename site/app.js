(() => {
  'use strict';
  const D = window.TIMETABLE;
  const $ = (s) => document.querySelector(s);

  const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];
  const fmtDate = (iso) => {
    const d = new Date(iso + 'T00:00:00');
    return `${WEEKDAYS[d.getDay() === 0 ? 6 : d.getDay() - 1]} ${d.toLocaleDateString('uk-UA')}`;
  };

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
    select.innerHTML = options.map((o) => `<option value="${o}">${o}</option>`).join('');
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
      { label: 'Дисципліна', get: (r) => r.subject },
      { label: 'Тип', get: (r) => r.lesson_type },
      { label: 'Викладач', get: (r) => r.teacher },
      { label: 'Аудиторія', get: (r) => r.room },
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
      { label: 'Дисципліна', get: (r) => r.subject },
      { label: 'Тип', get: (r) => r.lesson_type },
      { label: 'Група', get: (r) => r.group },
      { label: 'Аудиторія', get: (r) => r.room },
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
      { label: 'Дисципліна', get: (r) => r.subject },
      { label: 'Викладач', get: (r) => r.teacher },
      { label: 'Група', get: (r) => r.group },
    ]);
  }
  roomSelect.addEventListener('change', renderRoom);

  // ---- about / warnings
  $('#built-date').textContent = `Зібрано: ${D.built}. Семестр від ${D.settings.semester_start}, ${D.settings.weeks} тижнів.`;
  const warnList = $('#warnings-list');
  if (D.warnings.length === 0) {
    warnList.innerHTML = '<li class="ok">Зауважень немає.</li>';
  } else {
    warnList.innerHTML = D.warnings.map((w) => `<li>${w}</li>`).join('');
  }

  // ---- tabs
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
      btn.classList.add('active');
      $(`#view-${btn.dataset.tab}`).classList.add('active');
    });
  });

  renderGroup();
  renderTeacher();
  renderRoom();
})();
