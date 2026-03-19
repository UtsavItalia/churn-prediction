export default function StatCard({ label, value, sub, color }) {
    return (
        <div style={styles.card}>
            <div style={{ ...styles.accent, background: color }} />
            <p style={styles.label}>{label}</p>
            <p style={{ ...styles.value, color }}>{value}</p>
            {sub && <p style={styles.sub}>{sub}</p>}
        </div>
    )
}

const styles = {
    card: {
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: '20px 24px', position: 'relative',
        overflow: 'hidden',
    },
    accent: {
        position: 'absolute', top: 0, left: 0,
        right: 0, height: 3, borderRadius: '12px 12px 0 0',
    },
    label: { color: 'var(--muted)', fontSize: 12, marginBottom: 8, marginTop: 8 },
    value: { fontSize: 28, fontWeight: 700 },
    sub: { color: 'var(--muted)', fontSize: 12, marginTop: 4 },
}
