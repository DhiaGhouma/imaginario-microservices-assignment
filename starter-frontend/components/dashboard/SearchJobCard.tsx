interface SearchJob {
    job_id: string;
    query: string;
    status: string;
    execution_time?: number;
    created_at: string;
    completed_at?: string;
}

interface SearchJobCardProps {
    job: SearchJob;
}

export default function SearchJobCard({ job }: SearchJobCardProps) {
    const getStatusColor = (status: string): string => {
        const colors: Record<string, string> = {
            'completed': '#10b981',
            'processing': '#3b82f6',
            'failed': '#ef4444',
            'queued': '#f59e0b',
            'pending': '#f59e0b'
        };
        return colors[status] || '#666';
    };

    const formatTimeAgo = (timestamp: string): string => {
        const seconds = Math.floor((new Date().getTime() - new Date(timestamp).getTime()) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    };

    return (
        <div style={{
            padding: '16px',
            background: '#fafafa',
            borderRadius: '6px',
            marginBottom: '12px',
            border: '1px solid #eee'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '8px'
            }}>
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontWeight: '500',
                        marginBottom: '6px',
                        fontSize: '15px'
                    }}>
                        "{job.query}"
                    </div>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        fontSize: '13px',
                        color: '#666'
                    }}>
                        <span style={{
                            display: 'inline-block',
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: getStatusColor(job.status),
                            marginRight: '8px'
                        }} />
                        <span style={{ textTransform: 'capitalize' }}>
                            {job.status}
                        </span>
                        {job.execution_time && (
                            <span style={{ marginLeft: '12px', color: '#999' }}>
                                • {job.execution_time.toFixed(2)}s
                            </span>
                        )}
                    </div>
                </div>
                <div style={{
                    fontSize: '12px',
                    color: '#999',
                    textAlign: 'right',
                    whiteSpace: 'nowrap',
                    marginLeft: '16px'
                }}>
                    {formatTimeAgo(job.created_at)}
                </div>
            </div>

            {job.completed_at && (
                <div style={{
                    fontSize: '12px',
                    color: '#888',
                    marginTop: '4px'
                }}>
                    Completed: {new Date(job.completed_at).toLocaleString()}
                </div>
            )}
        </div>
    );
}