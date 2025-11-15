import { ButtonHTMLAttributes } from 'react'
import { clsx } from 'clsx'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'secondary'
}

export function Button({ className, variant = 'default', ...props }: Props) {
  const base = variant === 'secondary' ? 'button-secondary' : 'button'
  return <button className={clsx(base, className)} {...props} />
}


