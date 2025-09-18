// frontend/src/TicketSubmitter.js

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const INGESTION_API_URL = 'http://localhost:8001';
const RESULTS_API_URL = 'http://localhost:8002';

function TicketSubmitter() {
  const [subject, setSubject] = useState('');
  const [description, setDescription] =useState('');
  const [currentTicket, setCurrentTicket] = useState(null);
  
  const pollingInterval = useRef(null);

  useEffect(() => {
    // Cleanup interval on component unmount
    return () => {
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current);
      }
    };
  }, []);

  const pollForResult = (ticketId) => {
    pollingInterval.current = setInterval(async () => {
      try {
        const response = await axios.get(`${RESULTS_API_URL}/tickets/${ticketId}`);
        const { status } = response.data;
        
        if (status === 'COMPLETED' || status === 'PENDING_REVIEW') {
          setCurrentTicket({ id: ticketId, status: status, result: response.data });
          clearInterval(pollingInterval.current);
        } else {
          // Keep polling, update status
          setCurrentTicket({ id: ticketId, status: status, result: null });
        }
      } catch (error) {
        console.error("Polling failed:", error);
        clearInterval(pollingInterval.current);
      }
    }, 1000); // Poll every 1 seconds
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (pollingInterval.current) clearInterval(pollingInterval.current);
    setCurrentTicket(null);

    try {
      const response = await axios.post(`${INGESTION_API_URL}/tickets`, { subject, description });
      const { ticket_id } = response.data;
      setCurrentTicket({ id: ticket_id, status: 'PROCESSING', result: null });
      pollForResult(ticket_id);
    } catch (error) {
      console.error("Submission failed:", error);
      setCurrentTicket({ id: null, status: 'FAILED', result: null });
    }
  };

  return (
    <div className="bg-white p-8 rounded-lg shadow-md max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Submit a New Support Ticket</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700">Subject</label>
          <input 
            type="text" 
            id="subject"
            value={subject} 
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g., Production server down" 
            required 
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">Description</label>
          <textarea 
            id="description"
            value={description} 
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Please provide a detailed description of the issue..." 
            required
            rows="5"
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <button type="submit" className="w-full py-2 px-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
          Submit Ticket
        </button>
      </form>
      {currentTicket && <ResultDisplay ticket={currentTicket} />}
    </div>
  );
}

// Helper component for displaying submission results
function ResultDisplay({ ticket }) {
  const statusColorMap = {
    PROCESSING: 'text-blue-700',
    COMPLETED: 'text-green-700',
    PENDING_REVIEW: 'text-orange-700',
    FAILED: 'text-red-700',
  };
  
  return (
    <div className="mt-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
      <h3 className="text-lg font-semibold text-gray-900">Ticket Status</h3>
      <p className="text-sm text-gray-600"><strong>ID:</strong> {ticket.id || 'N/A'}</p>
      <p className={`text-lg font-bold ${statusColorMap[ticket.status]}`}>{ticket.status}</p>
      {ticket.status === 'COMPLETED' && (
        <div className="mt-2 text-sm text-gray-800 space-y-1">
          <p><strong>Final Category:</strong> {ticket.result.final_category}</p>
          <p><strong>Final Priority:</strong> {ticket.result.final_priority}</p>
        </div>
      )}
       {ticket.status === 'PENDING_REVIEW' && (
        <p className="mt-2 text-sm text-orange-800">This ticket has low confidence and is now waiting in the expert review queue.</p>
      )}
    </div>
  );
}

export default TicketSubmitter;