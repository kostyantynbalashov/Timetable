import { useEffect, useState } from "react";
import { api } from "../api";
import type { Group, ScheduleItem, Teacher } from "../api";

export default function SchedulePage() {
  const [mode, setMode] = useState<"group" | "teacher">("group");
  const [groups, setGroups] = useState<Group[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [entityId, setEntityId] = useState(0);
  const today = new Date();
  const in30 = new Date(today.getTime() + 30 * 86400000);
  const [dateFrom, setDateFrom] = useState(today.toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(in30.toISOString().slice(0, 10));
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Group[]>("/api/groups").then(setGroups);
    api.get<Teacher[]>("/api/teachers").then(setTeachers);
  }, []);

  const load = async () => {
    if (!entityId) { setError("Оберіть групу або викладача"); return; }
    setError("");
    try {
      const data = await api.get<ScheduleItem[]>(
        `/api/schedule/${mode}/${entityId}?date_from=${dateFrom}&date_to=${dateTo}`
      );
      setItems(data);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      <h2>Розклад</h2>
      {error && <p className="error">{error}</p>}
      <div className="form-row">
        <select value={mode} onChange={(e) => { setMode(e.target.value as "group" | "teacher"); setEntityId(0); }}>
          <option value="group">За групою</option>
          <option value="teacher">За викладачем</option>
        </select>
        <select value={entityId} onChange={(e) => setEntityId(Number(e.target.value))}>
          <option value={0}>— оберіть —</option>
          {mode === "group"
            ? groups.map((g) => <option key={g.id} value={g.id}>{g.code}</option>)
            : teachers.map((t) => <option key={t.id} value={t.id}>{t.last_name} {t.first_name}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <button onClick={load}>Показати</button>
      </div>
      <table>
        <thead><tr><th>Дата</th><th>Пара</th><th>Дисципліна</th><th>Тип</th><th>Викладач</th><th>Група</th><th>Аудиторія</th></tr></thead>
        <tbody>
          {items.map((i, idx) => (
            <tr key={idx}>
              <td>{i.date}</td><td>{i.period}</td><td>{i.subject}</td><td>{i.lesson_type}</td>
              <td>{i.teacher}</td><td>{i.group}</td><td>{i.room ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
