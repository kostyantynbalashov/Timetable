import { useEffect, useState } from "react";
import { api } from "../api";
import type { Room } from "../api";

const TYPES = ["лекційна", "семінарська", "лабораторія", "комп'ютерний клас", "спортзал", "інше"];

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ building: "", floor: 1, number: "", capacity: 30, room_type: TYPES[0] });

  const load = () => api.get<Room[]>("/api/rooms").then(setRooms).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/api/rooms", form);
      setForm({ ...form, number: "" });
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (id: number) => {
    await api.del(`/api/rooms/${id}`);
    load();
  };

  return (
    <div>
      <h2>Аудиторії</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit} className="form-row">
        <input placeholder="Корпус" required value={form.building}
          onChange={(e) => setForm({ ...form, building: e.target.value })} style={{ width: 80 }} />
        <input type="number" placeholder="Поверх" required value={form.floor}
          onChange={(e) => setForm({ ...form, floor: Number(e.target.value) })} style={{ width: 80 }} />
        <input placeholder="Номер" required value={form.number}
          onChange={(e) => setForm({ ...form, number: e.target.value })} style={{ width: 80 }} />
        <input type="number" placeholder="Місткість" required value={form.capacity}
          onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} style={{ width: 100 }} />
        <select value={form.room_type} onChange={(e) => setForm({ ...form, room_type: e.target.value })}>
          {TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <button type="submit">Додати</button>
      </form>
      <table>
        <thead><tr><th>Корпус</th><th>Поверх</th><th>Номер</th><th>Місткість</th><th>Тип</th><th /></tr></thead>
        <tbody>
          {rooms.map((r) => (
            <tr key={r.id}>
              <td>{r.building}</td><td>{r.floor}</td><td>{r.number}</td>
              <td>{r.capacity}</td><td>{r.room_type}</td>
              <td><button onClick={() => remove(r.id)}>Видалити</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
