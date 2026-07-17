'use client'

import { useState, useEffect } from 'react'
import { getCurrentUser } from '@/actions/auth'
import type { User } from '@/types/user'

export function usePermission() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCurrentUser().then((u) => {
      setUser(u)
      setLoading(false)
    })
  }, [])

  return {
    user,
    loading,
  }
}