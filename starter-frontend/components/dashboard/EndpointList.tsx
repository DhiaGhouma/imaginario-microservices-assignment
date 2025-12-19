interface EndpointListProps {
    endpoints?: Record<string, number>;
}

export default function EndpointList({ endpoints }: EndpointListProps) {
    if (!endpoints || Object.keys(endpoints).length === 0) {
        return <p style={{ color: '#999' }}>No endpoint data available</p>;
    }

    return (
        <div style={{
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '30px'
        }}>
            <h2 style={{ fontSize: '18px', marginBottom: '15px', fontWeight: '600' }}>
                Requests by Endpoint
            </h2>
            <div>
                {Object.entries(endpoints).map(([endpoint, count]) => (
                    <div key={endpoint} style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '12px 0',
                        borderBottom: '1px solid #f0f0f0'
                    }}>
                        <span style={{
                            color: '#555',
                            fontFamily: 'monospace',
                            fontSize: '14px'
                        }}>
                            {endpoint}
                        </span>
                        <span style={{
                            fontWeight: 'bold',
                            color: '#333',
                            background: '#f5f5f5',
                            padding: '4px 12px',
                            borderRadius: '4px'
                        }}>
                            {count}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}