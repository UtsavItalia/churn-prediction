const riskColors = {
    Critical: '#dc2626',
    High: '#ef4444',
    Medium: '#f59e0b',
    Low: '#10b981',
}

export default function CustomerTable({ customers, onRowClick }) {
    if (!customers.length) return (
        <p style={{ color: 'var(--muted)', padding: '24px 0' }}>No customers found.</p>
    )

    return (
        <div style={styles.wrapper}>
            <table style={styles.table}>
                <thead>
                    <tr>
                        {['Customer ID', 'Industry', 'Plan', 'Contract',
                            'Churn Prob', 'Risk', 'Status'].map(h => (
                                <th key={h} style={styles.th}>{h}</th>
                            ))}
                    </tr>
                </thead>
                <tbody>
                    {customers.map(c => (
                        <tr
                            key={c.customer_id}
                            onClick={() => onRowClick(c.customer_id)}
                            style={styles.row}
                        >
                            <td style={styles.td}>
                                <code style={styles.code}>{c.customer_id}</code>
                            </td>
                            <td style={styles.td}>{c.industry}</td>
                            <td style={styles.td}>{c.plan_tier}</td>
                            <td style={styles.td}>{c.contract_type}</td>
                            <td style={styles.td}>
                                <span style={{ fontWeight: 600 }}>
                                    {c.churn_probability != null
                                        ? `${(c.churn_probability * 100).toFixed(1)}%`
                                        : '—'}
                                </span>
                            </td>
                            <td style={styles.td}>
                                {c.risk_segment && (
                                    <span style={{
                                        ...styles.badge,
                                        color: riskColors[c.risk_segment],
                                        borderColor: riskColors[c.risk_segment],
                                    }}>
                                        {c.risk_segment}
                                    </span>
                                )}
                            </td>
                            <td style={styles.td}>
                                <span style={{
                                    color: c.churned ? 'var(--danger)' : 'var(--success)',
                                    fontWeight: 600,
                                }}>
                                    {c.churned ? 'Churned' : 'Active'}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

const styles = {
    wrapper: { overflowX: 'auto' },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: {
        textAlign: 'left', padding: '10px 16px',
        color: 'var(--muted)', fontSize: 12, fontWeight: 600,
        borderBottom: '1px solid var(--border)', textTransform: 'uppercase',
    },
    row: {
        cursor: 'pointer', transition: 'background 0.15s',
        borderBottom: '1px solid var(--border)',
    },
    td: { padding: '12px 16px' },
    code: {
        fontFamily: 'monospace', fontSize: 12,
        color: 'var(--primary)', background: 'rgba(99,102,241,0.1)',
        padding: '2px 6px', borderRadius: 4,
    },
    badge: {
        border: '1px solid', padding: '2px 8px',
        borderRadius: 12, fontSize: 12, fontWeight: 600,
    },
}
