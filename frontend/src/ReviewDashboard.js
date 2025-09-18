// frontend/src/ReviewDashboard.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const RESULTS_API_URL = 'http://localhost:8002';

function ReviewDashboard() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const TICKET_CATEGORIES = ["Technical Issues & Bugs", "Sales, Product & Marketing Inquiries", "Security & Compliance", "Infrastructure & Hardware", "Finance & Billing", "User Assistance & How-To"];
  const TICKET_PRIORITIES = ["high", "low", "medium"];

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${RESULTS_API_URL}/review-queue`);
      setQueue(response.data);
    } catch (error) {
      console.error("Failed to fetch review queue:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);
  
  const handleReviewSubmit = async (ticketId, final_category, final_priority) => {
    try {
        await axios.post(`${RESULTS_API_URL}/review/${ticketId}`, { final_category, final_priority });
        setQueue(prevQueue => prevQueue.filter(ticket => ticket.ticket_id !== ticketId));
    } catch (error) {
        console.error(`Failed to submit review for ${ticketId}:`, error);
        alert("Failed to submit review. The ticket might have been reviewed by someone else.");
    }
  };

  if (loading) {
    return <div className="bg-white p-6 rounded-lg shadow-md"><h2>Loading Review Queue...</h2></div>
  }

  return (
    <div className="bg-white p-8 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Expert Review Queue</h2>
        <span className="text-lg font-semibold text-blue-600">{queue.length} Tickets</span>
      </div>
      {queue.length === 0 ? (
        <p className="text-center text-gray-500 py-10">The review queue is currently empty. Great job!</p>
      ) : (
        <div className="space-y-6">
          {queue.map(ticket => (
            <div key={ticket.ticket_id} className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-bold text-gray-900">{ticket.subject}</h4>
              <p className="text-gray-600 mt-1 mb-3">{ticket.description}</p>
              <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-md mb-3">
                <h5 className="text-sm font-semibold text-yellow-800">Model's Guess:</h5>
                <div className="flex space-x-4 text-sm text-yellow-700">
                  <span>Category: {ticket.predicted_category}</span>
                  <span>Priority: {ticket.predicted_priority}</span>
                </div>
              </div>
              <ReviewForm ticket={ticket} categories={TICKET_CATEGORIES} priorities={TICKET_PRIORITIES} onSubmit={handleReviewSubmit}/>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper Component for the review form
function ReviewForm({ ticket, categories, priorities, onSubmit }) {
    const [cat, setCat] = useState(ticket.predicted_category);
    const [pri, setPri] = useState(ticket.predicted_priority);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(ticket.ticket_id, cat, pri);
    }

    return (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-4">
            <select value={cat} onChange={e => setCat(e.target.value)} className="flex-grow border border-gray-300 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={pri} onChange={e => setPri(e.target.value)} className="border border-gray-300 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                {priorities.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <button type="submit" className="py-2 px-4 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
              Save Correction
            </button>
        </form>
    );
}

export default ReviewDashboard;