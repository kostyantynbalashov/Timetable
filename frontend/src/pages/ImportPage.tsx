import { useState } from "react";
import { api } from "../api";

interface Result { created: number; errors: { row: number; error: string }[] }

const ENTITIES: { key: string; label: string; columns: string }[] = [
  {
    key: "teachers",
    label: "Викладачі",
    columns: "Прізвище*, Ім'я*, По батькові, Ступінь, Звання, Посада*, Ставка, Кафедра, Факультет, Предмети (через кому)",
  },
  {
    key: "rooms",
    label: "Аудиторії",
    columns: "Корпус*, Поверх*, Номер*, Місткість*, Тип, Кафедра, Факультет",
  },
  {
    key: "groups",
    label: "Групи",
    columns: "Факультет*, Спеціальність (код)*, Спеціальність (назва)*, Освітня програма, Код групи*, Рік зарахування*, Чисельність",
  },
];

function UploadBlock({ entityKey, label, columns }: { entityKey: string; label: string; columns: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");

  const onFile = async (file: File) => {
    setError("");
    setResult(null);
    try {
      const res = await api.upload<Result>(`/api/import/${entityKey}`, file);
      setResult(res);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="import-block">
      <h3>{label}</h3>
      <p className="hint">Очікувані стовпці: {columns}</p>
      <input type="file" accept=".xlsx,.xls"
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      {error && <p className="error">{error}</p>}
      {result && (
        <p>
          Створено: {result.created}.{" "}
          {result.errors.length > 0 && (
            <>
              Помилок: {result.errors.length} —{" "}
              {result.errors.map((e) => `рядок ${e.row}: ${e.error}`).join("; ")}
            </>
          )}
        </p>
      )}
    </div>
  );
}

export default function ImportPage() {
  return (
    <div>
      <h2>Імпорт з Excel</h2>
      <p>Завантажте .xlsx з відповідними стовпцями. Поля з * обов'язкові; невідомі факультети/кафедри/спеціальності/предмети будуть створені автоматично.</p>
      {ENTITIES.map((e) => <UploadBlock key={e.key} entityKey={e.key} label={e.label} columns={e.columns} />)}
    </div>
  );
}
