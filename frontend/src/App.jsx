import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Content, Theme } from '@carbon/react';
import AppHeader from './components/AppHeader';
import Dashboard from './pages/Dashboard';
import DocumentUpload from './pages/DocumentUpload';
import WorkflowExecution from './pages/WorkflowExecution';
import ExtractedFacts from './pages/ExtractedFacts';
import './App.scss';

function App() {
  return (
    <Router>
      <Theme theme="g100">
        <AppHeader />
        <Content>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<DocumentUpload />} />
            <Route path="/workflow/:projectId" element={<WorkflowExecution />} />
            <Route path="/facts/:projectId" element={<ExtractedFacts />} />
          </Routes>
        </Content>
      </Theme>
    </Router>
  );
}

export default App;

// Made with Bob
