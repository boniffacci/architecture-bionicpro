import React, { useState } from 'react'


export default function Counter() {
    const [count, setCount] = useState(0)


    function inc() {
// поставь breakpoint сюда
        console.log('increment', count + 1)
        setCount(c => c + 1)
    }


    return (
        <div>
            <div className="text-4xl font-semibold mb-4">{count}</div>
            <button
                onClick={inc}
                className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
            >
                Increment
            </button>
        </div>
    )
}