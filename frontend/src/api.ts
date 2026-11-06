const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body && !(init.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : undefined,
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>(path, { method: "POST", body: form });
  },
};

export interface Faculty { id: number; name: string }
export interface Department { id: number; faculty_id: number; name: string }
export interface Specialty { id: number; code: string; name: string }
export interface Subject { id: number; name: string; department_id: number | null }

export interface Teacher {
  id: number;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  degree: string;
  academic_title: string;
  position: string;
  fte: number;
  department_id: number | null;
  subjects: Subject[];
}

export interface Room {
  id: number;
  department_id: number | null;
  building: string;
  floor: number;
  number: string;
  capacity: number;
  room_type: string;
}

export interface Group {
  id: number;
  faculty_id: number;
  specialty_id: number;
  program_id: number | null;
  code: string;
  enrollment_year: number;
  size: number;
}

export interface WorkloadRow {
  teacher_id: number;
  teacher: string;
  fte: number;
  by_lesson_type_hours: Record<string, number>;
  total_hours: number;
  norm_hours: number;
  load_percentage: number | null;
}

export interface ScheduleItem {
  date: string;
  period: number;
  subject: string;
  lesson_type: string;
  teacher: string;
  group: string;
  room: string | null;
}
