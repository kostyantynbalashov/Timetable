import { useEffect, useState } from "react";
import { api } from "../api";
import type { Faculty, Group, Specialty } from "../api";

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [faculties, setFaculties] = useState<Faculty[]>([]);
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [error, setError] = useState("");
  const [newFaculty, setNewFaculty] = useState("");
  const [newSpecialty, setNewSpecialty] = useState({ code: "", name: "" });
  const [form, setForm] = useState({
    faculty_id: 0, specialty_id: 0, code: "", enrollment_year: new Date().getFullYear(), size: 0,
  });

  const loadAll = () => {
    api.get<Group[]>("/api/groups").then(setGroups).catch((e) => setError(String(e)));
    api.get<Faculty[]>("/api/faculties").then(setFaculties);
    api.get<Specialty[]>("/api/specialties").then(setSpecialties);
  };
  useEffect(() => { loadAll(); }, []);

  const addFaculty = async () => {
    if (!newFaculty.trim()) return;
    await api.post("/api/faculties", { name: newFaculty.trim() });
    setNewFaculty("");
    loadAll();
  };

  const addSpecialty = async () => {
    if (!newSpecialty.code.trim() || !newSpecialty.name.trim()) return;
    await api.post("/api/specialties", newSpecialty);
    setNewSpecialty({ code: "", name: "" });
    loadAll();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.faculty_id || !form.specialty_id) {
      setError("Оберіть факультет і спеціальність");
      return;
    }
    try {
      await api.post("/api/groups", form);
      setForm({ ...form, code: "", size: 0 });
      loadAll();
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (id: number) => {
    await api.del(`/api/groups/${id}`);
    loadAll();
  };

  return (
    <div>
      <h2>Студентські групи</h2>
      {error && <p className="error">{error}</p>}

      <details>
        <summary>Довідники (факультети / спеціальності)</summary>
        <div className="form-row">
          <input placeholder="Новий факультет" value={newFaculty} onChange={(e) => setNewFaculty(e.target.value)} />
          <button onClick={addFaculty}>Додати факультет</button>
        </div>
        <div className="form-row">
          <input placeholder="Код спец." style={{ width: 80 }} value={newSpecialty.code}
            onChange={(e) => setNewSpecialty({ ...newSpecialty, code: e.target.value })} />
          <input placeholder="Назва спеціальності" value={newSpecialty.name}
            onChange={(e) => setNewSpecialty({ ...newSpecialty, name: e.target.value })} />
          <button onClick={addSpecialty}>Додати спеціальність</button>
        </div>
      </details>

      <form onSubmit={submit} className="form-row">
        <select value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: Number(e.target.value) })}>
          <option value={0}>— факультет —</option>
          {faculties.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
        <select value={form.specialty_id} onChange={(e) => setForm({ ...form, specialty_id: Number(e.target.value) })}>
          <option value={0}>— спеціальність —</option>
          {specialties.map((s) => <option key={s.id} value={s.id}>{s.code} {s.name}</option>)}
        </select>
        <input placeholder="Код групи (напр. КН-24-1)" required value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })} />
        <input type="number" placeholder="Рік зарахування" required value={form.enrollment_year}
          onChange={(e) => setForm({ ...form, enrollment_year: Number(e.target.value) })} style={{ width: 120 }} />
        <input type="number" placeholder="Чисельність" value={form.size}
          onChange={(e) => setForm({ ...form, size: Number(e.target.value) })} style={{ width: 100 }} />
        <button type="submit">Додати</button>
      </form>

      <table>
        <thead><tr><th>Код</th><th>Факультет</th><th>Спеціальність</th><th>Рік зарахування</th><th>К-сть студентів</th><th /></tr></thead>
        <tbody>
          {groups.map((g) => (
            <tr key={g.id}>
              <td>{g.code}</td>
              <td>{faculties.find((f) => f.id === g.faculty_id)?.name}</td>
              <td>{specialties.find((s) => s.id === g.specialty_id)?.name}</td>
              <td>{g.enrollment_year}</td>
              <td>{g.size}</td>
              <td><button onClick={() => remove(g.id)}>Видалити</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
