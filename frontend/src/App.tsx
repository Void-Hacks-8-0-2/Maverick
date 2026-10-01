import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { CommandCenter } from './pages/CommandCenter';
import { AccountView } from './pages/AccountView';
import { TransactionExplorer } from './pages/TransactionExplorer';
import { NetworkGraph } from './pages/NetworkGraph';

export const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/investigate" element={<NetworkGraph />} />
            <Route path="/account/:id" element={<AccountView />} />
            <Route path="/transactions" element={<TransactionExplorer />} />
            <Route path="/graph" element={<NetworkGraph />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-slate-800/80 bg-[#070b12] py-4 text-center text-xs font-mono text-slate-500">
          Operation &quot;ABHEDYA-CHAKRA&quot; Base v0.1 &bull; Financial Cyber-Forensics & Money-Mule Network Investigation &bull; Void Hacks() 8.0
        </footer>
      </div>
    </Router>
  );
};

export default App;
