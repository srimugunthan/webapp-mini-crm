import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import Contacts from "./pages/Contacts";
import Groups from "./pages/Groups";
import GroupPage from "./pages/GroupPage";
import ImportPage from "./pages/Import";
import Pipelines from "./pages/Pipelines";

function HealthBadge() {
  const { data, isError } = useQuery({ queryKey: ["health"], queryFn: () => api.get<{ status: string }>("/api/health"), refetchInterval: 30000 });
  const ok = data?.status === "ok";
  return <span className={ok ? "ok" : isError ? "warn" : "muted"} data-testid="health" style={{ marginLeft: "auto" }}>{ok ? "● backend ok" : isError ? "● backend down" : "…"}</span>;
}

export default function App() {
  const path = useLocation().pathname;
  const wide = path === "/" || path.startsWith("/groups/"); // contacts table uses the full window width
  const link = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");
  return (
    <>
      <nav className="top">
        <span className="brand">LinkedIn Mini CRM</span>
        <NavLink to="/" end className={link}>Contacts</NavLink>
        <NavLink to="/groups" className={link}>Groups</NavLink>
        <NavLink to="/pipelines" className={link}>Pipelines</NavLink>
        <NavLink to="/import" className={link}>Import</NavLink>
        <HealthBadge />
      </nav>
      <main className={wide ? "wide" : ""}>
        <Routes>
          <Route path="/" element={<Contacts />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/groups" element={<Groups />} />
          <Route path="/groups/:id" element={<GroupPage />} />
          <Route path="/pipelines" element={<Pipelines />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}
