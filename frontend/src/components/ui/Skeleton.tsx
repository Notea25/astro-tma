// Skeleton shimmer components — replace LoadingSpinner where layout is known

function SkeletonLine({ width = '100%', height = '14px', radius = '6px', style }: {
  width?: string; height?: string; radius?: string; style?: React.CSSProperties
}) {
  return <div className="skeleton-line" style={{ width, height, borderRadius: radius, ...style }} />
}

// Horoscope card skeleton (glass-gold)
export function HoroscopeSkeleton() {
  return (
    <div className="horoscope-card glass-gold skeleton-card">
      <SkeletonLine width="120px" height="12px" style={{ marginBottom: '14px' }} />
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
        <div className="skeleton-circle" style={{ width: '40px', height: '40px' }} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <SkeletonLine width="90px" height="14px" />
          <SkeletonLine width="70px" height="11px" />
        </div>
      </div>
      <SkeletonLine height="13px" style={{ marginBottom: '8px' }} />
      <SkeletonLine height="13px" width="90%" style={{ marginBottom: '8px' }} />
      <SkeletonLine height="13px" width="75%" style={{ marginBottom: '20px' }} />
      <div style={{ display: 'flex', gap: '8px' }}>
        <SkeletonLine width="80px" height="8px" radius="4px" />
        <SkeletonLine width="60px" height="8px" radius="4px" />
        <SkeletonLine width="70px" height="8px" radius="4px" />
      </div>
    </div>
  )
}

// Natal basic card skeleton
export function NatalBasicSkeleton() {
  return (
    <div className="natal-card natal-card--basic skeleton-card">
      <SkeletonLine width="130px" height="12px" style={{ marginBottom: '16px' }} />
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
        <div className="skeleton-circle" style={{ width: '44px', height: '44px' }} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <SkeletonLine width="100px" height="16px" />
          <SkeletonLine width="80px" height="12px" />
        </div>
      </div>
      <div style={{ display: 'flex', gap: '10px' }}>
        <div className="skeleton-chip" />
        <div className="skeleton-chip" />
      </div>
    </div>
  )
}

// Moon phase card skeleton
export function MoonPhaseSkeleton() {
  return (
    <div className="moon-phase-card skeleton-card">
      <SkeletonLine width="80px" height="11px" style={{ marginBottom: '8px' }} />
      <SkeletonLine width="140px" height="18px" style={{ marginBottom: '8px' }} />
      <SkeletonLine width="110px" height="12px" style={{ marginBottom: '14px' }} />
      <SkeletonLine height="13px" style={{ marginBottom: '6px' }} />
      <SkeletonLine height="13px" width="85%" />
    </div>
  )
}

// Home moon card skeleton (glass-purp, compact horizontal)
export function MoonCardSkeleton() {
  return (
    <div className="moon-card glass-purp skeleton-card" style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
      <div className="skeleton-circle" style={{ width: '36px', height: '36px', flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <SkeletonLine width="120px" height="14px" />
        <SkeletonLine width="90px" height="11px" />
      </div>
    </div>
  )
}

// Moon calendar grid skeleton
export function MoonCalendarSkeleton() {
  return (
    <div className="moon-calendar skeleton-card">
      <div className="moon-calendar__days-header">
        {['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].map(d => (
          <div key={d} className="moon-calendar__day-label">{d}</div>
        ))}
      </div>
      <div className="moon-calendar__grid">
        {Array.from({ length: 35 }, (_, i) => (
          <div key={i} className="moon-calendar__cell moon-calendar__cell--empty">
            <div className="skeleton-line" style={{ width: '22px', height: '22px', borderRadius: '6px' }} />
          </div>
        ))}
      </div>
    </div>
  )
}
