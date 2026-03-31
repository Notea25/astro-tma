import { motion } from 'framer-motion'

export function LoadingSpinner({ message = 'Читаем звёзды...' }: { message?: string }) {
  return (
    <div className="loading-spinner">
      <motion.div
        className="spinner-moon"
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      >
        🌙
      </motion.div>
      <p className="spinner-text">{message}</p>
    </div>
  )
}
