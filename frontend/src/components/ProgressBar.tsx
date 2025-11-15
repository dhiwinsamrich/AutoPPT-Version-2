import { useEffect, useState, useRef } from 'react'

type Props = {
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'idle'
  logs: string[]
  className?: string
}

export function ProgressBar({ status, logs, className = '' }: Props) {
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState<string>('')
  const [tick, setTick] = useState(0) // Force re-calculation periodically
  const startTimeRef = useRef<number | null>(null)
  const lastProgressRef = useRef<number>(0)
  const progressHistoryRef = useRef<number[]>([])

  // Periodic update for time-based progress (every 2 seconds when running)
  useEffect(() => {
    if (status !== 'running') {
      return
    }

    const interval = setInterval(() => {
      // Trigger recalculation by updating tick
      setTick((prev) => prev + 1)
    }, 2000)

    return () => clearInterval(interval)
  }, [status])

  useEffect(() => {
    if (status === 'idle') {
      setProgress(0)
      setStage('')
      setTick(0)
      startTimeRef.current = null
      lastProgressRef.current = 0
      progressHistoryRef.current = []
      return
    }

    if (status === 'queued') {
      setProgress(5)
      setStage('Queued...')
      startTimeRef.current = Date.now()
      return
    }

    if (status === 'succeeded') {
      setProgress(100)
      setStage('Complete!')
      return
    }

    if (status === 'failed') {
      setProgress(lastProgressRef.current)
      setStage('Failed')
      return
    }

    // Initialize start time when running starts
    if (status === 'running' && startTimeRef.current === null) {
      startTimeRef.current = Date.now()
    }

    // Calculate progress based on log content
    const logText = logs.join('\n').toLowerCase()
    let calculatedProgress = 5 // Starting progress
    let currentStage = 'Initializing...'

    // Step 1: Analyzing template (5-15%)
    if (logText.includes('step 1') || logText.includes('analyzing presentation') || 
        logText.includes('analyzing template') || logText.includes('found') && logText.includes('placeholders')) {
      calculatedProgress = Math.max(calculatedProgress, 15)
      currentStage = 'Analyzing template...'
    }

    // Step 2: Identifying side headings (15-25%)
    if (logText.includes('step 2') || logText.includes('identifying maximum side_heading') ||
        logText.includes('maximum side_heading') || logText.includes('side_heading placeholders')) {
      calculatedProgress = Math.max(calculatedProgress, 25)
      currentStage = 'Detecting placeholders...'
    }

    // Step 3: Deleting slides (25-35%)
    if (logText.includes('step 3') || logText.includes('deleting slides') ||
        logText.includes('slides to delete') || logText.includes('re-analyzing presentation')) {
      calculatedProgress = Math.max(calculatedProgress, 35)
      currentStage = 'Cleaning template...'
    }

    // Step 4: Content generation starts (35-45%)
    if (logText.includes('step 4') || logText.includes('proceeding with content generation') ||
        logText.includes('matched') && logText.includes('placeholders')) {
      calculatedProgress = Math.max(calculatedProgress, 45)
      currentStage = 'Preparing content...'
    }

    // Step 4.1: Hyperlinks (45-50%)
    if (logText.includes('step 4.1') || logText.includes('hyperlinked placeholders') ||
        logText.includes('processing') && logText.includes('hyperlink')) {
      calculatedProgress = Math.max(calculatedProgress, 50)
      currentStage = 'Adding hyperlinks...'
    }

    // Fetching Google Sheets data (50-55%)
    if (logText.includes('fetching') && logText.includes('google sheets') ||
        logText.includes('sheets data') || logText.includes('analyzing project data') ||
        logText.includes('gemini') || logText.includes('sending project data')) {
      calculatedProgress = Math.max(calculatedProgress, 55)
      currentStage = 'Analyzing project data...'
    }

    // Comprehensive content generation (55-65%)
    if (logText.includes('comprehensive content generation') || 
        logText.includes('generating comprehensive content') ||
        logText.includes('successfully generated comprehensive content')) {
      calculatedProgress = Math.max(calculatedProgress, 65)
      currentStage = 'Generating content...'
    }

    // Individual content generation (65-70%)
    if (logText.includes('generating') && (logText.includes('heading') || logText.includes('content') || 
        logText.includes('bullet')) && !logText.includes('comprehensive')) {
      calculatedProgress = Math.max(calculatedProgress, 70)
      currentStage = 'Creating content...'
    }

    // Image generation (70-75%)
    if (logText.includes('generating') && logText.includes('image') ||
        logText.includes('downloading image') || logText.includes('uploading image')) {
      calculatedProgress = Math.max(calculatedProgress, 75)
      currentStage = 'Processing images...'
    }

    // Replacing placeholders (75-85%)
    if (logText.includes('replacing') || logText.includes('replaced') ||
        logText.includes('placeholder') && (logText.includes('updated') || logText.includes('processed'))) {
      calculatedProgress = Math.max(calculatedProgress, 85)
      currentStage = 'Replacing placeholders...'
    }

    // Applying styling (85-90%)
    if (logText.includes('applying') && logText.includes('styling') ||
        logText.includes('applying theme') || logText.includes('color') && logText.includes('applied')) {
      calculatedProgress = Math.max(calculatedProgress, 90)
      currentStage = 'Applying styling...'
    }

    // Finalizing (90-95%)
    if (logText.includes('presentation generated successfully') || 
        logText.includes('successfully generated') ||
        logText.includes('presentation url') || logText.includes('finalizing')) {
      calculatedProgress = Math.max(calculatedProgress, 95)
      currentStage = 'Finalizing...'
    }

    // Time-based fallback: gradually increase if stuck
    if (status === 'running' && startTimeRef.current) {
      const elapsed = (Date.now() - startTimeRef.current) / 1000 // seconds
      
      // If we've been running for a while and progress hasn't increased much, add time-based progress
      if (elapsed > 10 && calculatedProgress < 30) {
        // Add 1% per 5 seconds after 10 seconds, capped at 30%
        const timeBasedProgress = Math.min(30, 10 + Math.floor((elapsed - 10) / 5))
        calculatedProgress = Math.max(calculatedProgress, timeBasedProgress)
      } else if (elapsed > 30 && calculatedProgress < 60) {
        // After 30 seconds, allow up to 60% based on time
        const timeBasedProgress = Math.min(60, 30 + Math.floor((elapsed - 30) / 3))
        calculatedProgress = Math.max(calculatedProgress, timeBasedProgress)
      } else if (elapsed > 60 && calculatedProgress < 85) {
        // After 60 seconds, allow up to 85% based on time
        const timeBasedProgress = Math.min(85, 60 + Math.floor((elapsed - 60) / 2))
        calculatedProgress = Math.max(calculatedProgress, timeBasedProgress)
      }
    }

    // Smooth progress: don't decrease, and limit sudden jumps
    if (calculatedProgress > lastProgressRef.current) {
      // Allow progress to increase, but limit sudden jumps (max 10% increase per update)
      const maxIncrease = 10
      const allowedProgress = Math.min(
        calculatedProgress,
        lastProgressRef.current + maxIncrease
      )
      lastProgressRef.current = allowedProgress
      progressHistoryRef.current.push(allowedProgress)
      // Keep only last 10 progress values
      if (progressHistoryRef.current.length > 10) {
        progressHistoryRef.current.shift()
      }
      calculatedProgress = allowedProgress
    } else if (calculatedProgress < lastProgressRef.current) {
      // Don't decrease, maintain last progress
      calculatedProgress = lastProgressRef.current
    } else {
      // Same progress, update ref
      lastProgressRef.current = calculatedProgress
    }

    setProgress(calculatedProgress)
    setStage(currentStage)
  }, [status, logs, tick]) // Include tick to trigger recalculation

  if (status === 'idle') {
    return null
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-white/80">{stage || 'Processing...'}</span>
        <span className="text-white/60">{progress}%</span>
      </div>
      <div className="w-full rounded-full border border-white/15 bg-black/60 h-2.5 overflow-hidden">
        <div
          className="relative h-full rounded-full bg-gradient-to-r from-white to-neutral-300 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        >
          {/* Shimmer effect for active progress */}
          {status === 'running' && progress > 0 && progress < 100 && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          )}
        </div>
      </div>
      {status === 'running' && (
        <div className="flex items-center gap-2 text-xs text-white/60">
          <div className="h-1 w-1 rounded-full bg-white animate-pulse" />
          <span>This may take a few minutes...</span>
        </div>
      )}
    </div>
  )
}


