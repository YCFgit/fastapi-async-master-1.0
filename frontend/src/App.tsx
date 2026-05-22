// frontend/src/App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { I18nProvider } from './lib/i18n';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import TasksHistory from './pages/TasksHistory';
import TasksCleanup from './pages/TasksCleanup';
import TaskTypeManager from './pages/TaskTypeManager';
import './App.css';

function App() {
  return (
    <I18nProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="task-types" element={<TaskTypeManager />} />
            <Route path="tasks-history" element={<TasksHistory />} />
            <Route path="tasks-cleanup" element={<TasksCleanup />} />
          </Route>
        </Routes>
      </Router>
    </I18nProvider>
  );
}

export default App;
