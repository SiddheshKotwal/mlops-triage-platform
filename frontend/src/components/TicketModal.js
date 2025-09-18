// frontend/src/components/TicketModal.js
import React from 'react';

function TicketModal({ ticket, onClose }) {
  if (!ticket) return null;

  const statusColorMap = {
    PROCESSING: 'bg-blue-100 text-blue-800',
    COMPLETED: 'bg-green-100 text-green-800',
    PENDING_REVIEW: 'bg-orange-100 text-orange-800',
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-8 max-w-2xl w-full space-y-4" onClick={(e) => e.stopPropagation()}>
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Ticket Details</h2>
          <p className="font-mono text-sm text-gray-500">{ticket.ticket_id}</p>
        </div>
        <div className="border-t border-gray-200 pt-4">
          <p><strong>Subject:</strong> {ticket.subject}</p>
          <p className="mt-2"><strong>Description:</strong> {ticket.description}</p>
        </div>
        <div className="grid grid-cols-2 gap-4 border-t border-gray-200 pt-4">
          <p><strong>Status:</strong> <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColorMap[ticket.status]}`}>{ticket.status}</span></p>
          <p><strong>Submitted At:</strong> {new Date(ticket.created_at).toLocaleString()}</p>
          {ticket.status === 'COMPLETED' ? (
              <>
                  <p><strong>Final Category:</strong> {ticket.final_category}</p>
                  <p><strong>Final Priority:</strong> {ticket.final_priority}</p>
              </>
          ) : (
              <>
                  <p><strong>Predicted Category:</strong> {ticket.predicted_category || '-'}</p>
                  <p><strong>Predicted Priority:</strong> {ticket.predicted_priority || '-'}</p>
              </>
          )}
          <p><strong>Category Confidence:</strong> {ticket.prediction_confidence_category ? (ticket.prediction_confidence_category * 100).toFixed(2) + '%' : '-'}</p>
          <p><strong>Priority Confidence:</strong> {ticket.prediction_confidence_priority ? (ticket.prediction_confidence_priority * 100).toFixed(2) + '%' : '-'}</p>
          {ticket.reviewed_at && <p><strong>Reviewed At:</strong> {new Date(ticket.reviewed_at).toLocaleString()}</p>}
        </div>
        <div className="text-right pt-4">
          <button onClick={onClose} className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TicketModal;