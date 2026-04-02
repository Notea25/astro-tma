import { motion } from 'framer-motion'

export function LoadingSpinner({ message = 'Читаем звёзды...' }: { message?: string }) {
  return (
    <div className="loading-spinner">
      <motion.svg
        className="spinner-ring"
        width="36" height="36" viewBox="0 0 36 36" fill="none"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
      >
        <circle cx="18" cy="18" r="15" stroke="rgba(201,168,76,0.15)" strokeWidth="2.5"/>
        <path
          d="M18 3 A15 15 0 0 1 33 18"
          stroke="var(--gold)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </motion.svg>
      <p className="spinner-text">{message}</p>
    </div>
  )
}
