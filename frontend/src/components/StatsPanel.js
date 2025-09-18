// frontend/src/components/StatsPanel.js
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

function StatsPanel({ stats }) {
    if (!stats) return null;

    // ... (keep the same data transformation logic as before) ...
    const statusData = [
        { name: 'Completed', value: stats.status_breakdown.completed || 0 },
        { name: 'Pending Review', value: stats.status_breakdown.pending_review || 0 },
        { name: 'Processing', value: stats.status_breakdown.processing || 0 },
    ].filter(item => item.value > 0);

    const categoryData = Object.keys(stats.category_breakdown || {}).map(key => ({
        name: key, value: stats.category_breakdown[key]
    }));
    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF0000'];

    return (
        <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
                <div className="bg-gray-50 p-5 rounded-lg border-l-4 border-blue-500">
                    <h3 className="text-sm font-medium text-gray-500">Total Tickets</h3>
                    <p className="mt-1 text-3xl font-semibold text-gray-900">{stats.total_tickets}</p>
                </div>
                <div className="bg-gray-50 p-5 rounded-lg border-l-4 border-green-500">
                    <h3 className="text-sm font-medium text-gray-500">Throughput (Last Min)</h3>
                    <p className="mt-1 text-3xl font-semibold text-gray-900">{stats.throughput_last_minute}</p>
                </div>
                <div className="bg-gray-50 p-5 rounded-lg border-l-4 border-orange-500">
                    <h3 className="text-sm font-medium text-gray-500">Review Queue</h3>
                    <p className="mt-1 text-3xl font-semibold text-gray-900">{stats.status_breakdown.pending_review}</p>
                </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="text-center">
                    <h3 className="font-semibold text-gray-700">Tickets by Status</h3>
                    {statusData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart><Pie data={statusData} dataKey="value" outerRadius={80} labelLine={false}><Cell fill="#00C49F"/><Cell fill="#FF8042"/><Cell fill="#0088FE"/></Pie><Tooltip /><Legend /></PieChart>
                        </ResponsiveContainer>
                    ) : <p className="text-gray-500 mt-4">No status data.</p>}
                </div>
                <div className="text-center">
                    <h3 className="font-semibold text-gray-700">Tickets by Final Category</h3>
                    {categoryData.length > 0 ? (
                         <ResponsiveContainer width="100%" height={200}>
                            <PieChart><Pie data={categoryData} dataKey="value" outerRadius={80} labelLine={false}>{categoryData.map((e,i) => <Cell key={`c-${i}`} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
                        </ResponsiveContainer>
                    ) : <p className="text-gray-500 mt-4">No completed tickets with categories yet.</p>}
                </div>
            </div>
        </div>
    );
}

export default StatsPanel;