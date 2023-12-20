import { AnimatePresence } from 'framer-motion'
import { Routes, Route } from 'react-router-dom'

import { Home } from '../pages/Home'

import { NotFound } from 'remoteApp/NotFound'
import { Path } from '../utils/types'

export const AnimatedRoutes = () => {
  return (
    <AnimatePresence>
      <Routes>
        <Route path={Path.HOME} element={<Home />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AnimatePresence>
  )
}
