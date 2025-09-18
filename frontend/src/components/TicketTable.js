// frontend/src/components/TicketTable.js
import React, { useState } from 'react';
import TicketModal from './TicketModal';

function TicketTable({ tickets }) {
  const [selectedTicket, setSelectedTicket] = useState(null);

  const statusColorMap = {
    PROCESSING: 'bg-blue-100 text-blue-800',
    COMPLETED: 'bg-green-100 text-green-800',
    PENDING_REVIEW: 'bg-orange-100 text-orange-800',
  };

  const formatTicketId = (id) => `${id.substring(0, 8)}...`;

  return (
    <div className="overflow-x-auto">
      <h3 className="text-xl font-semibold mb-2">Recent Tickets</h3>
      <table className="min-w-full bg-white">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created At</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {tickets.map(ticket => (
            <tr key={ticket.ticket_id} onClick={() => setSelectedTicket(ticket)} className="hover:bg-gray-50 cursor-pointer">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">{formatTicketId(ticket.ticket_id)}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 truncate max-w-xs">{ticket.subject}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{ticket.final_category || ticket.predicted_category || '-'}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{ticket.final_priority || ticket.predicted_priority || '-'}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColorMap[ticket.status]}`}>
                  {ticket.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(ticket.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selectedTicket && <TicketModal ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}

export default TicketTable;