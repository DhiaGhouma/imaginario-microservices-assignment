"use client"

import Link from 'next/link'
import { useRouter } from 'next/router'
import { useDispatch, useSelector } from 'react-redux'
import { useEffect, useState } from 'react'
import { AppDispatch, RootState } from '@/lib/store'
import { logout } from '@/lib/slices/authSlice'

export default function Navbar() {
    const router = useRouter()
    const dispatch = useDispatch<AppDispatch>()
    const { user, isAuthenticated } = useSelector((state: RootState) => state.auth)

    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    const handleLogout = () => {
        dispatch(logout())
        router.push('/login')
    }

    if (!mounted) return null
    if (!isAuthenticated) return null

    return (
        <nav className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                    <div className="flex items-center">
                        <Link href="/" className="flex items-center">
                            <h1 className="text-xl font-bold text-indigo-600">
                                Video Platform
                            </h1>
                        </Link>

                        <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                            <Link
                                href="/"
                                className={`${router.pathname === '/'
                                    ? 'border-indigo-500 text-gray-900'
                                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                            >
                                Home
                            </Link>

                            <Link
                                href="/developer-dashboard"
                                className={`${router.pathname === '/developer-dashboard'
                                    ? 'border-indigo-500 text-gray-900'
                                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                            >
                                Dashboard
                            </Link>

                            <Link
                                href="/api-keys"
                                className={`${router.pathname === '/api-keys'
                                    ? 'border-indigo-500 text-gray-900'
                                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                            >
                                API Keys
                            </Link>
                        </div>
                    </div>

                    <div className="flex items-center">
                        <span className="text-gray-700 mr-4">
                            Welcome, {user?.name}
                        </span>
                        <button
                            onClick={handleLogout}
                            className="px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    )
}
