import React from 'react'
import { motion } from 'framer-motion'

type PodiumPerson = {
  name: string;
  team?: string;
  time?: string;
  number?: string | number;
  avatarUrl?: string;
};

export default function PodiumWidget({ podium }: { podium: PodiumPerson[] }) {
  const first = podium?.[0]
  const second = podium?.[1]
  const third = podium?.[2]

  return (
    <div className="flex items-end gap-4">
      <div className="text-center">
        <div className="w-20 h-20 rounded-xl border flex items-center justify-center text-sm font-semibold">2</div>
        {second && <div className="mt-2 text-xs truncate">{second.name}</div>}
      </div>

      <motion.div initial={{ y: 20 }} animate={{ y: 0 }} className="text-center">
        <div className="w-28 h-28 rounded-xl border shadow-md flex items-center justify-center text-lg font-bold">1</div>
        {first && <div className="mt-2 text-sm font-semibold truncate">{first.name}</div>}
      </motion.div>

      <div className="text-center">
        <div className="w-20 h-20 rounded-xl border flex items-center justify-center text-sm font-semibold">3</div>
        {third && <div className="mt-2 text-xs truncate">{third.name}</div>}
      </div>
    </div>
  )
}
