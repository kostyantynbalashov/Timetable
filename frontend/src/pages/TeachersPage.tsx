import { useEffect, useState } from "react";
import { api } from "../api";
import type { Teacher } from "../api";

const POSITIONS = ["асистент", "викладач", "старший викладач", "доцент", "професор", "завідувач кафедри"];
const DEGREES = ["немає", "кандидат наук / доктор філософії", "доктор наук"];
const TITLES = ["немає", "доцент", "професор", "старший дослідник"];

export default function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    last_name: "", first_name: "", middle_name: "",
    degree: DEGREES[0], academic_title: TITLES[0], position: POSITIONS[0], fte: 1,
  });

  const load = () => api.get<Teacher[]>("/api/teachers").then(setTeachers).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/api/teachers", { ...form, fte: Number(form.fte), subject_ids: [] });
      setForm({ ...form, last_name: "", first_name: "", middle_name: "" });
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (id: number) => {
    await api.del(`/api/teachers/${id}`);
    load();
  };

  return (
    <div>
      <h2>Викладачі</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit} className="form-row">
        <input placeholder="Прізвище" required value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        <input placeholder="Ім'я" required value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        <input placeholder="По батькові" value={form.middle_name}
          onChange={(e) => setForm({ ...form, middle_name: e.target.value })} />
        <select value={form.degree} onChange={(e) => setForm({ ...form, degree: e.target.value })}>
          {DEGREES.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select value={form.academic_title} onChange={(e) => setForm({ ...form, academic_title: e.target.value })}>
          {TITLES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })}>
          {POSITIONS.map((p) => <option key={p}>{p}</option>)}
        </select>
        <input type="number" step="0.1" min="0.1" max="2" style={{ width: 70 }} value={form.fte}
          onChange={(e) => setForm({ ...form, fte: Number(e.target.value) })} title="Ставка" />
        <button type="submit">Додати</button>
      </form>
      <table>
        <thead>
          <tr><th>ПІБ</th><th>Ступінь</th><th>Звання</th><th>Посада</th><th>Ставка</th><th>Предмети</th><th /></tr>
        </thead>
        <tbody>
          {teachers.map((t) => (
            <tr key={t.id}>
              <td>{[t.last_name, t.first_name, t.middle_name].filter(Boolean).join(" ")}</td>
              <td>{t.degree}</td>
              <td>{t.academic_title}</td>
              <td>{t.position}</td>
              <td>{t.fte}</td>
              <td>{t.subjects.map((s) => s.name).join(", ")}</td>
              <td><button onClick={() => remove(t.id)}>Видалити</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
