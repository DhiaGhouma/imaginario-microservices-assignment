import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import StatCard from '../components/dashboard/StatCard';
import EndpointList from '../components/dashboard/EndpointList';
import SearchJobsList from '../components/dashboard/SearchJobList';
import ApiKeyCard from '../components/dashboard/ApiKeyCard';
import DashboardCard from '../components/dashboard/DashboardCard';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

interface AnalyticsData {
    total_requests: number;
    success_rate: number;
    avg_response_time: number;
    requests_by_endpoint: Record<string, number>;
}

interface ApiKey {
    id: string;
    name: string;
    is_active: boolean;
    created_at: string;
    last_used_at?: string;
}

interface SearchJob {
    job_id: string;
    query: string;
    status: string;
    execution_time?: number;
    created_at: string;
    completed_at?: string;
}

export default function DeveloperDashboard() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<AnalyticsData | null>(null);
    const [jobs, setJobs] = useState<SearchJob[]>([]);
    const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
    const [error, setError] = useState('');

    useEffect(() => {
        loadDashboardData();

        // Auto-refresh every 5 seconds
        const interval = setInterval(loadDashboardData, 5000);
        return () => clearInterval(interval);
    }, []);

    const loadDashboardData = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                router.push('/login');
                return;
            }

            const headers = { 'Authorization': `Bearer ${token}` };

            // Load all data in parallel
            const [analyticsRes, keysRes, jobsRes] = await Promise.all([
                fetch(`${API_URL}/api/v1/analytics/overview`, { headers }),
                fetch(`${API_URL}/api/v1/auth/api-keys`, { headers }),
                fetch(`${API_URL}/api/v1/search/jobs?per_page=20`, { headers })
            ]);

            if (analyticsRes.ok) {
                const data = await analyticsRes.json();
                setStats(data);
            }

            if (keysRes.ok) {
                const data = await keysRes.json();
                setApiKeys(data.api_keys || []);
            }

            if (jobsRes.ok) {
                const data = await jobsRes.json();
                setJobs(data.jobs || []);
            }

            setLoading(false);
        } catch (err) {
            console.error('Dashboard error:', err);
            setError('Failed to load dashboard data');
            setLoading(false);
        }
    };

    const handleDeleteApiKey = async (keyId: string) => {
        if (!confirm('Are you sure you want to delete this API key?')) {
            return;
        }

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_URL}/api/v1/auth/api-keys/${keyId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                loadDashboardData(); // Refresh data
            } else {
                alert('Failed to delete API key');
            }
        } catch (err) {
            alert('Error deleting API key');
        }
    };

    if (loading) {
        return (
            <div style={{
                padding: '40px',
                fontFamily: 'system-ui, sans-serif',
                textAlign: 'center'
            }}>
                <p>Loading dashboard...</p>
            </div>
        );
    }

    return (
        <div style={{
            padding: '24px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            maxWidth: '1200px',
            margin: '0 auto',
            background: '#f8f9fa',
            minHeight: '100vh'
        }}>
            {/* Header */}
            <div style={{ marginBottom: '32px' }}>
                <h1 style={{
                    fontSize: '28px',
                    marginBottom: '8px',
                    fontWeight: '700',
                    color: '#1a1a1a'
                }}>
                    Developer Dashboard
                </h1>
                <p style={{ color: '#666', fontSize: '15px' }}>
                    Monitor your API usage, search jobs, and API keys
                </p>
            </div>

            {/* Error Message */}
            {error && (
                <div style={{
                    padding: '12px 16px',
                    background: '#fee',
                    border: '1px solid #fcc',
                    borderRadius: '6px',
                    marginBottom: '24px',
                    color: '#c00'
                }}>
                    {error}
                </div>
            )}

            {/* Stats Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '16px',
                marginBottom: '32px'
            }}>
                <StatCard
                    title="Total Requests"
                    value={stats?.total_requests || 0}
                    color="#3b82f6"
                />
                <StatCard
                    title="Success Rate"
                    value={`${stats?.success_rate || 0}%`}
                    color="#10b981"
                />
                <StatCard
                    title="Avg Response"
                    value={`${((stats?.avg_response_time || 0) * 1000).toFixed(0)}ms`}
                    color="#8b5cf6"
                />
                <StatCard
                    title="API Keys"
                    value={apiKeys.length}
                    color="#f59e0b"
                />
            </div>

            {/* Endpoint Breakdown */}
            <EndpointList endpoints={stats?.requests_by_endpoint} />

            {/* Search Jobs */}
            <DashboardCard
                title="Recent Search Jobs"
                subtitle="Auto-refreshes every 5 seconds"
            >
                <SearchJobsList jobs={jobs} loading={false} />
            </DashboardCard>

            {/* API Keys */}
            <DashboardCard
                title="API Keys"
                subtitle="Manage your API access keys"
            >
                {apiKeys.length === 0 ? (
                    <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
                        No API keys created yet
                    </p>
                ) : (
                    <div>
                        {apiKeys.map(key => (
                            <ApiKeyCard
                                key={key.id}
                                apiKey={key}
                                onDelete={handleDeleteApiKey}
                            />
                        ))}
                    </div>
                )}
            </DashboardCard>
        </div>
    );
}