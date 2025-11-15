import { InputHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

type Props = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, Props>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={clsx('input w-full', className)} {...props} />
})


