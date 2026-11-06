import { NavLink, Route, Routes } from "react-router-dom";
import TeachersPage from "./pages/TeachersPage";
import RoomsPage from "./pages/RoomsPage";
import GroupsPage from "./pages/GroupsPage";
import ImportPage from "./pages/ImportPage";
import SchedulePage from "./pages/SchedulePage";
import WorkloadPage from "./pages/WorkloadPage";

export default function App() {
  return (
    <div className="app">
      <nav>
        <div className="nav-group">
          <span className="nav-label">Оператор</span>
          <NavLink to="/teachers">Викладачі</NavLink>
          <NavLink to="/rooms">Аудиторії</NavLink>
          <NavLink to="/groups">Групи</NavLink>
          <NavLink to="/import">Імпорт Excel</NavLink>
          <NavLink to="/workload">Навантаження</NavLink>
        </div>
        <div className="nav-group">
          <span className="nav-label">Користувач</span>
          <NavLink to="/schedule">Розклад</NavLink>
        </div>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<SchedulePage />} />
          <Route path="/teachers" element={<TeachersPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/groups" element={<GroupsPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/workload" element={<WorkloadPage />} />
          <Route path="/schedule" element={<SchedulePage />} />
        </Routes>
      </main>
    </div>
  );
}
