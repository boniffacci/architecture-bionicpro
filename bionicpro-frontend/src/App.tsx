import React from 'react'
import Counter from './components/Counter'


export default function App() {
    console.log('App rendered')
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full p-8 bg-white rounded-2xl shadow">
                <h1 className="text-2xl font-bold mb-4">Vite + React + TypeScript + Tailwind</h1>
                <p className="mb-4 text-sm text-gray-600">Breakpoint: поставь `debug` в `Counter.tsx`</p>
                <Counter />
            </div>
        </div>
    )
}