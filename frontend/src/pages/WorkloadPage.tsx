import { useState } from "react";
import { api } from "../api";
import type { WorkloadRow } from "../api";

export default function WorkloadPage() {
  const [academicYear, setAcademicYear] = useState("2026/2027");
  const [semester, setSemester] = useState(1);
  const [norm, setNorm] = useState(600);
  const [rows, setRows] = useState<WorkloadRow[]>([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const data = await api.get<WorkloadRow[]>(
        `/api/workload/teachers?academic_year=${encodeURIComponent(academicYear)}&semester=${semester}&norm_hours_per_fte=${norm}`
      );
      setRows(data);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      <h2>Навантаження викладачів</h2>
      <p className="hint">
        MVP: сума контактних годин (1 пара = 2 акад. год) за фактично запланованими заняттями.
        Норма на ставку — орієнтовний параметр, уточніть реальне значення на кафедрі.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="form-row">
        <input placeholder="Навчальний рік (2026/2027)" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
        <select value={semester} onChange={(e) => setSemester(Number(e.target.value))}>
          <option value={1}>1 семестр</option>
          <option value={2}>2 семестр</option>
        </select>
        <input type="number" value={norm} onChange={(e) => setNorm(Number(e.target.value))} style={{ width: 100 }} title="Норма год./ставку" />
        <button onClick={load}>Розрахувати</button>
      </div>
      <table>
        <thead><tr><th>Викладач</th><th>Ставка</th><th>За типами занять</th><th>Усього год.</th><th>Норма год.</th><th>% навантаження</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.teacher_id}>
              <td>{r.teacher}</td>
              <td>{r.fte}</td>
              <td>{Object.entries(r.by_lesson_type_hours).map(([k, v]) => `${k}: ${v}`).join(", ")}</td>
              <td>{r.total_hours}</td>
              <td>{r.norm_hours}</td>
              <td>{r.load_percentage ?? "—"}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
