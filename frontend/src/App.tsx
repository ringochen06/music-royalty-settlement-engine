import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import JournalEntries from './pages/JournalEntries';
import Ingestion from './pages/Ingestion';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="journal-entries" element={<JournalEntries />} />
        <Route path="ingestion" element={<Ingestion />} />
      </Route>
    </Routes>
  );
}
