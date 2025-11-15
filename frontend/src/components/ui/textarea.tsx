import { TextareaHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

type Props = TextareaHTMLAttributes<HTMLTextAreaElement>

export const Textarea = forwardRef<HTMLTextAreaElement, Props>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={clsx('input w-full min-h-[120px] resize-y', className)} {...props} />
})


