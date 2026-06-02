import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

interface Props {
  label: string
  value: string
  short?: boolean
}

export default function CopyableId({ label, value, short = true }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-[#5f6368]">
      <span className="text-[#9aa0a6] not-mono font-sans">{label}:</span>
      <span>{short ? `${value.slice(0, 8)}…` : value}</span>
      <button
        onClick={handleCopy}
        title={`Copy ${label}`}
        className="text-[#9aa0a6] hover:text-[#1a73e8] transition-colors"
      >
        {copied
          ? <Check size={11} className="text-[#34a853]" />
          : <Copy size={11} />
        }
      </button>
    </span>
  )
}
