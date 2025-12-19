import { ReactNode } from 'react';

interface DashboardCardProps {
    title?: string;
    subtitle?: string;
    children: ReactNode;
}

export default function DashboardCard({ title, subtitle, children }: DashboardCardProps) {
    return (
        <div style={{
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '24px',
            marginBottom: '24px'
        }}>
            {title && (
                <div style={{ marginBottom: '20px' }}>
                    <h2 style={{
                        fontSize: '18px',
                        marginBottom: subtitle ? '4px' : '0',
                        fontWeight: '600',
                        color: '#333'
                    }}>
                        {title}
                    </h2>
                    {subtitle && (
                        <p style={{
                            fontSize: '14px',
                            color: '#666',
                            margin: 0
                        }}>
                            {subtitle}
                        </p>
                    )}
                </div>
            )}
            {children}
        </div>
    );
}