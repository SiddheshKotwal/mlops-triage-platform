// frontend/src/Dashboard.js (No changes to logic, just imports and structure)

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Toaster, toast } from 'react-hot-toast';

import StatsPanel from './components/StatsPanel';
import SearchBar from './components/SearchBar';
import TicketTable from './components/TicketTable';

const RESULTS_API_URL = 'http://localhost:8002';
const WEBSOCKET_URL = 'ws://localhost:8002/ws/ticket-updates';

function Dashboard() {
    // ... (Keep all the existing state and useEffect logic from the previous step) ...
    const [stats, setStats] = useState(null);
    const [tickets, setTickets] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const [statsRes, ticketsRes] = await Promise.all([
                    axios.get(`${RESULTS_API_URL}/stats`),
                    axios.get(`${RESULTS_API_URL}/tickets/recent`)
                ]);
                setStats(statsRes.data);
                const sortedTickets = ticketsRes.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 100);
                setTickets(sortedTickets);
            } catch (error) {
                console.error("Failed to fetch initial dashboard data:", error);
                toast.error("Could not load dashboard data.");
            } finally {
                setLoading(false);
            }
        };
        fetchInitialData();
    }, []);

    useEffect(() => {
        const ws = new WebSocket(WEBSOCKET_URL);
        ws.onopen = () => console.log("WebSocket connection established.");
        ws.onmessage = (event) => {
            const updatedTicket = JSON.parse(event.data);
            toast(`Ticket ${updatedTicket.ticket_id.substring(0, 8)}... updated to ${updatedTicket.status}`, { icon: '🔄' });
            setTickets(prevTickets => {
                const index = prevTickets.findIndex(t => t.ticket_id === updatedTicket.ticket_id);
                if (index > -1) {
                    const newTickets = [...prevTickets];
                    newTickets[index] = updatedTicket;
                    return newTickets.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                } else {
                    return [updatedTicket, ...prevTickets].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 100);
                }
            });
            axios.get(`${RESULTS_API_URL}/stats`).then(res => setStats(res.data));
        };
        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            toast.error("Real-time connection failed.");
        };
        ws.onclose = () => console.log("WebSocket connection closed.");
        return () => ws.close();
    }, []);

    const filteredTickets = useMemo(() => {
        if (!searchTerm) return tickets;
        return tickets.filter(ticket =>
            (ticket.subject && ticket.subject.toLowerCase().includes(searchTerm.toLowerCase())) ||
            ticket.ticket_id.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [tickets, searchTerm]);

    if (loading) {
        return <div className="bg-white p-6 rounded-lg shadow-md"><h2>Loading Dashboard...</h2></div>;
    }

    return (
        <div className="space-y-8">
            <Toaster position="top-right" />
            <StatsPanel stats={stats} />
            <div className="bg-white p-6 rounded-lg shadow-md">
                <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
                <TicketTable tickets={filteredTickets} />
            </div>
        </div>
    );
}

export default Dashboard;