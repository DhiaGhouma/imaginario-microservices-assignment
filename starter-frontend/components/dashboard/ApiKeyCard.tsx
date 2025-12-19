interface ApiKey {
    id: string;
    name: string;
    is_active: boolean;
    created_at: string;
    last_used_at?: string;
}

interface ApiKeyCardProps {
    apiKey: ApiKey;
    onDelete?: (id: string) => void;
}

export default function ApiKeyCard({ apiKey, onDelete }: ApiKeyCardProps) {
    return (
        <div style={{
            padding: '16px',
            background: '#f9f9f9',
            borderRadius: '6px',
            marginBottom: '12px',
            border: '1px solid #e5e5e5'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontWeight: '600',
                        marginBottom: '6px',
                        fontSize: '15px',
                        color: '#333'
                    }}>
                        {apiKey.name}
                    </div>
                    <div style={{ fontSize: '13px', color: '#666' }}>
                        <div>Created: {new Date(apiKey.created_at).toLocaleDateString()}</div>
                        {apiKey.last_used_at && (
                            <div>Last used: {new Date(apiKey.last_used_at).toLocaleDateString()}</div>
                        )}
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{
                        padding: '6px 12px',
                        background: apiKey.is_active ? '#d1fae5' : '#fee2e2',
                        color: apiKey.is_active ? '#065f46' : '#991b1b',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: '500'
                    }}>
                        {apiKey.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {onDelete && (
                        <button
                            onClick={() => onDelete(apiKey.id)}
                            style={{
                                padding: '6px 12px',
                                background: '#fff',
                                border: '1px solid #ddd',
                                borderRadius: '4px',
                                fontSize: '12px',
                                cursor: 'pointer',
                                color: '#666'
                            }}
                        >
                            Delete
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}