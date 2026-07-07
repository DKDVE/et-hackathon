import { Navigate, Route, Routes } from "react-router-dom";

import { AssetRegistry } from "@/routes/AssetRegistry";
import { DossierView } from "@/routes/DossierView";
import { EventBoard } from "@/routes/EventBoard";
import { ReportView } from "@/routes/ReportView";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/events" replace />} />
      <Route path="/events" element={<EventBoard />} />
      <Route path="/events/:id" element={<DossierView />} />
      <Route path="/events/:id/report" element={<ReportView />} />
      <Route path="/assets" element={<AssetRegistry />} />
    </Routes>
  );
}
