export default function StatCard({ title, value, color = '#3b82f6' }) {
    return (
        <div style={{
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '20px'
        }}>
            <div style={{
                fontSize: '13px',
                color: '#666',
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
            }}>
                {title}
            </div>
            <div style={{
                fontSize: '32px',
                fontWeight: 'bold',
                color
            }}>
                {value}
            </div>
        </div>
    );
}