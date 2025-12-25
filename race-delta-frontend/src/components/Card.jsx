import React from 'react'

export default function Card({ title, subtitle, children, onClick }){
  return (
    <div onClick={onClick} className="p-4 border rounded-lg hover:shadow-sm cursor-pointer">
      <div className="text-sm text-gray-500">{subtitle}</div>
      <div className="mt-1 font-semibold text-primary">{title}</div>
      {children && <div className="mt-3 text-sm text-gray-700">{children}</div>}
    </div>
  )
}
