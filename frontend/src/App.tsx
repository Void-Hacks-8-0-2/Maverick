import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { LandingPage } from './pages/LandingPage';
import { CommandCenter } from './pages/CommandCenter';
import { VictimInvestigation } from './pages/VictimInvestigation';
import { NetworkGraph } from './pages/NetworkGraph';
import { TimelineInvestigationView } from './pages/TimelineInvestigationView';
import { TransactionExplorer } from './pages/TransactionExplorer';
import { MuleIntelligence } from './pages/MuleIntelligence';
import { AccountView } from './pages/AccountView';
import { CaseFileView } from './pages/CaseFileView';
import { CaseDiaryView } from './pages/CaseDiaryView';
import { LegalFreezeView } from './pages/LegalFreezeView';

export const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Phase 17: Premium Institutional Landing Page */}
        <Route path="/" element={<LandingPage />} />

        {/* Operational Investigation Studio (Wrapped in AppLayout) */}
        <Route
          path="/dashboard"
          element={
            <AppLayout>
              <CommandCenter />
            </AppLayout>
          }
        />
        <Route
          path="/command"
          element={
            <AppLayout>
              <CommandCenter />
            </AppLayout>
          }
        />

        {/* Investigate Modules */}
        <Route
          path="/victim"
          element={
            <AppLayout>
              <VictimInvestigation />
            </AppLayout>
          }
        />
        <Route
          path="/victim/:id"
          element={
            <AppLayout>
              <VictimInvestigation />
            </AppLayout>
          }
        />
        <Route
          path="/graph"
          element={
            <AppLayout>
              <NetworkGraph />
            </AppLayout>
          }
        />
        <Route
          path="/investigate"
          element={
            <AppLayout>
              <NetworkGraph />
            </AppLayout>
          }
        />
        <Route
          path="/timeline"
          element={
            <AppLayout>
              <TimelineInvestigationView />
            </AppLayout>
          }
        />
        <Route
          path="/transactions"
          element={
            <AppLayout>
              <TransactionExplorer />
            </AppLayout>
          }
        />
        <Route
          path="/mules"
          element={
            <AppLayout>
              <MuleIntelligence />
            </AppLayout>
          }
        />
        <Route
          path="/suspect/:id"
          element={
            <AppLayout>
              <AccountView />
            </AppLayout>
          }
        />
        <Route
          path="/account/:id"
          element={
            <AppLayout>
              <AccountView />
            </AppLayout>
          }
        />
        <Route
          path="/accounts/:id"
          element={
            <AppLayout>
              <AccountView />
            </AppLayout>
          }
        />

        {/* Evidence Modules */}
        <Route
          path="/case-file"
          element={
            <AppLayout>
              <CaseFileView />
            </AppLayout>
          }
        />
        <Route
          path="/case-file/:id"
          element={
            <AppLayout>
              <CaseFileView />
            </AppLayout>
          }
        />
        <Route
          path="/case-diary"
          element={
            <AppLayout>
              <CaseDiaryView />
            </AppLayout>
          }
        />
        <Route
          path="/diary"
          element={
            <AppLayout>
              <CaseDiaryView />
            </AppLayout>
          }
        />
        <Route
          path="/diary/:id"
          element={
            <AppLayout>
              <CaseDiaryView />
            </AppLayout>
          }
        />
        <Route
          path="/legal-freeze"
          element={
            <AppLayout>
              <LegalFreezeView />
            </AppLayout>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
