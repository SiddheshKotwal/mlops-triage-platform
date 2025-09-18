// frontend/src/App.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Dashboard from './Dashboard';
import TicketSubmitter from './TicketSubmitter'; // <-- Import the real component
import ReviewDashboard from './ReviewDashboard'; // <-- Import the real component

function App() {
  const [view, setView] = useState('dashboard');
  const [reviewCount, setReviewCount] = useState(0);

  // This effect will update the badge in the navigation
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('http://localhost:8002/stats');
        setReviewCount(response.data.status_breakdown.pending_review || 0);
      } catch (error) {
        console.error("Failed to fetch stats for nav count:", error);
      }
    };
    fetchStats();
    const intervalId = setInterval(fetchStats, 3000);
    return () => clearInterval(intervalId);
  }, []);

  const renderView = () => {
    switch(view) {
      case 'dashboard': 
        return <Dashboard />;
      case 'submit': 
        return <TicketSubmitter />; // <-- Render the real component
      case 'review': 
        return <ReviewDashboard />; // <-- Render the real component
      default: 
        return <Dashboard />;
    }
  };

  return (
    <div className="bg-gray-100 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="bg-white shadow-md rounded-lg p-6 mb-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-blue-600">AI Triage System</h1>
          <nav className="flex items-center space-x-4">
            <button 
              onClick={() => setView('dashboard')} 
              className={`px-4 py-2 rounded-md font-semibold text-sm transition ${view === 'dashboard' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              Live Dashboard
            </button>
            <button 
              onClick={() => setView('submit')} 
              className={`px-4 py-2 rounded-md font-semibold text-sm transition ${view === 'submit' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              Submit Ticket
            </button>
            <button 
              onClick={() => setView('review')} 
              className={`relative px-4 py-2 rounded-md font-semibold text-sm transition ${view === 'review' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              Review Queue
              {reviewCount > 0 && (
                <span className="absolute -top-2 -right-2 flex items-center justify-center w-5 h-5 bg-orange-500 text-white text-xs font-bold rounded-full">
                  {reviewCount}
                </span>
              )}
            </button>
          </nav>
        </header>
        <main>
          {renderView()}
        </main>
      </div>
    </div>
  );
}

export default App;